import json
import subprocess
import sys
from pathlib import Path
import fitz

CLI = Path(__file__).resolve().parents[1] / "scripts/long_work.py"
sys.path.insert(0, str(CLI.parent))


def call(vault, *args, ok=True):
    p = subprocess.run(
        [sys.executable, str(CLI), "--vault", str(vault), *map(str, args)],
        capture_output=True,
        text=True,
    )
    if ok:
        assert p.returncode == 0, p.stderr + p.stdout
    else:
        assert p.returncode != 0, p.stdout
    return json.loads(p.stdout)


def pdf(path, n=4):
    d = fitz.open()
    for i in range(n):
        p = d.new_page()
        p.insert_text(
            (72, 72), f"Chapter {i+1}. Definitions and worked examples on page {i+1}."
        )
    d.set_page_labels([{"startpage": 0, "prefix": "", "style": "r", "firstpagenum": 1}])
    d.save(path)
    d.close()


def test_prepare_resume_and_dry_run(tmp_path):
    source = tmp_path / "source.pdf"
    pdf(source)
    v = tmp_path / "vault"
    v.mkdir()
    call(v, "prepare", source, "--dry-run")
    assert not list(v.iterdir())
    a = call(v, "prepare", source)
    b = call(v, "prepare", source)
    assert a["book_id"] == b["book_id"]
    assert b["coverage"]["read_pages"] == 0
    assert b["book_coverage"] == "unread"


def record(v, b, data, ok=True):
    p = v / "input.json"
    p.write_text(json.dumps({"schema_version": 1, **data}))
    return call(v, "record", b, "--input", p, ok=ok)


def prepared(tmp_path):
    source = tmp_path / "source.pdf"
    pdf(source)
    v = tmp_path / "vault"
    v.mkdir()
    r = call(v, "prepare", source)
    b = r["book_id"]
    h = json.loads(
        (v / ".long-work-summarizer/works" / b / "manifest.json").read_text()
    )["source_hash"]
    return v, b, h


def mapping(h):
    return {
        "kind": "mapping",
        "source_hash": h,
        "chapters": [
            {
                "id": "ch-01",
                "title": "Foundations",
                "start": 1,
                "end": 2,
                "confirmed": True,
                "boundary_evidence": "TOC and heading inspected",
            },
            {
                "id": "ch-02",
                "title": "Methods",
                "start": 3,
                "end": 4,
                "confirmed": True,
                "boundary_evidence": "Visible heading inspected",
            },
        ],
        "exclusions": [],
    }


def test_reading_gaps_and_selected_scope(tmp_path):
    v, b, h = prepared(tmp_path)
    bad = mapping(h)
    bad["chapters"][0]["end"] = 1
    record(v, b, bad, ok=False)
    record(v, b, mapping(h))
    n = call(v, "next", b, "--chapters", "ch-02")
    assert [x["pdf_page"] for x in n["chunk"]] == [3, 4]
    assert n["chunk"][0]["printed_label"] == "iii"
    record(
        v,
        b,
        {
            "kind": "chapter",
            "source_hash": h,
            "chapter_id": "ch-02",
            "note": "Premature",
            "citations": [3, 4],
            "verified": True,
        },
        ok=False,
    )
    record(
        v,
        b,
        {
            "kind": "chunk",
            "source_hash": h,
            "chapter_id": "ch-02",
            "pages": [3],
            "sections": [
                {
                    "title": "Methods",
                    "pages": [3],
                    "evidence": "Read definition and checked example.",
                }
            ],
            "unresolved": [],
        },
    )
    assert [x["pdf_page"] for x in call(v, "next", b)["chunk"]] == [4]
    record(
        v,
        b,
        {
            "kind": "chunk",
            "source_hash": h,
            "chapter_id": "ch-02",
            "pages": [4],
            "sections": [
                {"title": "Examples", "pages": [4], "evidence": "Read worked example."}
            ],
            "unresolved": ["Equation illegible"],
        },
    )
    assert call(v, "status", b)["book_coverage"] == "partial"
    record(
        v,
        b,
        {
            "kind": "chapter",
            "source_hash": h,
            "chapter_id": "ch-02",
            "note": "Premature",
            "citations": [3, 4],
            "verified": True,
        },
        ok=False,
    )


