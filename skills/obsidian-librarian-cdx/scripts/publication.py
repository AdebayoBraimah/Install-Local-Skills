"""Managed note sections and recoverable compare-and-replace publication."""

import copy
from datetime import datetime
import json
import os
from pathlib import Path
import re

import yaml
from inventory import frontmatter, relevant
from state import atomic, confined, digest, file_hash, save


def markers(name):
    return (
        "<!-- librarian:" + name + ":begin -->",
        "<!-- librarian:" + name + ":end -->",
    )


def region(text, name):
    start, end = markers(name)
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Edited or missing managed markers: " + name)
    a = text.index(start)
    b = text.index(end) + len(end)
    if b < a:
        raise ValueError("Reversed managed markers")
    return a, b, text[a:b]


def section(text, name, content, owned):
    start, end = markers(name)
    if "<!-- librarian:" in content:
        raise ValueError("Reserved managed marker in proposal")
    block = start + "\n" + content.rstrip() + "\n" + end
    if name in owned:
        a, b, current = region(text, name)
        if digest(current) != owned[name]:
            raise ValueError("User edited managed section: " + name)
        text = text[:a] + block + text[b:]
    else:
        if start in text or end in text:
            raise ValueError("Unowned managed section: " + name)
        text += "\n\n" + block + "\n"
    return text, digest(block)


def add_metadata(text, values, owned):
    data, match = frontmatter(text)
    if text.startswith("---") and not match:
        raise ValueError("Malformed frontmatter")
    if not match:
        text = "---\n\n---\n" + text
        data, match = frontmatter(text)
    # Retain every existing byte unless this workflow owns an unchanged field.
    for key, value in values.items():
        data, match = frontmatter(text)
        if key in data:
            if key not in owned:
                continue
            pattern = re.compile(
                r"^"
                + re.escape(key)
                + r":[^\n]*(?:\n(?:(?:[ \t]+[^\n]*)|(?:#[^\n]*)))*",
                re.M,
            )
            field = pattern.search(match[1])
            if not field or digest(field.group()) != owned[key]:
                if key in {"tags", "Keywords"}:
                    # A user-edited standard list becomes personal metadata.
                    # Current source values remain in separate Librarian fields.
                    owned.pop(key, None)
                    continue
                raise ValueError("Edited managed metadata: " + key)
            raw = key + ": " + json.dumps(value, ensure_ascii=False)
            offset = match.start(1)
            text = text[: offset + field.start()] + raw + text[offset + field.end() :]
            owned[key] = digest(raw)
        else:
            raw = key + ": " + json.dumps(value, ensure_ascii=False)
            # Empty frontmatter has no captured newline; insert immediately after opener.
            pos = match.end(1)
            prefix = "\n" if match[1] else ""
            text = text[:pos] + prefix + raw + text[pos:]
            owned[key] = digest(raw)
    return text, owned


def citation(src):
    m = src["metadata"]
    key = src["citation_key"]
    values = {
        "title": m.get("title", ""),
        "year": str(m.get("date", ""))[:4],
        "doi": m.get("DOI", ""),
        "url": m.get("url", ""),
    }
    authors = [
        " ".join(filter(None, [x.get("firstName"), x.get("lastName")]))
        or x.get("name", "")
        for x in m.get("creators", [])
        if x.get("creatorType", "author") == "author"
    ]
    if authors:
        values["author"] = " and ".join(authors)
    escape = (
        lambda v: str(v)
        .replace("\\", "\\textbackslash{}")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", " ")
    )
    lines = [
        "@"
        + ("article" if m["itemType"] == "journalArticle" else "misc")
        + "{"
        + key
        + ","
    ]
    lines += ["  " + k + " = {" + escape(v) + "}," for k, v in values.items() if v]
    return "## Citation\n\n```bibtex\n" + "\n".join(lines) + "\n}\n```"


