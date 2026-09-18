"""Validated Zotero captures, source comparison, and conservative note discovery."""

from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import yaml
from cli_anything.zotero.utils.snapshots import validate, diff, hash_file
from state import digest

CLI = os.environ.get(
    "CLI_ZOTERO", str(Path.home() / "anaconda3/bin/cli-anything-zotero")
)
PAPERS = {
    "journalArticle",
    "conferencePaper",
    "preprint",
    "report",
    "thesis",
    "bookSection",
    "dataset",
    "webpage",
    "computerProgram",
}


def command(*args):
    p = subprocess.run(
        [CLI, "--json", *args], capture_output=True, text=True, timeout=300
    )
    if p.returncode:
        raise ValueError("Zotero command failed: " + p.stderr.strip())
    return json.loads(p.stdout)


def capture(path=None):
    if path:
        s = json.loads(Path(path).read_text())
    else:
        with tempfile.TemporaryDirectory(prefix="librarian-source-") as tmp:
            out = Path(tmp) / "snapshot.json"
            command("snapshot", "-o", str(out))
            s = json.loads(out.read_text())
    validate(s)
    if path:
        for x in s["items"]:
            f = x.get("file")
            if f and f.get("sha256") and hash_file(f["path"])[0] != f["sha256"]:
                raise ValueError("Snapshot PDF bytes changed: " + x["key"])
    roots = [
        x["key"]
        for x in s["items"]
        if not x["parentItem"] and x["metadata"]["itemType"] in PAPERS | {"book"}
    ]
    if path:
        if any(
            not isinstance(s.get("citationKeys", {}).get(k), str)
            or not s["citationKeys"][k]
            for k in roots
        ):
            raise ValueError(
                "Controlled snapshot requires canonical citationKeys for every work"
            )
    else:

        def cite(k):
            r = command("cite", k)
            key = r.get("citationKey")
            if not key:
                raise ValueError("Missing canonical citation key: " + k)
            return k, key

        with ThreadPoolExecutor(max_workers=8) as pool:
            s["citationKeys"] = dict(pool.map(cite, roots))
        # Canonical citation lookups happen outside the snapshot transaction.
        # Reject a profile/library/source change during that interval.
        with tempfile.TemporaryDirectory(prefix="librarian-confirm-") as tmp:
            out = Path(tmp) / "snapshot.json"
            command("snapshot", "-o", str(out))
            confirmed = json.loads(out.read_text())
        changes = diff(s, confirmed)
        if any(changes.values()):
            raise ValueError("Library changed during citation resolution; rescan")
    return s


def identity(s, key=None):
    result = dict(
        server_id=s["serverID"],
        library_type=s["library"]["type"],
        library_id=s["library"]["id"],
    )
    if key:
        result["key"] = key
    return result


def selected_keys(s, items, collections):
    cmap = {c["key"]: c for c in s["collections"]}
    selected = set(items)
    allkeys = {x["key"] for x in s["items"] if not x["parentItem"]}
    if selected - allkeys:
        raise ValueError(
            "Unknown top-level item: " + ", ".join(sorted(selected - allkeys))
        )
    cs = set()
    for selector in collections:
        found = [
            c for c in cmap.values() if c["key"] == selector or c["path"] == selector
        ]
        if not found:
            found = [c for c in cmap.values() if c["collectionName"] == selector]
        if len(found) != 1:
            raise ValueError(
                "Collection missing or ambiguous: "
                + selector
                + "; candidates: "
                + ", ".join(c["path"] for c in found)
            )
        cs.add(found[0]["key"])
    while True:
        more = {k for k, c in cmap.items() if c["parentCollection"] in cs}
        if more <= cs:
            break
        cs |= more
    selected |= {
        x["key"] for x in s["items"] if set(x["metadata"].get("collections", [])) & cs
    }
    return selected if items or collections else allkeys