def finish_chapter(v, b, h, cid, pages):
    record(
        v,
        b,
        {
            "kind": "chunk",
            "source_hash": h,
            "chapter_id": cid,
            "pages": pages,
            "sections": [
                {
                    "title": "Definitions and examples",
                    "pages": pages,
                    "evidence": "Read all definitions and examples and checked notation.",
                }
            ],
            "unresolved": [],
        },
    )
    record(
        v,
        b,
        {
            "kind": "chapter",
            "source_hash": h,
            "chapter_id": cid,
            "note": "## Definitions\n\nStudy explanation. Source: PDF pages "
            + ", ".join(map(str, pages))
            + ".\n",
            "citations": pages,
            "verified": True,
            "verification": dict.fromkeys(
                ["sections", "mathematics", "citations", "figures"], True
            ),
            "figures": [],
        },
    )


def test_publication_preserves_edits_and_scope(tmp_path):
    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    call(v, "next", b, "--chapters", "ch-02")
    finish_chapter(v, b, h, "ch-02", [3, 4])
    record(
        v,
        b,
        {
            "kind": "synthesis",
            "source_hash": h,
            "chapters": ["ch-02"],
            "verified": True,
            "note": "Methods depend on the definitions in the earlier chapter, which remains unread.",
        },
    )
    r = call(v, "publish", b)
    assert r["status"] == "complete" and r["book_coverage"] == "partial"
    paths = [v / x for x in r["output_paths"]]
    original = {str(p): p.read_bytes() for p in paths}
    call(v, "publish", b)
    assert all(p.read_bytes() == original[str(p)] for p in paths)
    target = next(p for p in paths if "-ch-02" in p.name)
    target.write_text(target.read_text().replace("Study explanation", "My correction"))
    conflict = call(v, "publish", b)
    assert conflict["status"] == "blocked"
    assert "My correction" in target.read_text()
    assert list((v / ".long-work-summarizer/works" / b / "conflicts").glob("*.md"))
    call(v, "verify", b, ok=False)


def test_source_replacement_and_mapping_reconciliation(tmp_path):
    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    call(v, "publish", b)
    source = tmp_path / "source.pdf"
    source.unlink()
    pdf(source, 5)
    call(v, "status", b, ok=False)
    r = call(v, "prepare", source)
    assert r["book_id"] == b and r["coverage"]["read_pages"] == 0
    m = json.loads(
        (v / ".long-work-summarizer/works" / b / "manifest.json").read_text()
    )
    changed = mapping(m["source_hash"])
    changed["chapters"][1]["end"] = 5
    record(v, b, changed, ok=False)
    for c in changed["chapters"]:
        c["match_evidence"] = (
            "Verified unchanged chapter title and content across editions"
        )
    record(v, b, changed)
    assert list((v / ".long-work-summarizer/works" / b / "history").glob("*.json"))
    assert "stale" in (v / m["index_path"]).read_text().lower()


def test_missing_markers_and_unmanaged_text(tmp_path):
    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    r = call(v, "publish", b)
    target = v / next(p for p in r["output_paths"] if "-ch-01" in p)
    target.write_text(target.read_text() + "\nMy personal notes survive.\n")
    call(v, "publish", b)
    assert target.read_text().endswith("My personal notes survive.\n")
    target.write_text(target.read_text().replace("<!-- long-work-study:start -->", ""))
    before = target.read_bytes()
    assert call(v, "publish", b)["status"] == "blocked"
    assert target.read_bytes() == before