def prepare(vault, entry, result):
    target = confined(vault, entry["path"])
    text = target.read_bytes().decode() if target.exists() else ""
    if not target.exists() and entry["adoption"] != "new":
        raise ValueError("Established note missing")
    if target.exists() and entry["adoption"] == "new" and not entry["sections"]:
        raise ValueError("New filename collision")
    after = copy.deepcopy(entry)
    values = {
        "Librarian-Identity": entry["item"],
        "Librarian-Citation-Key": entry["source"]["citation_key"],
        "Librarian-Source-Quality": (
            (entry.get("published_quality") or entry.get("legacy_quality"))
            if result["operation"] == "metadata"
            else entry["source"]["source_quality"]
        ),
        "Librarian-Tags": [
            t["tag"] if isinstance(t, dict) else t
            for t in entry["source"]["metadata"].get("tags", [])
        ],
    }
    if not target.exists():
        now = datetime.now()
        values.update(
            {
                "Title": "[[" + Path(entry["path"]).stem + "]]",
                "Zotero-Key": entry["item"]["key"],
                "Medium": [
                    (
                        "Paper-peer-reviewed"
                        if entry["source"]["metadata"]["itemType"]
                        in {"journalArticle", "conferencePaper", "bookSection"}
                        else "Paper-not-reviewed"
                    )
                ],
                "Category": ["Literature-Review"],
                "Date Created": now.strftime("%a-%m-%d-%Y"),
                "Time Created": now.strftime("%I:%M:%S %p").lower(),
            }
        )
    keywords = (
        result.get("keywords", entry.get("keywords", []))
        if result["operation"] == "generate"
        else entry.get("keywords", [])
    )
    values["Librarian-Keywords"] = keywords
    values.update(
        {
            "Source-Quality": values["Librarian-Source-Quality"],
            "tags": values["Librarian-Tags"],
            "Keywords": keywords,
        }
    )
    text, after["owned_metadata"] = add_metadata(text, values, after["owned_metadata"])
    text, after["sections"]["citation"] = section(
        text, "citation", citation(entry["source"]), after["sections"]
    )
    if result["operation"] == "generate":
        text, after["sections"]["content"] = section(
            text, "content", result["sections"]["content"], after["sections"]
        )
        after["published_quality"] = entry["source"]["source_quality"]
    after["previous_keywords"] = entry.get("keywords", [])
    after["keywords"] = keywords
    after["published"] = copy.deepcopy(entry["observed"])
    if result["operation"] == "metadata":
        after["published"] = copy.deepcopy(entry.get("published") or {})
        for k in ["bibliography", "citation", "membership", "tags"]:
            after["published"][k] = entry["observed"][k]
    after["adoption"] = "managed" if entry["adoption"] == "new" else entry["adoption"]
    after["pending"] = [
        x for x in entry["pending"] if x not in {"generate", "metadata"}
    ]
    if "link" not in after["pending"]:
        after["pending"].append("link")
    after.pop("proposal", None)
    after["revision"] += 1
    after["destination_hash"] = digest(text)
    writes = []
    for asset in result.get("assets", []):
        staged = confined(vault, asset["staged_path"])
        dest = confined(vault, asset["path"])
        data = staged.read_bytes()
        if digest(data) != asset["sha256"]:
            raise ValueError("Staged asset changed")
        if dest.exists() and file_hash(dest) != digest(data):
            raise ValueError("Asset filename collision")
        writes.append(
            dict(
                path=asset["path"],
                before=file_hash(dest),
                after=digest(data),
                content_hex=data.hex(),
            )
        )
    writes.append(
        dict(
            path=entry["path"],
            before=file_hash(target),
            after=digest(text),
            content_hex=text.encode().hex(),
        )
    )
    return after, writes


def apply_transaction(vault, root, state, tx):
    # Check every destination before any replacement; recovery accepts only before or after.
    for w in tx["writes"]:
        actual = file_hash(confined(vault, w["path"]))
        if actual not in {w["before"], w["after"]}:
            tx["status"] = "conflict"
            atomic(root / "transactions" / (tx["id"] + ".json"), tx)
            key = tx.get("key")
            if key:
                state["items"][key]["blocked"] = "recovery_conflict"
            save(root, state)
            raise ValueError(
                "Publication recovery found a concurrent edit: " + w["path"]
            )
    for index, w in enumerate(tx["writes"]):
        target = confined(vault, w["path"])
        if file_hash(target) != w["after"]:
            if os.environ.get("LIBRARIAN_TEST_CRASH") == "before_replace":
                os._exit(91)
            atomic(target, bytes.fromhex(w["content_hex"]))
            if os.environ.get("LIBRARIAN_TEST_CRASH") == "after_replace":
                os._exit(92)
    if tx.get("key"):
        state["items"][tx["key"]] = tx["checkpoint"]
    state.setdefault("links", {}).update(tx.get("link_checkpoints", {}))
    state["transactions"][tx["id"]] = "applied"
    if tx.get("result"):
        run, token = tx["result"]
        state["runs"][run]["results"][token]["publication"] = "applied"
    save(root, state)
    tx["status"] = "applied"
    atomic(root / "transactions" / (tx["id"] + ".json"), tx)


def transact(vault, root, state, key, after, writes, txid, result=None):
    tx = dict(
        schema_version=1,
        id=txid,
        key=key,
        checkpoint=after,
        writes=writes,
        status="pending",
        result=result,
    )
    atomic(root / "transactions" / (txid + ".json"), tx)
    apply_transaction(vault, root, state, tx)


