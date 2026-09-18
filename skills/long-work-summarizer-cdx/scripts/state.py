"""Durable state and conservative coverage contracts."""

import contextlib
import fcntl
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

VERSION = 1


def digest(data):
    return hashlib.sha256(
        data if isinstance(data, bytes) else data.encode()
    ).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        value
        if isinstance(value, str)
        else json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    )
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextlib.contextmanager
def lock(root, name):
    folder = Path(root) / "locks"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / (name + ".lock")).open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another writer owns this book; retry later")
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def safe_name(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,150}", value
    ):
        raise ValueError("Unsafe or empty identifier")
    return value


def contained(vault, relative):
    p = (Path(vault) / relative).resolve()
    if not p.is_relative_to(Path(vault).resolve()):
        raise ValueError("Path escapes vault")
    return p


def load(root, book):
    m = json.loads(
        (Path(root) / "works" / safe_name(book) / "manifest.json").read_text()
    )
    if m.get("schema_version") != VERSION:
        raise ValueError("Unsupported manifest version")
    return m


def save(root, m):
    atomic(Path(root) / "works" / m["book_id"] / "manifest.json", m)
    atomic(Path(root) / "works" / m["book_id"] / "run-result.json", report(m))


def report(m):
    read = set()
    for x in m["chunks"].values():
        if not x["unresolved"]:
            read.update(x["pages"])
    substantive = {p for c in m["chapters"] for p in range(c["start"], c["end"] + 1)}
    scope = m["scope"] or [c["id"] for c in m["chapters"]]
    done = [
        c
        for c in scope
        if c in m["results"]
        and m["published"].get(c, {}).get("source_hash") == m["source_hash"]
        and m["published"].get(c, {}).get("result_hash")
        == digest(json.dumps(m["results"][c], sort_keys=True))
    ]
    syn = m.get("synthesis", {})
    synth_ok = bool(
        syn
        and syn.get("chapters") == scope
        and syn.get("verified")
        and m["published"].get("index", {}).get("synthesis_hash")
        == digest(json.dumps(syn, sort_keys=True))
    )
    full = bool(
        m["mapped"]
        and substantive <= read
        and len(done) == len(m["chapters"])
        and set(scope) == {c["id"] for c in m["chapters"]}
        and synth_ok
    )
    coverage = (
        "full"
        if full
        else "partial" if read else "scanned" if m["mapped"] else "unread"
    )
    unresolved = []
    if not m["mapped"]:
        unresolved.append("Source mapping required")
    unresolved += [
        f'Chapter {c["id"]}: boundary unresolved'
        for c in m["chapters"]
        if c["id"] in scope and not c["confirmed"]
    ]
    unresolved += [
        f"Chapter {c}: reading or publication incomplete"
        for c in scope
        if c not in done
    ]
    unresolved += [
        f'Chunk {k}: {x["unresolved"]}'
        for k, x in m["chunks"].items()
        if x["unresolved"] and x["chapter_id"] in scope
    ]
    unresolved += m.get("conflicts", [])
    if not synth_ok:
        unresolved.append("Verified scope synthesis not published")
    blocked = (
        not m["mapped"]
        or m.get("conflicts")
        or any(not c["confirmed"] for c in m["chapters"] if c["id"] in scope)
        or any(
            x["unresolved"] for x in m["chunks"].values() if x["chapter_id"] in scope
        )
    )
    complete = bool(
        scope and len(done) == len(scope) and synth_ok and not m.get("conflicts")
    )
    return dict(
        schema_version=VERSION,
        book_id=m["book_id"],
        status="complete" if complete else "blocked" if blocked else "partial",
        book_coverage=coverage,
        scope=scope,
        coverage={
            "read_pages": len(read & substantive),
            "substantive_pages": len(substantive),
            "pdf_pages": m["page_count"],
            "chapters_published": len(done),
        },
        output_paths=[m["index_path"]]
        + [v["path"] for k, v in m["published"].items() if k != "index"],
        unresolved=unresolved,
        resume_selector=m["book_id"],
    )


def require(condition, message):
    if not condition:
        raise ValueError(message)


def chapter(m, cid):
    found = [c for c in m["chapters"] if c["id"] == cid]
    require(len(found) == 1, "Unknown chapter")
    return found[0]


def read_pages(m, cid):
    return {
        p
        for x in m["chunks"].values()
        if x["chapter_id"] == cid and not x["unresolved"]
        for p in x["pages"]
    }