def test_ocr_cache(tmp_path):
    src = tmp_path / "scan.pdf"
    d = fitz.open()
    p = d.new_page()
    p.insert_text(
        (72, 72), "Scanned mathematical definition and worked example.", fontsize=18
    )
    pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
    scan = fitz.open()
    scan.new_page().insert_image(p.rect, stream=pix.tobytes("png"))
    scan.save(src)
    v = tmp_path / "vault"
    v.mkdir()
    b = call(v, "prepare", src)["book_id"]
    m = json.loads(
        (v / ".long-work-summarizer/works" / b / "manifest.json").read_text()
    )
    record(
        v,
        b,
        {
            "kind": "mapping",
            "source_hash": m["source_hash"],
            "chapters": [
                {
                    "id": "ch-01",
                    "title": "Scan",
                    "start": 1,
                    "end": 1,
                    "confirmed": True,
                    "boundary_evidence": "Single-page fixture",
                }
            ],
            "exclusions": [],
        },
    )
    first = call(v, "next", b)
    assert first["chunk"][0]["ocr"]
    assert "definition" in first["chunk"][0]["text"]
    cache = list((v / ".long-work-summarizer/cache").rglob("*.json"))
    times = [p.stat().st_mtime_ns for p in cache]
    assert call(v, "next", b)["chunk"] == first["chunk"]
    assert times == [p.stat().st_mtime_ns for p in cache]
    assert call(v, "status", b)["coverage"]["read_pages"] == 0


def test_reserved_ids_and_name_collisions(tmp_path):
    v, b, h = prepared(tmp_path)
    bad = mapping(h)
    bad["chapters"][0]["id"] = "index"
    record(v, b, bad, ok=False)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    m = json.loads(
        (v / ".long-work-summarizer/works" / b / "manifest.json").read_text()
    )
    p = v / m["chapter_dir"] / (m["note_prefix"] + "-ch-01.md")
    p.parent.mkdir(parents=True)
    p.write_text("My existing note")
    r = call(v, "publish", b)
    assert r["status"] == "blocked"
    assert p.read_text() == "My existing note"


def test_book_complete_only_after_synthesis(tmp_path):
    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    finish_chapter(v, b, h, "ch-02", [3, 4])
    r = call(v, "publish", b)
    assert r["book_coverage"] == "partial"
    record(
        v,
        b,
        {
            "kind": "synthesis",
            "source_hash": h,
            "chapters": ["ch-01", "ch-02"],
            "verified": True,
            "note": "Foundations explain the methods.",
        },
    )
    assert call(v, "publish", b)["book_coverage"] == "full"
    assert call(v, "verify", b)["status"] == "complete"


def test_lock_excludes_second_writer(tmp_path):
    import fcntl

    v, b, h = prepared(tmp_path)
    with (v / ".long-work-summarizer/locks" / (b + ".lock")).open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r = call(v, "publish", b, ok=False)
        assert "Another writer" in r["error"]


def test_collection_routes_books_before_legacy_dedup(tmp_path, monkeypatch):
    sys.path.insert(0, str(CLI.parent))
    import sources

    monkeypatch.setattr(
        sources,
        "zotero",
        lambda *args: [
            {"key": "B", "itemType": "book", "processed": True},
            {"key": "P", "itemType": "journalArticle"},
            {"key": "B", "itemType": "book"},
        ],
    )
    assert sources.collection_items("Mixed") == [
        {"key": "B", "route": "long-work-summarizer-cdx", "itemType": "book"},
        {"key": "P", "route": "paper-pipeline", "itemType": "journalArticle"},
    ]


def test_reread_unresolved_invalidates_published_coverage(tmp_path):
    import yaml

    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    r = call(v, "publish", b)
    record(
        v,
        b,
        {
            "kind": "chunk",
            "source_hash": h,
            "chapter_id": "ch-01",
            "pages": [1, 2],
            "sections": [
                {
                    "title": "Recheck",
                    "pages": [1, 2],
                    "evidence": "Found unreadable equation on recheck.",
                }
            ],
            "unresolved": ["Equation unresolved"],
        },
    )
    path = v / next(p for p in r["output_paths"] if "-ch-01" in p)
    assert (
        yaml.safe_load(path.read_text().split("---")[1])["Reading-Coverage"] != "full"
    )
    assert call(v, "verify", b)["book_coverage"] != "full"


def test_repeated_replacement_retains_identity_guard(tmp_path):
    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    call(v, "publish", b)
    source = tmp_path / "source.pdf"
    for n in [5, 6]:
        source.unlink()
        pdf(source, n)
        call(v, "prepare", source)
    m = json.loads(
        (v / ".long-work-summarizer/works" / b / "manifest.json").read_text()
    )
    r = mapping(m["source_hash"])
    r["chapters"][1]["end"] = 6
    assert "match evidence" in record(v, b, r, ok=False)["error"]