def recover(vault, root, state):
    for path in sorted((root / "transactions").glob("*.json")):
        tx = json.loads(path.read_text())
        if (
            tx["status"] == "pending"
            and state["transactions"].get(tx["id"]) != "applied"
        ):
            apply_transaction(vault, root, state, tx)


def conflict(root, state, run, token, result, reason):
    key = result["item"]["key"]
    state["items"][key]["blocked"] = "publication_conflict"
    state["items"][key]["errors"].append(
        dict(stage=result["operation"], reason=reason, run=run, transient=False)
    )
    state["runs"][run]["results"][token]["publication"] = "conflict"
    atomic(
        root / "conflicts" / (token + ".json"),
        dict(schema_version=1, reason=reason, proposal=result),
    )
    save(root, state)


def terms(data):
    values = []
    for field in ["Keywords", "Librarian-Keywords"]:
        value = data.get(field, []) or []
        values += value if isinstance(value, list) else [value]
    return {
        str(x).strip().removeprefix("[[").removesuffix("]]").split("|")[0].strip()
        for x in values
        if isinstance(x, str) and x.strip()
    }


def link(vault, root, state, key, run_id):
    from inventory import notes, scalar

    if os.environ.get("LIBRARIAN_TEST_LINK_FAIL"):
        raise OSError("Transient linker unavailable")
    x = state["items"][key]
    entries = {n["path"]: n for n in notes(vault) if not n["invalid"]}
    if x["path"] not in entries:
        raise ValueError("Published note missing for linking")
    work = {
        p: n
        for p, n in entries.items()
        if scalar(n["data"].get("Zotero-Key"))
        or n["data"].get("Book-ID")
        or n["data"].get("Parent-Book")
    }
    changed = terms(
        {"Keywords": x.get("keywords", []) + x.get("previous_keywords", [])}
    )

    def work_id(n):
        d = n["data"]
        return str(
            scalar(d.get("Book-ID"))
            or scalar(d.get("Parent-Book"))
            or scalar(d.get("Zotero-Key"))
            or n["path"]
        )

    termmap = {p: terms(n["data"]) for p, n in entries.items()}
    affected = {x["path"]} | {p for p in work if termmap[p] & changed}
    affected |= set(x.get("linked_paths", [])) & entries.keys()
    hubs = {}
    for concept in changed:
        matches = [p for p in entries if Path(p).stem == concept and p not in work]
        if len(matches) > 1:
            raise ValueError("Ambiguous concept hub: " + concept)
        if matches:
            hubs[concept] = matches[0]
            continue
        supporters = [p for p in work if concept in termmap[p]]
        substantive = len(concept.strip()) >= 3 and concept.casefold() not in {
            "paper",
            "papers",
            "research",
            "method",
            "methods",
            "misc",
            "literature",
        }
        if (
            substantive
            and len({work_id(work[p]) for p in supporters}) >= 3
            and re.fullmatch(r"[^/\\\x00-\x1f\[\]|#]+", concept)
        ):
            path = "Ideas/" + concept + ".md"
            if confined(vault, path).exists():
                raise ValueError("New hub filename collision")
            hubs[concept] = path
            entries[path] = dict(path=path, data={"Keywords": [concept]})
            termmap[path] = {concept}
    affected |= set(hubs.values())
    writes = []
    checkpoints = {}
    for path in sorted(affected):
        if path not in entries:
            continue
        d = entries[path]["data"]
        # Existing book/chapter content and linking remain owned by long-work.
        if d.get("Book-ID") or d.get("Parent-Book"):
            continue
        own_terms = termmap[path]
        hub_concepts = {c for c, p in hubs.items() if p == path}
        if hub_concepts:
            own_terms |= hub_concepts
        destinations = {p for p in work if p != path and termmap[p] & own_terms}
        if path in work:
            destinations |= {
                p
                for p in entries
                if p not in work and Path(p).stem in own_terms and p != path
            }
        destinations = {
            p
            for p in destinations
            if confined(vault, p).is_file() or p in hubs.values()
        }
        target = confined(vault, path)
        text = (
            target.read_bytes().decode()
            if target.exists()
            else "---\nCategory: [Concept]\n---\n\n# " + Path(path).stem + "\n"
        )
        owned = state.get("links", {}).get(path)
        body = "## Related works\n\n" + "\n".join(
            "- [[" + str(Path(p).with_suffix("")) + "]]" for p in sorted(destinations)
        )
        proposed, h = section(text, "links", body, {"links": owned} if owned else {})
        checkpoints[path] = h
        if proposed != text:
            writes.append(
                dict(
                    path=path,
                    before=file_hash(target),
                    after=digest(proposed),
                    content_hex=proposed.encode().hex(),
                )
            )
    after = copy.deepcopy(x)
    after["pending"] = [p for p in x["pending"] if p != "link"]
    after["linked_paths"] = sorted(affected)
    after["destination_hash"] = next(
        (w["after"] for w in writes if w["path"] == x["path"]),
        file_hash(confined(vault, x["path"])),
    )
    after["revision"] += 1
    txid = digest([run_id, key, "links", x["revision"]])[:24]
    tx = dict(
        schema_version=1,
        id=txid,
        key=key,
        checkpoint=after,
        writes=writes,
        status="pending",
        result=None,
        link_checkpoints=checkpoints,
    )
    atomic(root / "transactions" / (txid + ".json"), tx)
    apply_transaction(vault, root, state, tx)