def record(m, r):
    require(r.get("schema_version") == VERSION, "Unsupported record version")
    require(r.get("source_hash") == m["source_hash"], "Stale source hash")
    kind = r["kind"]
    if "note" in r:
        require(
            "<!-- long-work-study:" not in r["note"],
            "Draft contains reserved publication markers",
        )
    if kind == "mapping":
        require(
            not m["chunks"] or r.get("chapters") == m["chapters"],
            "Remapping read chapters requires new source preparation",
        )
        chapters = r["chapters"]
        ids = []
        pages = []
        old = {c["id"]: c for c in m.get("previous_chapters", [])}
        for c in chapters:
            safe_name(c["id"])
            require(c["id"] != "index", "index is reserved for the book index")
            ids.append(c["id"])
            require(
                type(c["start"]) is int
                and type(c["end"]) is int
                and 1 <= c["start"] <= c["end"] <= m["page_count"],
                "Invalid chapter range",
            )
            require(
                type(c["confirmed"]) is bool, "Boundary confirmation must be boolean"
            )
            require(
                not c["confirmed"] or bool(c.get("boundary_evidence", "").strip()),
                "Boundary evidence required",
            )
            if c["id"] in old:
                require(
                    bool(c.get("match_evidence", "").strip()),
                    "Replacement chapter requires explicit identity match evidence",
                )
            pages.extend(range(c["start"], c["end"] + 1))
        require(len(ids) == len(set(ids)), "Duplicate chapter IDs")
        for e in r["exclusions"]:
            require(
                e.get("reason", "").strip() and e["pages"],
                "Exclusion needs pages and reason",
            )
            pages.extend(e["pages"])
        require(
            all(type(p) is int for p in pages)
            and sorted(pages) == list(range(1, m["page_count"] + 1)),
            "Mapping must account for each page exactly once",
        )
        if "labels" in r:
            require(
                len(r["labels"]) == m["page_count"] and bool(r.get("label_evidence")),
                "Page-label correction needs exhaustive labels and inspection evidence",
            )
            require(
                all(x is None or isinstance(x, str) for x in r["labels"]),
                "Invalid page label",
            )
            m["labels"] = r["labels"]
            m["label_evidence"] = r["label_evidence"]
        m.update(
            chapters=chapters,
            exclusions=r["exclusions"],
            mapped=True,
            scope=ids,
            synthesis={},
        )
    elif kind == "chunk":
        c = chapter(m, r["chapter_id"])
        require(c["confirmed"], "Chapter boundary unresolved")
        pages = r["pages"]
        require(
            1 <= len(pages) <= 8 and len(set(pages)) == len(pages),
            "Chunk requires 1–8 unique pages",
        )
        require(
            all(type(p) is int and c["start"] <= p <= c["end"] for p in pages),
            "Chunk page outside chapter",
        )
        covered = []
        for s in r["sections"]:
            require(
                s.get("title", "").strip() and s.get("evidence", "").strip(),
                "Section reading evidence required",
            )
            covered.extend(s["pages"])
        require(set(covered) == set(pages), "Every chunk page needs section evidence")
        require(isinstance(r["unresolved"], list), "Unresolved passages must be a list")
        # Replace a retry only at the exact same chunk boundary, never silently erase other evidence.
        key = r["chapter_id"] + ":" + ",".join(map(str, sorted(pages)))
        for k, x in m["chunks"].items():
            require(
                k == key or not (set(x["pages"]) & set(pages)),
                "Overlapping chunk; retry original page selection",
            )
        m["chunks"][key] = r
        m["results"].pop(c["id"], None)
        m["synthesis"] = {}
    elif kind == "chapter":
        c = chapter(m, r["chapter_id"])
        require(c["confirmed"], "Boundary unresolved")
        require(
            set(range(c["start"], c["end"] + 1)) <= read_pages(m, c["id"]),
            "Substantive reading missing or unresolved",
        )
        require(
            r.get("verified") is True and bool(r.get("verification", {})),
            "Explicit verification results required",
        )
        require(
            all(
                r["verification"].get(k) is True
                for k in ["sections", "mathematics", "citations", "figures"]
            ),
            "Chapter verification failed",
        )
        require(
            r.get("note", "").strip() and r.get("citations"),
            "Draft and supporting citations required",
        )
        require(
            all(type(p) is int and c["start"] <= p <= c["end"] for p in r["citations"]),
            "Citation outside chapter",
        )
        require(not r.get("unresolved", []), "Unresolved chapter passages")
        for f in r.get("figures", []):
            require(
                f.get("inspected") is True and f.get("page") in r["citations"],
                "Figure inspection and source citation required",
            )
        m["results"][c["id"]] = r
        m["synthesis"] = {}
    elif kind == "synthesis":
        require(
            r.get("chapters") == m["scope"]
            and all(c in m["results"] for c in m["scope"]),
            "Synthesis scope has incomplete chapters",
        )
        require(
            r.get("verified") is True and r.get("note", "").strip(),
            "Verified synthesis note required",
        )
        m["synthesis"] = r
    else:
        raise ValueError("Unknown record kind")


def select_scope(m, scope):
    require(scope and len(scope) == len(set(scope)), "Empty or duplicate scope")
    for cid in scope:
        chapter(m, cid)
    if m["scope"] != scope:
        m["scope"] = scope
        m["synthesis"] = {}


def next_chunk(m, root, ocr=False):
    from sources import extract

    require(m["mapped"], "Source mapping required")
    for cid in m["scope"]:
        c = chapter(m, cid)
        if not c["confirmed"]:
            return {**report(m), "blocked_chapter": cid}
        unresolved = [
            x
            for x in m["chunks"].values()
            if x["chapter_id"] == cid and x["unresolved"]
        ]
        if unresolved:
            pages = unresolved[0]["pages"]
        else:
            pages = [
                p
                for p in range(c["start"], c["end"] + 1)
                if p not in read_pages(m, cid)
            ][:8]
        if pages:
            return {
                **report(m),
                "chapter_id": cid,
                "chunk": extract(m, root, pages, ocr),
                "prerequisite_chapters": [
                    x["id"]
                    for x in m["chapters"]
                    if x["end"] < c["start"] and x["id"] in m["results"]
                ],
            }
        if cid not in m["results"]:
            return {
                **report(m),
                "chapter_id": cid,
                "action": "record verified chapter result",
            }
    return {**report(m), "action": "record scope synthesis and publish"}
