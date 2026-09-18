#!/usr/bin/env python3
"""Versioned CLI for reader-driven long-work study."""
import argparse
import json
import sys
import uuid
from pathlib import Path
from state import *
from sources import resolve, inspect, collection_items
from publication import publish, verify, reconcile


def _prepare(a, root):
    if a.collection:
        return {"schema_version": 1, "items": collection_items(a.collection)}
    path, meta, identity = resolve(a.selector, a.library_id, a.attachment)
    h = file_hash(path)
    info = inspect(path)
    matches = []
    for p in (root / "works").glob("*/manifest.json"):
        m = json.loads(p.read_text())
        if (
            (identity and m.get("identity") == identity)
            or (
                not identity
                and not m.get("identity")
                and (m["source_path"] == str(path) or m["source_hash"] == h)
            )
            or a.book_id == m["book_id"]
        ):
            matches.append(m)
    if len(matches) > 1:
        raise ValueError(
            "Multiple local identities match; use distinct vault or resolve registry"
        )
    if a.dry_run:
        return {
            "schema_version": 1,
            "source_path": str(path),
            "source_hash": h,
            "metadata": meta,
            **info,
            "existing_book_id": matches[0]["book_id"] if matches else None,
        }
    book = (
        matches[0]["book_id"]
        if matches
        else "book-" + (digest(identity)[:20] if identity else uuid.uuid4().hex[:20])
    )
    with lock(root, book):
        if matches:
            m = load(root, book)
            reconcile(a.vault, root, m)
            require(
                not identity or identity == m.get("identity"),
                "Cannot change Zotero identity with --book-id",
            )
            if m["source_hash"] != h:
                m.pop("label_evidence", None)
                atomic(
                    root / "works" / book / "history" / (m["source_hash"] + ".json"),
                    m,
                )
                m["previous_chapters"] = list(
                    {
                        c["id"]: c
                        for c in m.get("previous_chapters", []) + m["chapters"]
                    }.values()
                )
                m["chapters"] = []
                m["chunks"] = {}
                m["results"] = {}
                m["synthesis"] = {}
                m["mapped"] = False
                m["scope"] = []
                m["stale"] = True
            if m["source_hash"] == h and m.get("label_evidence"):
                info["labels"] = m["labels"]
            m.update(source_path=str(path), source_hash=h, metadata=meta, **info)
        else:
            key = safe_name(meta.get("citationKey") or a.citation_key or book)
            index = a.index_path
            if not index and meta.get("key"):
                import re

                found = []
                for p in (a.vault / "Ideas").rglob("*.md"):
                    if re.search(
                        r"^Zotero-Key:\s*[\"\']?"
                        + re.escape(meta["key"])
                        + r"[\"\']?\s*$",
                        p.read_text(),
                        re.M,
                    ):
                        found.append(p)
                if len(found) > 1:
                    raise ValueError(
                        "Multiple legacy indexes match; supply --index-path"
                    )
                if found:
                    index = str(found[0].relative_to(a.vault))
            index = index or f"Ideas/Research/{key}.md"
            contained(a.vault, index)
            m = dict(
                schema_version=1,
                book_id=book,
                identity=identity,
                source_path=str(path),
                source_hash=h,
                metadata=meta,
                index_path=index,
                note_prefix=key,
                chapter_dir=f"Ideas/Research/Books/{key}",
                chapters=[],
                chunks={},
                results={},
                published={},
                mapped=False,
                scope=[],
                synthesis={},
                conflicts=[],
                **info,
            )
        save(root, m)
        if m.get("stale"):
            publish(a.vault, root, m)
        return report(m)


def prepare(a, root):
    if a.dry_run or a.collection:
        return _prepare(a, root)
    with lock(root, "registry"):
        return _prepare(a, root)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vault", type=Path, required=True)
    sub = p.add_subparsers(dest="op", required=True)
    q = sub.add_parser("prepare")
    q.add_argument("selector", nargs="?", default="")
    q.add_argument("--collection")
    q.add_argument("--library-id")
    q.add_argument("--attachment")
    q.add_argument("--book-id")
    q.add_argument("--citation-key")
    q.add_argument("--index-path")
    q.add_argument("--dry-run", action="store_true")
    for op in ["next", "record", "publish", "status", "verify"]:
        q = sub.add_parser(op)
        q.add_argument("book")
        q.add_argument("--chapters", nargs="+")
        q.add_argument("--input", type=Path)
        q.add_argument("--ocr", action="store_true")
    a = p.parse_args()
    a.vault = a.vault.resolve()
    root = a.vault / ".long-work-summarizer"
    try:
        if a.op == "prepare":
            result = prepare(a, root)
        else:
            with lock(root, safe_name(a.book)):
                m = load(root, a.book)
                reconcile(a.vault, root, m)
                if file_hash(m["source_path"]) != m["source_hash"]:
                    raise ValueError("Source changed; prepare and remap first")
                if a.op in ["status", "next"] and any(
                    k != "index"
                    and p["coverage"] == "full"
                    and (k not in m["results"] or p["source_hash"] != m["source_hash"])
                    for k, p in m["published"].items()
                ):
                    publish(a.vault, root, m)
                if a.chapters:
                    select_scope(m, a.chapters)
                if a.op == "record":
                    if not a.input:
                        raise ValueError("--input required")
                    record(m, json.loads(a.input.read_text()))
                    save(root, m)
                    if m["published"]:
                        publish(a.vault, root, m)
                result = (
                    next_chunk(m, root, a.ocr)
                    if a.op == "next"
                    else (
                        publish(a.vault, root, m)
                        if a.op == "publish"
                        else verify(a.vault, root, m) if a.op == "verify" else report(m)
                    )
                )
                if a.op in ["record", "next"] or a.chapters:
                    save(root, m)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        expected = isinstance(e, (ValueError, OSError, KeyError, TypeError))
        error = str(e) if expected else type(e).__name__ + ": " + str(e)
        print(
            json.dumps(
                dict(
                    schema_version=1,
                    status="blocked" if expected else "failed",
                    error=error,
                    output_paths=[],
                    coverage=None,
                    unresolved=[error],
                    resume_selector=getattr(a, "book", None)
                    or getattr(a, "selector", None)
                    or getattr(a, "collection", None),
                )
            )
        )
        return 2 if expected else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
