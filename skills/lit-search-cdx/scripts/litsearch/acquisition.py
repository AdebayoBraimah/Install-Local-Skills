"""Read-only Zotero matching, validated downloads and manual import bundles."""

import copy
from functools import lru_cache
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlparse, urljoin
import requests
from .records import title_key, doi, arxiv, same, bibtex
from .state import Blocked, digest

ZOTERO = str(Path.home() / "anaconda3/bin/cli-anything-zotero")


def zotero(*args):
    try:
        p = subprocess.run(
            [ZOTERO, "--json", *args], capture_output=True, text=True, timeout=45
        )
        if p.returncode:
            raise ValueError()
        return json.loads(p.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise Blocked("zotero_unavailable") from None


@lru_cache(maxsize=1)
def zotero_inventory():
    rows = zotero("items", "-n", "100000")
    if len(rows) >= 100000:
        raise Blocked("zotero_inventory_incomplete")
    return rows


def zotero_match(r):
    rows = zotero_inventory()
    matches = []
    for row in rows:
        data = row
        names = data.get("creators", [])
        if names and isinstance(names[0], dict):
            names = [
                " ".join([a.get("firstName", ""), a.get("lastName", "")]).strip()
                for a in names
            ]
        d = {"doi": doi(data.get("DOI")), "arxiv": arxiv(data.get("url", ""))}
        exact = same(r, d)
        authors = {title_key(x.split()[-1]) for x in r.get("authors", []) if x.split()}
        author_match = bool(
            authors & {title_key(x.split()[-1]) for x in names if x.split()}
        )
        if exact or (
            title_key(r["title"]) == title_key(data.get("title")) and author_match
        ):
            matches.append((data, names))
    if len(matches) > 1:
        raise Blocked("ambiguous_zotero_match")
    if not matches:
        return None
    d, names = matches[0]
    d = zotero("info", d["key"])
    cite = zotero("cite", d["key"])
    return {
        "zotero": {"key": d["key"], "attachments": d.get("attachments", [])},
        "title": d["title"],
        "authors": names,
        "doi": doi(d.get("DOI")) or r.get("doi"),
        "year": (
            int(d["date"][:4])
            if re.match(r"^\d{4}", d.get("date", ""))
            else r.get("year")
        ),
        "venue": d.get("publicationTitle") or r.get("venue"),
        "citation_key": cite.get("citationKey") or cite.get("citekey"),
        "metadata_preference": "zotero",
    }


def public_url(url):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise Blocked("unsafe_download_url")
    try:
        addresses = socket.getaddrinfo(
            p.hostname,
            p.port or (443 if p.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
        if any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise Blocked("unsafe_download_host")
    except OSError:
        raise Blocked("download_host_unavailable") from None
    return p


def download_bytes(url, max_bytes=100 * 1024 * 1024, headers=None):
    session = requests.Session()
    session.trust_env = False
    original = urlparse(url).hostname
    start = time.monotonic()
    try:
        for redirect in range(6):
            p = public_url(url)
            # Credentials are allowed only for the named content service and
            # are removed on every redirect, including same-host redirects.
            auth = (
                headers
                if redirect == 0
                and original == "content.openalex.org"
                and p.scheme == "https"
                else {}
            )
            with session.get(
                url,
                headers=auth or {},
                stream=True,
                allow_redirects=False,
                timeout=(10, 30),
            ) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get("Location", ""))
                    continue
                if response.status_code != 200:
                    raise Blocked(
                        "pdf_unavailable", {"http_status": response.status_code}
                    )
                chunks = []
                size = 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > max_bytes or time.monotonic() - start > 120:
                        raise Blocked("download_limit")
                    chunks.append(chunk)
                return b"".join(chunks), url
        raise Blocked("redirect_limit")
    except requests.RequestException:
        raise Blocked("download_failed") from None
    finally:
        session.close()


def verify_pdf(path, r):
    path = Path(path)
    try:
        if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
            return {"status": "invalid"}
        with path.open("rb") as f:
            if not f.read(8).startswith(b"%PDF-"):
                return {"status": "invalid"}
        info = subprocess.run(
            ["pdfinfo", str(path)], capture_output=True, text=True, timeout=20
        )
        if info.returncode:
            return {"status": "invalid"}
        text = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "2", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if text.returncode:
            return {"status": "uncertain", "reason": "text_unavailable"}
        head = text.stdout.split("\f", 1)[0][:12000]
        # Use front matter before an abstract/introduction/reference heading. A
        # citation buried in the body is not evidence of document identity.
        front = re.split(
            r"(?im)^\s*(?:abstract|introduction|references|bibliography)\b",
            head,
            maxsplit=1,
        )[0][:2500]
        expected = title_key(r["title"])
        metadata = re.search(r"^Title:\s*(.*)", info.stdout, re.M)
        metadata = metadata[1].strip() if metadata else ""
        found_dois = {
            doi(x.rstrip(".,;)"))
            for x in re.findall(r"10\.\d{4,9}/[^\s<>]+", front, re.I)
        }
        exact_doi = bool(r.get("doi") and doi(r["doi"]) in found_dois)
        title_match = len(expected) >= 12 and expected in title_key(front)
        if (
            metadata
            and len(title_key(metadata)) >= 12
            and title_key(metadata) not in ("untitled", "microsoftword")
            and title_key(metadata) != expected
        ):
            status = "mismatch"
        elif title_match or (exact_doi and title_key(metadata) == expected):
            status = "verified"
        else:
            status = "uncertain"
        return {
            "status": status,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "evidence": {
                "title_match": title_match,
                "doi_match": exact_doi,
                "pdf_title": metadata,
            },
            "path": str(path.resolve()),
        }
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "invalid", "reason": "validation_unavailable"}


def select(records, ids):
    known = {r["id"]: r for r in records}
    if not ids or any(i not in known for i in ids):
        raise Blocked("explicit_valid_selection_required")
    return [copy.deepcopy(known[i]) for i in dict.fromkeys(ids)]


def fetch(providers, run, records, ids):
    selected = select(records, ids)
    remaining = []
    state = providers.state
    for r in selected:
        r.pop("download", None)
        try:
            matched = zotero_match(r)
            if matched:
                r.update(matched)
        except Blocked as e:
            remaining.append({"id": r["id"], "reason": e.code})
            continue
        locations = [
            {"path": x["full_path"], "source": "zotero", "version": None}
            for x in r.get("zotero", {}).get("attachments", [])
            if x.get("full_path") and x.get("contentType") == "application/pdf"
        ]
        locations += sorted(
            r.get("pdf_locations", []),
            key=lambda x: x.get("source") == "openalex_cache",
        )
        errors = []
        for loc in locations:
            token = digest([r["id"], loc])
            destination = state.root / "pdfs" / f"{token}.pdf"
            destination.parent.mkdir(exist_ok=True)
            with state.request_lock(token):
                if destination.exists():
                    checked = verify_pdf(destination, r)
                    if checked["status"] == "verified":
                        r["download"] = {**checked, "source": loc}
                        break
                attempt = None
                try:
                    if loc.get("path"):
                        if Path(loc["path"]).stat().st_size > 100 * 1024 * 1024:
                            raise Blocked("download_limit")
                        data = Path(loc["path"]).read_bytes()
                        source = loc["path"]
                    else:
                        headers = {}
                        if loc.get("source") == "openalex_cache":
                            parsed = urlparse(loc["url"])
                            if (
                                parsed.hostname != "content.openalex.org"
                                or parsed.scheme != "https"
                            ):
                                raise Blocked("invalid_content_host")
                            headers, attempt = providers.content_headers(run)
                        data, source = download_bytes(loc["url"], headers=headers)
                    fd, temp = tempfile.mkstemp(suffix=".pdf", dir=state.root)
                    with os.fdopen(fd, "wb") as f:
                        f.write(data)
                    checked = verify_pdf(temp, r)
                    if checked["status"] == "verified":
                        os.replace(temp, destination)
                        checked["path"] = str(destination)
                        r["download"] = {
                            **checked,
                            "source": loc,
                            "resolved_url": source,
                        }
                        if attempt:
                            state.finish(attempt, "complete")
                        break
                    quarantine = state.root / "quarantine"
                    quarantine.mkdir(exist_ok=True)
                    os.replace(temp, quarantine / f"{token}.pdf")
                    errors.append(
                        {
                            "source": loc,
                            "reason": checked["status"],
                            "quarantine": str(quarantine / f"{token}.pdf"),
                        }
                    )
                    if attempt:
                        state.finish(attempt, "invalid_pdf")
                except (Blocked, OSError) as e:
                    errors.append(
                        {
                            "source": loc,
                            "reason": (
                                e.code if isinstance(e, Blocked) else "file_unavailable"
                            ),
                        }
                    )
        if r.get("download", {}).get("status") != "verified":
            r["download"] = {"status": "unresolved", "attempts": errors}
            remaining.append(
                {"id": r["id"], "reason": "pdf_unresolved", "attempts": errors}
            )
    return {
        "schema_version": 1,
        "run_id": run,
        "status": "partial" if remaining else "complete",
        "records": selected,
        "remaining_work": remaining,
        "completed": [
            r["id"]
            for r in selected
            if r.get("download", {}).get("status") == "verified"
        ],
        "usage": state.usage(run),
    }


def bundle(state, run, records, ids):
    selected = select(records, ids)
    destination = (
        state.root / "runs" / digest(run)[:20] / "bundles" / digest(selected)[:20]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    unresolved = []
    existing = []
    entries = []
    with state.request_lock(str(destination)):
        staging = Path(tempfile.mkdtemp(prefix=".bundle-", dir=destination.parent))
        (staging / "pdfs").mkdir()
        try:
            for r in selected:
                matched = zotero_match(r)
                if matched:
                    r.update(matched)
                if r.get("zotero"):
                    existing.append(
                        {
                            "id": r["id"],
                            "zotero": r["zotero"],
                            "citation_key": r.get("citation_key"),
                            "manual_attachment": (
                                r.get("download")
                                if not any(
                                    a.get("contentType") == "application/pdf"
                                    and a.get("full_path")
                                    and verify_pdf(a["full_path"], r)["status"]
                                    == "verified"
                                    for a in r["zotero"].get("attachments", [])
                                )
                                else None
                            ),
                        }
                    )
                    continue
                attachment = None
                download = r.get("download", {})
                if download.get("path"):
                    relative = "pdfs/" + digest(r["id"])[:20] + ".pdf"
                    try:
                        shutil.copyfile(download["path"], staging / relative)
                    except OSError:
                        checked = {"status": "unavailable"}
                    else:
                        checked = verify_pdf(staging / relative, r)
                    if checked["status"] == "verified":
                        attachment = relative
                        r["download"] = {**download, "sha256": checked["sha256"]}
                    else:
                        (staging / relative).unlink(missing_ok=True)
                        unresolved.append(
                            {"id": r["id"], "reason": "attachment_" + checked["status"]}
                        )
                else:
                    unresolved.append({"id": r["id"], "reason": "pdf_unresolved"})
                entry = bibtex(r, attachment)
                if entry:
                    entries.append(entry)
                else:
                    unresolved.append(
                        {"id": r["id"], "reason": "insufficient_verified_metadata"}
                    )
            manifest = {
                "schema_version": 1,
                "run_id": run,
                "records": selected,
                "existing_zotero": existing,
                "unresolved": unresolved,
                "manual_import_required": True,
            }
            destination = destination.parent / digest(manifest)[:20]
            (staging / "library.bib").write_text("\n".join(entries))
            (staging / "manifest.json").write_text(json.dumps(manifest, indent=2))
            if destination.exists():
                shutil.rmtree(staging)
            else:
                os.replace(staging, destination)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return {
        "schema_version": 1,
        "run_id": run,
        "status": "partial" if unresolved else "complete",
        "records": selected,
        "bundle": str(destination),
        "remaining_work": unresolved,
        "existing_zotero": existing,
        "usage": state.usage(run),
    }