def sources(s, old_items, selections):
    result = {}
    for row in s["items"]:
        key = row["key"]
        meta = row["metadata"]
        if row["parentItem"] or meta["itemType"] not in PAPERS | {"book"}:
            continue
        old = old_items.get(key, {})
        children = [x for x in s["items"] if x["rootItem"] == key and x["key"] != key]
        pdfs = [
            x
            for x in children
            if x["metadata"].get("contentType") == "application/pdf"
            and x.get("file", {}).get("status") == "available"
        ]
        requested = selections.get(key)
        preferred = requested or old.get("selected_attachment")
        chosen = next((x for x in pdfs if x["key"] == preferred), None)
        problem = None
        if requested and not chosen:
            raise ValueError(
                "Selected attachment must be an available PDF belonging to " + key
            )
        if not chosen:
            distinct = {x["file"]["sha256"] for x in pdfs}
            if preferred and pdfs:
                problem = "selected_attachment_missing"
            elif len(distinct) > 1:
                problem = "attachment_ambiguous"
            elif pdfs:
                chosen = sorted(pdfs, key=lambda x: x["key"])[0]
        bib = {
            k: v
            for k, v in meta.items()
            if k
            not in {
                "abstractNote",
                "collections",
                "collectionDetails",
                "tags",
                "note",
                "dateModified",
                "dateAdded",
                "version",
            }
        }
        fp = dict(
            bibliography=digest(bib),
            citation=digest(s["citationKeys"][key]),
            abstract=digest(meta.get("abstractNote", "")),
            pdf=chosen["file"]["sha256"] if chosen else None,
            availability="available" if chosen else "unavailable",
            membership=digest(
                meta.get("collectionDetails", meta.get("collections", []))
            ),
            tags=digest(meta.get("tags", [])),
            annotations=digest(
                [
                    x["metadata"]
                    for x in children
                    if x["metadata"]["itemType"] in {"note", "annotation"}
                ]
            ),
        )
        result[key] = dict(
            item=identity(s, key),
            metadata=meta,
            citation_key=s["citationKeys"][key],
            fingerprints=fp,
            selected_attachment=chosen["key"] if chosen else preferred,
            pdf_path=chosen["file"]["path"] if chosen else None,
            source_quality=(
                "pdf-full"
                if chosen
                else "abstract-only" if meta.get("abstractNote") else "metadata-only"
            ),
            problem=problem,
            attachment_candidates=[dict(key=x["key"], **x["file"]) for x in pdfs],
        )
    return result


def scalar(value):
    return value[0] if isinstance(value, list) and len(value) == 1 else value


def frontmatter(text):
    m = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not m:
        return {}, None
    data = yaml.safe_load(m[1]) or {}
    if not isinstance(data, dict):
        raise ValueError("Frontmatter must be a mapping")
    return data, m


def notes(vault):
    result = []
    for p in sorted((vault / "Ideas").rglob("*.md")):
        if p.is_symlink():
            continue
        try:
            data, _ = frontmatter(p.read_text())
        except (ValueError, yaml.YAMLError):
            result.append(
                dict(path=p.relative_to(vault).as_posix(), data={}, invalid=True)
            )
            continue
        result.append(
            dict(path=p.relative_to(vault).as_posix(), data=data, invalid=False)
        )
    return result


def adopt(vault, source, candidates):
    key = source["item"]["key"]
    matches = []
    uncertain = []
    for n in candidates:
        if not n["path"].startswith("Ideas/Research/"):
            continue
        d = n["data"]
        zotkey = scalar(d.get("Zotero-Key"))
        explicit = scalar(d.get("Librarian-Identity"))
        if explicit and explicit != source["item"]:
            continue
        if zotkey == key or explicit == source["item"]:
            # Legacy personal-library keys are accepted only without contradictory library properties.
            if any(
                scalar(d.get(k, v)) != v
                for k, v in [
                    ("Zotero-Server-ID", source["item"]["server_id"]),
                    ("Zotero-Library-ID", source["item"]["library_id"]),
                ]
            ):
                uncertain.append(n)
                continue
            matches.append(n)
        elif Path(n["path"]).stem == source["citation_key"] or (
            source["metadata"].get("DOI")
            and scalar(d.get("DOI")) == source["metadata"]["DOI"]
        ):
            uncertain.append(n)
    progress = vault / "Ideas/Research/_batch-progress.md"
    historical = []
    if progress.exists():
        for line in progress.read_text().splitlines():
            cols = [x.strip() for x in line.split("|")[1:-1]]
            if len(cols) >= 6 and cols[0] == key:
                historical.append(cols[5])
    if len(matches) > 1:
        return None, "duplicate_identity"
    if matches:
        if historical and any(p != matches[0]["path"] for p in historical):
            return None, "conflicting_history"
        return matches[0], None
    if historical or uncertain:
        return None, "identity_review"
    return None, None


def relevant(fp):
    return {k: v for k, v in fp.items() if k != "annotations"}


def action(source, old, refresh=False):
    if refresh:
        return "generate"
    baseline = {**(old.get("baseline") or {}), **(old.get("published") or {})}
    if not baseline:
        return "generate"
    fp = source["fingerprints"]
    quality = old.get("published_quality") or old.get("legacy_quality")
    if fp["pdf"] and (quality != "pdf-full" or fp["pdf"] != baseline["pdf"]):
        return "generate"
    if not fp["pdf"] and quality == "pdf-full":
        # An unavailable source must not replace a better existing summary.
        pass
    elif fp["abstract"] != baseline["abstract"] and quality != "pdf-full":
        return "generate"
    if any(
        fp[k] != baseline[k] for k in ["bibliography", "citation", "membership", "tags"]
    ):
        return "metadata"
    return None