def test_recover_after_note_write_before_checkpoint(tmp_path, monkeypatch):
    import publication, state

    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    root = v / ".long-work-summarizer"
    m = state.load(root, b)

    def crash(*args):
        raise OSError("Injected interruption after note replacement")

    monkeypatch.setattr(publication, "save", crash)
    import pytest

    with pytest.raises(OSError):
        publication.publish(v, root, m)
    assert (root / "works" / b / "pending.json").exists()
    call(v, "status", b)
    assert not (root / "works" / b / "pending.json").exists()
    assert call(v, "publish", b)["coverage"]["chapters_published"] == 1


def test_attachment_ambiguity_and_bbt_resolution(tmp_path, monkeypatch):
    import sources, pytest

    source = tmp_path / "book.pdf"
    pdf(source)
    meta = {"key": "ABCDEFGH", "itemType": "book", "citationKey": "author2026book"}
    attachments = [
        {"key": "PDF1", "contentType": "application/pdf", "full_path": str(source)},
        {"key": "PDF2", "contentType": "application/pdf", "full_path": str(source)},
    ]

    def fake(*args):
        return {
            "items": [meta],
            "info": meta,
            "attachments": attachments,
            "cite": {"citationKey": "author2026book"},
        }[args[0]]

    monkeypatch.setattr(sources, "zotero", fake)
    monkeypatch.setattr(
        sources.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, "@book{author2026book}", ""),
    )
    with pytest.raises(ValueError, match="ambiguous"):
        sources.resolve("author2026book", "fixture")
    path, metadata, identity = sources.resolve("author2026book", "fixture", "PDF2")
    assert path == source and identity == "fixture:ABCDEFGH"
    assert metadata["attachment_key"] == "PDF2"


def test_corrected_labels_do_not_use_stale_cache(tmp_path):
    v, b, h = prepared(tmp_path)
    r = mapping(h)
    record(v, b, r)
    call(v, "next", b)
    r["labels"] = ["19", "20", "21", "22"]
    r["label_evidence"] = "Inspected visible printed folios"
    record(v, b, r)
    assert call(v, "next", b)["chunk"][0]["printed_label"] == "19"


def test_generated_marker_in_draft_rejected(tmp_path):
    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    r = {
        "kind": "chapter",
        "source_hash": h,
        "chapter_id": "ch-01",
        "note": "A note <!-- long-work-study:end -->",
        "citations": [1, 2],
        "verified": True,
        "verification": dict.fromkeys(
            ["sections", "mathematics", "citations", "figures"], True
        ),
        "figures": [],
    }
    record(v, b, r, ok=False)


def test_adoption_keeps_exact_unmanaged_text(tmp_path):
    v, b, h = prepared(tmp_path)
    m = json.loads(
        (v / ".long-work-summarizer/works" / b / "manifest.json").read_text()
    )
    p = v / m["index_path"]
    p.parent.mkdir(parents=True)
    original = "---\nTitle: Legacy\n---\nMy content with trailing spaces.  \n\n\n"
    p.write_text(original)
    call(v, "publish", b)
    actual = p.read_text().replace("\nReading-Coverage: unread", "")
    assert actual.startswith(original)


def test_ambiguous_boundary_blocks_chapter(tmp_path):
    v, b, h = prepared(tmp_path)
    r = mapping(h)
    r["chapters"][0]["confirmed"] = False
    record(v, b, r)
    assert call(v, "next", b)["status"] == "blocked"
    record(
        v,
        b,
        {
            "kind": "chunk",
            "source_hash": h,
            "chapter_id": "ch-01",
            "pages": [1, 2],
            "sections": [
                {"title": "Unconfirmed", "pages": [1, 2], "evidence": "Some text"}
            ],
            "unresolved": [],
        },
        ok=False,
    )


