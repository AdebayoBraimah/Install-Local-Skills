"""Read-only source adapters and hash-keyed extraction."""

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
import fitz
from state import atomic, digest, file_hash

CLI = os.environ.get(
    "ZOTERO_CLI", str(Path.home() / "anaconda3/bin/cli-anything-zotero")
)


def zotero(*args):
    for attempt in range(3):
        try:
            p = subprocess.run(
                [CLI, "--json", *args], capture_output=True, text=True, timeout=60
            )
        except subprocess.TimeoutExpired:
            if attempt == 2:
                raise ValueError("Zotero lookup timed out after three attempts")
            time.sleep(0.2 * (attempt + 1))
            continue
        if p.returncode == 0:
            return json.loads(p.stdout)
        if attempt < 2 and any(
            s in p.stderr.lower()
            for s in ["timeout", "busy", "unavailable", "connection"]
        ):
            time.sleep(0.2 * (attempt + 1))
            continue
        raise ValueError("Zotero lookup failed: " + p.stderr.strip())


def identity():
    with urllib.request.urlopen("http://127.0.0.1:23119/api/", timeout=10) as r:
        server = r.headers.get("Zotero-Server-ID")
    if not server:
        raise ValueError("Supply --library-id; Zotero server identity unavailable")
    return "local:" + server + ":users/0"


def collection_items(name):
    items = zotero("export", "-c", name, "-f", "json")
    if not isinstance(items, list):
        raise ValueError("Expected collection array")
    seen = set()
    result = []
    for item in items:
        key = item.get("key") or item.get("itemKey")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "key": key,
                "route": (
                    "long-work-summarizer-cdx"
                    if item.get("itemType") == "book"
                    else "paper-pipeline"
                ),
                "itemType": item.get("itemType"),
            }
        )
    return result


def resolve(selector, library_id=None, attachment=None):
    path = Path(selector).expanduser()
    if path.is_file():
        return (
            path.resolve(),
            {"title": None, "citationKey": None, "citation": None},
            None,
        )
    library = library_id or identity()
    # info supports item keys; resolve BBT keys by exact exported citation key.
    meta = None
    if len(selector) == 8 and selector.isalnum():
        try:
            meta = zotero("info", selector)
        except ValueError:
            pass  # Eight-character citation keys are valid too.
    if meta is None:
        items = zotero("items", "-t", "book", "--all")
        found = [
            x for x in items if selector in [x.get("citationKey"), x.get("citekey")]
        ]
        if len(found) != 1:
            raise ValueError("Citation key missing or ambiguous")
        meta = zotero("info", found[0]["key"])
    if meta.get("itemType") != "book":
        raise ValueError("Source is not a Zotero book")
    key = meta["key"]
    candidates = [
        a
        for a in zotero("attachments", key)
        if a.get("contentType") == "application/pdf"
        or str(a.get("full_path", "")).lower().endswith(".pdf")
    ]
    if attachment:
        candidates = [a for a in candidates if a.get("key") == attachment]
    if len(candidates) != 1:
        raise ValueError("Missing or ambiguous PDF attachments; select --attachment")
    path = Path(candidates[0].get("full_path") or "")
    if not path.is_file():
        raise ValueError("Selected PDF attachment is unavailable")
    citation = zotero("cite", key)
    meta["citationKey"] = citation.get("citationKey") or citation.get("citekey")
    p = subprocess.run(
        [CLI, "export", key, "-f", "bibtex"], capture_output=True, text=True, timeout=60
    )
    if p.returncode:
        raise ValueError("Citation export failed")
    meta["citation"] = p.stdout
    meta["library_id"] = library
    meta["attachment_key"] = candidates[0]["key"]
    if not library_id and identity() != library:
        raise ValueError("Zotero profile changed during lookup")
    return path.resolve(), meta, library + ":" + key


def inspect(path):
    with fitz.open(path) as d:
        if d.needs_pass:
            raise ValueError("Encrypted PDF requires an unlocked copy")
        return {
            "page_count": len(d),
            "bookmarks": d.get_toc(),
            "labels": [p.get_label() or None for p in d],
        }


def extract(m, root, pages, force_ocr=False):
    if file_hash(m["source_path"]) != m["source_hash"]:
        raise ValueError("Source changed; prepare and remap first")
    output = []
    settings = {
        "engine": fitz.VersionBind,
        "language": "eng",
        "dpi": 200,
        "force": force_ocr,
        "tessdata": os.environ.get("TESSDATA_PREFIX", "/opt/homebrew/share/tessdata"),
    }
    with fitz.open(m["source_path"]) as d:
        for n in pages:
            cache = (
                Path(root)
                / "cache"
                / m["source_hash"]
                / (
                    str(n)
                    + "-"
                    + digest(json.dumps(settings, sort_keys=True))[:12]
                    + ".json"
                )
            )
            if cache.exists():
                data = json.loads(cache.read_text())
            else:
                page = d[n - 1]
                text = page.get_text()
                ocr = False
                error = None
                if force_ocr or len(text.strip()) < 30 or "\ufffd" in text:
                    try:
                        tp = page.get_textpage_ocr(
                            language="eng",
                            dpi=200,
                            full=True,
                            tessdata=settings["tessdata"],
                        )
                        text = page.get_text(textpage=tp)
                        ocr = True
                    except Exception as e:
                        error = "OCR unavailable: " + str(e)
                data = {
                    "pdf_page": n,
                    "printed_label": m["labels"][n - 1],
                    "text": text,
                    "ocr": ocr,
                    "error": error,
                }
                atomic(cache, data)
            data["printed_label"] = m["labels"][n - 1]
            output.append(data)
    return output