def progress(vault, root, state):
    path = "Ideas/Research/_batch-progress.md"
    target = confined(vault, path)
    text = (
        target.read_bytes().decode()
        if target.exists()
        else "# Batch summarization progress\n"
    )

    def cell(value):
        return str(value).replace("|", "/").replace("\n", " ")

    rows = {}
    collection_members = {"Unfiled": []}
    for key, x in state["items"].items():
        src = x["source"]
        memberships = src["metadata"].get("collections", [])
        names = {c["key"]: c["path"] for c in state["snapshot"]["collections"]}
        cs = [names.get(c, c) for c in memberships] or ["Unfiled"]
        status = x.get("blocked") or (
            "pending " + ",".join(x["pending"])
            if x["pending"]
            else "published" if x.get("published_quality") else x["adoption"]
        )
        if src["metadata"]["itemType"] == "book":
            status = x.get("book_result", {}).get("status", "deferred")
        rows[key] = (
            "| "
            + " | ".join(
                map(
                    cell,
                    [
                        key,
                        src["citation_key"],
                        ", ".join(cs),
                        status,
                        x.get("published_quality")
                        or x.get("legacy_quality")
                        or "unverified",
                        x["path"],
                    ],
                )
            )
            + " |"
        )

    def table(text, label, header, rows, keyed=False):
        pattern = re.compile(
            r"^\| " + re.escape(label) + r" \|[^\n]*\n\|[- |:]+\|\n(?:\|[^\n]*\|\n?)*",
            re.M,
        )
        m = pattern.search(text)
        if keyed and m:
            for line in m.group().splitlines()[2:]:
                key = line.split("|")[1].strip()
                if key not in rows:
                    rows[key] = line
        body = header + "\n" + "\n".join(rows[k] for k in sorted(rows)) + "\n"
        if m:
            return text[: m.start()] + body + text[m.end() :]
        return text + "\n\n" + body

    text = table(
        text,
        "Zotero-Key",
        "| Zotero-Key | CitationKey | Collection | Status | Source-Quality | Note Path |\n|---|---|---|---|---|---|",
        rows,
        True,
    )
    from inventory import PAPERS

    cmap = {c["key"]: c for c in state["snapshot"]["collections"]}
    collection_members.update({c["path"]: [] for c in cmap.values()})
    for row in state["snapshot"]["items"]:
        if row["parentItem"] or row["metadata"]["itemType"] not in PAPERS | {"book"}:
            continue
        membership = set(row["metadata"].get("collections", []))
        pending = list(membership)
        while pending:
            parent = cmap[pending.pop()]["parentCollection"]
            if parent and parent not in membership:
                membership.add(parent)
                pending.append(parent)
        groups = [cmap[c]["path"] for c in membership] or ["Unfiled"]
        entry = state["items"].get(row["key"], dict(pending=["unprocessed"]))
        for group in groups:
            collection_members[group].append(entry)
    counts = {}
    for c, members in collection_members.items():
        total = len(members)
        done = sum(
            bool(x.get("published_quality"))
            and not x["pending"]
            and not x.get("blocked")
            for x in members
        )
        errors = sum(bool(x.get("blocked")) for x in members)
        counts[c] = (
            f"| {cell(c)} | {total} | {done} | {total-done} | {errors} | librarian |"
        )
    text = table(
        text,
        "Collection",
        "| Collection | Total | Summarized | Pending | Errors | Phase |\n|---|---|---|---|---|---|",
        counts,
    )
    if file_hash(target) == digest(text):
        return
    txid = "progress-" + digest(text)[:20]
    transact(
        vault,
        root,
        state,
        None,
        None,
        [
            dict(
                path=path,
                before=file_hash(target),
                after=digest(text),
                content_hex=text.encode().hex(),
            )
        ],
        txid,
    )