def test_transient_cli_timeouts_retry_twice(monkeypatch):
    import sources

    attempts = []

    def fake(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            raise subprocess.TimeoutExpired(args, 60)
        return subprocess.CompletedProcess(args, 0, "[]", "")

    monkeypatch.setattr(sources.subprocess, "run", fake)
    monkeypatch.setattr(sources.time, "sleep", lambda _: None)
    assert sources.zotero("items") == [] and len(attempts) == 3


def test_citation_change_keeps_paths_and_reading(tmp_path, monkeypatch):
    import argparse, long_work, state

    source = tmp_path / "source.pdf"
    pdf(source)
    v = tmp_path / "vault"
    v.mkdir()
    root = v / ".long-work-summarizer"
    meta = {"key": "ABCDEFGH", "citationKey": "oldkey", "citation": "@book{oldkey}"}
    monkeypatch.setattr(
        long_work, "resolve", lambda *args: (source, dict(meta), "fixture:ABCDEFGH")
    )
    a = argparse.Namespace(
        vault=v,
        selector="ABCDEFGH",
        collection=None,
        library_id="fixture",
        attachment=None,
        book_id=None,
        citation_key=None,
        index_path=None,
        dry_run=False,
    )
    b = long_work.prepare(a, root)["book_id"]
    m = state.load(root, b)
    h = m["source_hash"]
    record(v, b, mapping(h))
    finish_chapter(v, b, h, "ch-01", [1, 2])
    call(v, "publish", b)
    before = state.load(root, b)
    meta.update(citationKey="newkey", citation="@book{newkey}")
    long_work.prepare(a, root)
    after = state.load(root, b)
    assert after["metadata"]["citationKey"] == "newkey"
    assert (
        after["index_path"] == before["index_path"] and after["note_prefix"] == "oldkey"
    )
    assert after["chunks"] == before["chunks"] and after["results"] == before["results"]


def test_eight_character_bbt_key_is_not_assumed_item_key(tmp_path, monkeypatch):
    import sources

    source = tmp_path / "book.pdf"
    pdf(source)
    meta = {"key": "ABCDEFGH", "itemType": "book", "citationKey": "shortkey"}

    def fake(*args):
        if args[0] == "info" and args[1] != "ABCDEFGH":
            raise ValueError("Item not found")
        return {
            "items": [meta],
            "info": meta,
            "attachments": [
                {
                    "key": "PDF1",
                    "contentType": "application/pdf",
                    "full_path": str(source),
                }
            ],
            "cite": {"citationKey": "shortkey"},
        }[args[0]]

    monkeypatch.setattr(sources, "zotero", fake)
    monkeypatch.setattr(
        sources.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, "@book{shortkey}", ""),
    )
    assert sources.resolve("shortkey", "fixture")[2] == "fixture:ABCDEFGH"


def test_blocked_result_has_resume_and_coverage_contract(tmp_path):
    v, b, h = prepared(tmp_path)
    result = record(
        v,
        b,
        {"kind": "mapping", "source_hash": "stale", "chapters": [], "exclusions": []},
        ok=False,
    )
    assert result["resume_selector"] == b
    assert result["unresolved"] and "output_paths" in result and "coverage" in result


def test_table_alias_publication_and_missing_link_validation(tmp_path):
    v, b, h = prepared(tmp_path)
    record(v, b, mapping(h))
    call(v, "next", b, "--chapters", "ch-01")
    finish_chapter(v, b, h, "ch-01", [1, 2])
    result = call(v, "publish", b)
    index = next(v / x for x in result["output_paths"] if "-ch-01" not in x)
    chapter_path = next(v / x for x in result["output_paths"] if "-ch-01" in x)
    assert "[[" + chapter_path.stem + "\\|Foundations]]" in index.read_text()
    call(v, "verify", b)
    for link in ["[[" + chapter_path.stem + "|plain]]",
                 "[[" + chapter_path.stem + "\\|table]]",
                 "[[" + chapter_path.stem + "#Definitions\\|heading]]",
                 "[[#Scope synthesis|local]]"]:
        record(v, b, {"kind": "synthesis", "source_hash": h,
                      "chapters": ["ch-01"], "verified": True, "note": link})
        call(v, "publish", b)
        call(v, "verify", b)
    record(v, b, {"kind": "synthesis", "source_hash": h,
                  "chapters": ["ch-01"], "verified": True,
                  "note": "[[nonexistent-target\\|missing]]"})
    call(v, "publish", b)
    failure = call(v, "verify", b, ok=False)
    assert "Unresolved link: nonexistent-target" in str(failure)
