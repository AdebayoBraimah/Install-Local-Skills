import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/librarian.py"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(*keys):
    return dict(
        schemaVersion=1,
        complete=True,
        serverID="server-test",
        library={"type": "user", "id": 42},
        capturedAt="2026-09-10T00:00:00Z",
        libraryVersion=1,
        collections=[],
        citationKeys={k: "paper" + k for k in keys},
        items=[
            dict(
                key=k,
                parentItem=None,
                rootItem=k,
                source={},
                file=None,
                metadata=dict(
                    itemType="journalArticle",
                    title="Paper " + k,
                    abstractNote="A controlled abstract.",
                    collections=[],
                    tags=[],
                ),
            )
            for k in keys
        ],
    )


class Library:
    def __init__(self, tmp):
        self.vault = tmp / "vault"
        self.vault.mkdir()
        self.source = tmp / "snapshot.json"
        self.data = snapshot("AAAA0001")
        self.write()

    def write(self):
        self.source.write_text(json.dumps(self.data))

    def cli(self, *args, code=0, env=None):
        p = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--vault",
                str(self.vault),
                "--snapshot",
                str(self.source),
                *args,
            ],
            text=True,
            capture_output=True,
            env=dict(os.environ, **(env or {})),
        )
        assert p.returncode == code, (p.stdout, p.stderr)
        return json.loads(p.stdout)

    def scan(self, *args):
        self.write()
        return self.cli("scan", *args)

    def work(self, run):
        return self.cli("next", "--run", run, "--limit", "10")["assignments"]


@pytest.fixture
def lib(tmp_path):
    return Library(tmp_path)


def test_scan_dry_run_and_rescan_preserve_pending_work(lib):
    preview = lib.scan("--dry-run")
    assert preview["actionable"] == 1
    assert list(lib.vault.iterdir()) == []
    run = lib.scan()["run_id"]
    a = lib.work(run)[0]
    assert a["operation"] == "generate"
    assert a["source_quality"] == "abstract-only"
    assert a["item"]["key"] == "AAAA0001"
    run2 = lib.scan()["run_id"]
    assert lib.work(run2)[0]["operation"] == "generate"


def record(lib, run, assignment, text="## Summary\n\nControlled summary.", **changes):
    result = {
        k: copy.deepcopy(assignment[k])
        for k in [
            "schema_version",
            "assignment_id",
            "item",
            "operation",
            "revision",
            "source_fingerprints",
            "expected_destination_hashes",
        ]
    }
    result.update(outcome="success", sections={"content": text}, assets=[], keywords=[])
    result.update(changes)
    f = lib.source.parent / "result.json"
    f.write_text(json.dumps(result))
    return lib.cli("record", "--run", run, "--input", str(f))


def generate(lib):
    run = lib.scan()["run_id"]
    assignment = lib.work(run)[0]
    record(lib, run, assignment)
    lib.cli("publish", "--run", run)
    return lib.vault / assignment["path"], run


def test_publish_and_unchanged_second_scan(lib):
    note, run = generate(lib)
    before = note.read_bytes()
    assert b"Controlled summary." in before
    assert lib.cli("status", "--run", run)["status"] == "complete"
    second = lib.scan()
    assert lib.work(second["run_id"]) == []
    assert note.read_bytes() == before


def pdf(lib, key="PDF00001", parent="AAAA0001", data=b"%PDF-1.4\ncontrolled"):
    f = lib.source.parent / (key + ".pdf")
    f.write_bytes(data)
    lib.data["items"] = [x for x in lib.data["items"] if x["key"] != key]
    lib.data["items"].append(
        dict(
            key=key,
            parentItem=parent,
            rootItem=parent,
            source={},
            metadata={"itemType": "attachment", "contentType": "application/pdf"},
            file={"path": str(f), "status": "available", "sha256": sha(data)},
        )
    )
    lib.write()
    return f


@pytest.mark.parametrize("quality", ["metadata-only", "abstract-only"])
def test_legacy_upgrade_preserves_body_and_yaml(lib, quality):
    note = lib.vault / "Ideas/Research/nested/legacy.md"
    note.parent.mkdir(parents=True)
    original = f"---\n# my YAML comment\nZotero-Key:\n  - AAAA0001\nSource-Quality: {quality}\nDate Created: old-date # keep\ntags: [my-tag]\n---\n\nMy notes  \n\n"
    note.write_text(original)
    initial = lib.scan()
    assert initial["items"][0]["adoption"] == "adopted_unverified"
    assert initial["items"][0]["published"] is None
    assert lib.work(initial["run_id"]) == []
    pdf(lib)
    run = lib.scan()["run_id"]
    work = lib.work(run)[0]
    assert work["operation"] == "generate" and work["path"].endswith("nested/legacy.md")
    record(lib, run, work)
    lib.cli("publish", "--run", run)
    updated = note.read_text()
    assert "# my YAML comment" in updated and "Date Created: old-date # keep" in updated
    assert "tags: [my-tag]" in updated and "\n\nMy notes  \n\n" in updated
    before = note.read_bytes()
    assert lib.scan()["actionable"] == 0
    assert note.read_bytes() == before


def test_pdf_replacement_citation_annotation_and_removal(lib):
    pdf(lib)
    note, _ = generate(lib)
    original = note.read_bytes()
    lib.data["citationKeys"]["AAAA0001"] = "renamed2026"
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    assert (
        w["operation"] == "metadata"
        and w["path"] == note.relative_to(lib.vault).as_posix()
    )
    record(lib, r, w, sections={})
    lib.cli("publish", "--run", r)
    assert (
        "renamed2026" in note.read_text() and "Controlled summary." in note.read_text()
    )
    pdf(lib, data=b"%PDF-new content same timestamp metadata")
    r = lib.scan()["run_id"]
    assert lib.work(r)[0]["operation"] == "generate"
    record(lib, r, lib.work(r)[0])
    lib.cli("publish", "--run", r)
    lib.data["items"].append(
        dict(
            key="ANNO0001",
            parentItem="PDF00001",
            rootItem="AAAA0001",
            source={},
            file=None,
            metadata={"itemType": "annotation", "annotationText": "note"},
        )
    )
    out = lib.scan()
    assert out["actionable"] == 0
    assert "annotations_changed_report_only" in out["items"][0]["reports"]
    before = note.read_bytes()
    lib.data["items"] = []
    lib.data["citationKeys"] = {}
    out = lib.scan()
    assert out["items"][0]["blocked"] == "source_removed"
    assert note.read_bytes() == before


@pytest.mark.parametrize("edit", ["content", "marker", "unmanaged"])
def test_edit_conflict_preserves_proposal(lib, edit):
    note, _ = generate(lib)
    r = lib.scan("--refresh")["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w, "Replacement text")
    text = note.read_text()
    text = (
        text.replace("Controlled summary.", "Personal correction")
        if edit == "content"
        else (
            text.replace("librarian:content:end", "removed-marker")
            if edit == "marker"
            else text + "\nMy new idea\n"
        )
    )
    note.write_text(text)
    out = lib.cli("publish", "--run", r)
    assert out["status"] == "blocked" and note.read_text() == text
    proposals = list((lib.vault / ".obsidian-librarian/conflicts").glob("*.json"))
    assert len(proposals) == 1 and "Replacement text" in proposals[0].read_text()


def test_attachment_selection_is_retained_and_wrong_parent_rejected(lib):
    pdf(lib)
    pdf(lib, key="PDF00002", data=b"%PDF-other")
    out = lib.scan()
    assert out["items"][0]["blocked"] == "attachment_ambiguous"
    r = lib.scan("--attachment", "AAAA0001=PDF00002")["run_id"]
    assert lib.work(r)[0]["source"]["selected_attachment"] == "PDF00002"
    out = lib.scan()
    assert out["items"][0]["selected_attachment"] == "PDF00002"
    assert (
        "available PDF belonging"
        in lib.cli("scan", "--attachment", "AAAA0001=NOPE0000", code=2)["error"]
    )
    lib.data["items"] = [x for x in lib.data["items"] if x["key"] != "PDF00002"]
    out = lib.scan()
    assert out["items"][0]["blocked"] == "selected_attachment_missing"


def test_result_survives_rescan_and_stale_source_requeues(lib):
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w)
    r2 = lib.scan()["run_id"]
    out = lib.cli("publish", "--run", r2)
    assert out["status"] == "complete"
    r = lib.scan("--refresh")["run_id"]
    record(lib, r, lib.work(r)[0])
    lib.data["items"][0]["metadata"]["abstractNote"] = "Changed abstract"
    r2 = lib.scan()["run_id"]
    assert lib.work(r2)[0]["operation"] == "generate"


@pytest.mark.parametrize(
    "point,exit_code", [("before_replace", 91), ("after_replace", 92)]
)
def test_crash_recovery_is_idempotent(lib, point, exit_code):
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w)
    p = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--vault",
            str(lib.vault),
            "--snapshot",
            str(lib.source),
            "publish",
            "--run",
            r,
        ],
        env=dict(os.environ, LIBRARIAN_TEST_CRASH=point),
        capture_output=True,
    )
    assert p.returncode == exit_code
    out = lib.cli("publish", "--run", r)
    assert out["status"] == "complete"
    note = lib.vault / w["path"]
    before = note.read_bytes()
    assert before.count(b"Controlled summary.") == 1
    lib.cli("publish", "--run", r)
    assert note.read_bytes() == before


def test_failed_items_retry_twice_and_survive_scans(lib):
    r = lib.scan()["run_id"]
    for _ in range(3):
        w = lib.work(r)[0]
        record(lib, r, w, outcome="failed", transient=True, error="temporary busy")
    assert lib.work(r) == []
    r2 = lib.scan("--retry-failed")["run_id"]
    assert len(lib.work(r2)) == 1


def test_targeted_links_and_progress_preserve_narrative(lib):
    research = lib.vault / "Ideas/Research"
    research.mkdir(parents=True)
    neighbor = research / "neighbor.md"
    neighbor.write_text(
        '---\nZotero-Key: BBBB0002\nKeywords: ["[[Planning]]"]\n---\nHandwritten [[elsewhere]]\n'
    )
    hub = lib.vault / "Ideas/Planning.md"
    hub.write_text("---\nCategory: [Concept]\n---\nMy hub text.\n")
    unrelated = lib.vault / "Ideas/Unrelated.md"
    unrelated.write_text("Unrelated bytes\n")
    progress = research / "_batch-progress.md"
    progress.write_text(
        "# Progress\n\n## Narrative\nKeep this log.\n\n```dataview\nLIST\n```\n"
    )
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w, keywords=["[[Planning]]"])
    out = lib.cli("publish", "--run", r)
    assert out["status"] == "complete"
    assert "neighbor" in (lib.vault / w["path"]).read_text()
    assert (
        "paperAAAA0001" in hub.read_text() and "paperAAAA0001" in neighbor.read_text()
    )
    assert "Handwritten [[elsewhere]]" in neighbor.read_text()
    assert unrelated.read_text() == "Unrelated bytes\n"
    assert (
        "Keep this log." in progress.read_text()
        and "```dataview\nLIST\n```" in progress.read_text()
    )
    assert "Unfiled" in progress.read_text() and "AAAA0001" in progress.read_text()


def test_linking_failure_resumes_without_generation(lib):
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w, keywords=["Planning"])
    out = lib.cli("publish", "--run", r, env={"LIBRARIAN_TEST_LINK_FAIL": "1"})
    assert out["items"][0]["published"] and out["items"][0]["pending"] == ["link"]
    r2 = lib.scan()["run_id"]
    assert lib.work(r2)[0]["operation"] == "link"
    out = lib.cli("publish", "--run", r2)
    assert out["status"] == "complete"


def test_book_scope_and_existing_long_work_identity(lib):
    lib.data["items"][0]["metadata"]["itemType"] = "book"
    pdf(lib)
    assert lib.scan()["actionable"] == 0
    r = lib.scan("--item", "AAAA0001")["run_id"]
    w = lib.work(r)[0]
    assert w["operation"] == "book"
    assert w["book"]["library_id"] == "local:server-test:users/0"
    assert w["book"]["identity"] == "local:server-test:users/0:AAAA0001"
    assert w["book"]["index_path"] == w["path"]
    assert lib.scan()["actionable"] == 0


def test_three_distinct_works_required_for_new_hub(lib):
    rdir = lib.vault / "Ideas/Research"
    rdir.mkdir(parents=True)
    for i in range(3):
        (rdir / f"chapter{i}.md").write_text(
            f'---\nBook-ID: same-book\nKeywords: ["[[Control theory]]"]\n---\nChapter {i}\n'
        )
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w, keywords=["[[Control theory]]"])
    lib.cli("publish", "--run", r)
    assert not (lib.vault / "Ideas/Control theory.md").exists()
    (rdir / "other.md").write_text(
        '---\nZotero-Key: OTHER000\nKeywords: ["[[Control theory]]"]\n---\nOther work\n'
    )
    r = lib.scan("--refresh")["run_id"]
    record(lib, r, lib.work(r)[0], keywords=["[[Control theory]]"])
    lib.cli("publish", "--run", r)
    assert (lib.vault / "Ideas/Control theory.md").exists()


def test_explicit_resolution_releases_edited_section(lib):
    note, _ = generate(lib)
    note.write_text(
        note.read_text().replace("Controlled summary.", "My changed summary.")
    )
    r = lib.scan("--refresh")["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w, "Approved replacement")
    assert lib.cli("publish", "--run", r)["status"] == "blocked"
    row = lib.cli("status")["items"][0]
    resolution = dict(
        schema_version=1,
        kind="resolution",
        item=row["item"],
        revision=row["revision"],
        action="approve_replacement",
        approve_sections=["content"],
        expected_destination_hashes={row["path"]: sha(note.read_bytes())},
    )
    f = lib.source.parent / "resolve.json"
    f.write_text(json.dumps(resolution))
    lib.cli("record", "--run", r, "--input", str(f))
    w = lib.work(r)[0]
    record(lib, r, w, "Approved replacement")
    out = lib.cli("publish", "--run", r)
    assert out["status"] == "complete" and "Approved replacement" in note.read_text()


def test_legacy_duplicate_and_new_collision_block_early(lib):
    root = lib.vault / "Ideas/Research"
    root.mkdir(parents=True)
    for path in ["a.md", "b.md"]:
        (root / path).write_text("---\nZotero-Key: AAAA0001\n---\nMine\n")
    out = lib.scan()
    assert out["items"][0]["blocked"] == "duplicate_identity"
    assert lib.work(out["run_id"]) == []


def test_collection_descendants_unfiled_and_ambiguous_names(lib):
    lib.data = snapshot("AAAA0001", "BBBB0002", "CCCC0003")
    lib.data["collections"] = [
        dict(key="COLL0001", collectionName="Root", path="Root", parentCollection=None),
        dict(
            key="COLL0002",
            collectionName="Same",
            path="Root/Same",
            parentCollection="COLL0001",
        ),
        dict(key="COLL0003", collectionName="Same", path="Same", parentCollection=None),
    ]
    lib.data["items"][0]["metadata"]["collections"] = ["COLL0002"]
    lib.data["items"][1]["metadata"]["collections"] = ["COLL0003"]
    r = lib.scan("--collection", "Root")["run_id"]
    assert [x["item"]["key"] for x in lib.work(r)] == ["AAAA0001"]
    lib.data["collections"][2]["path"] = "Other/Same"
    # Both short names are ambiguous when neither is itself an exact path.
    lib.write()
    error = lib.cli("scan", "--collection", "Same", code=2)["error"]
    assert "Root/Same" in error and "Other/Same" in error
    r = lib.scan()["run_id"]
    assert len(lib.work(r)) == 3


def test_drift_lock_and_incomplete_snapshot_cannot_publish(lib):
    import fcntl

    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    record(lib, r, w)
    lock = lib.vault / ".obsidian-librarian/locks/writer.lock"
    with lock.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert "holds the lock" in lib.cli("publish", "--run", r, code=2)["error"]
        assert not (lib.vault / w["path"]).exists()
    lib.data["items"][0]["metadata"]["abstractNote"] = "Source drift"
    lib.write()
    assert lib.cli("publish", "--run", r)["status"] == "blocked"
    assert not (lib.vault / w["path"]).exists()
    before = (lib.vault / ".obsidian-librarian/state.json").read_bytes()
    lib.data["complete"] = False
    lib.write()
    lib.cli("scan", code=2)
    assert (lib.vault / ".obsidian-librarian/state.json").read_bytes() == before


def test_pdf_locator_change_and_abstract_edit_preserve_pdf_summary(lib):
    old = pdf(lib)
    note, _ = generate(lib)
    before = note.read_bytes()
    new = old.with_name("relocated.pdf")
    old.rename(new)
    lib.data["items"][1]["file"]["path"] = str(new)
    lib.data["items"][0]["metadata"][
        "abstractNote"
    ] = "Updated abstract, same paper PDF"
    out = lib.scan()
    assert out["actionable"] == 0 and note.read_bytes() == before
    assert out["items"][0]["source"]["pdf_path"] == str(new)


def test_book_partial_result_uses_real_long_work_verification(lib):
    import fitz

    lib.data["items"][0]["metadata"]["itemType"] = "book"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Chapter 1. Controlled book.")
    data = document.tobytes()
    document.close()
    f = pdf(lib, data=data)
    helper = Path.home() / ".codex/skills/long-work-summarizer-cdx/scripts/long_work.py"
    prepared = subprocess.run(
        [
            sys.executable,
            str(helper),
            "--vault",
            str(lib.vault),
            "prepare",
            str(f),
            "--citation-key",
            "paperAAAA0001",
        ],
        capture_output=True,
        text=True,
    )
    assert prepared.returncode == 0, (prepared.stdout, prepared.stderr)
    book = json.loads(prepared.stdout)["book_id"]
    workdir = lib.vault / ".long-work-summarizer/works" / book
    manifest = json.loads((workdir / "manifest.json").read_text())
    manifest["identity"] = "local:server-test:users/0:AAAA0001"
    (workdir / "manifest.json").write_text(json.dumps(manifest))
    r = lib.scan("--item", "AAAA0001")["run_id"]
    w = lib.work(r)[0]
    assert w["book"]["book_id"] == book
    out = record(
        lib,
        r,
        w,
        book_result_path=f".long-work-summarizer/works/{book}/run-result.json",
    )
    assert out["items"][0]["book_result"]["book_coverage"] == "unread"
    assert (
        out["items"][0]["pending"] == ["book"] and out["items"][0]["published"] is None
    )
    assert out["items"][0]["book_result"]["resume_selector"] == book


def test_routine_book_scan_never_dispatches_deferred_study(lib):
    lib.data["items"][0]["metadata"]["itemType"] = "book"
    pdf(lib)
    lib.scan("--item", "AAAA0001")
    r = lib.scan()["run_id"]
    assert lib.work(r) == []


def test_targeted_neighbor_retains_other_concept_hub(lib):
    lib.data = snapshot("AAAA0001", "BBBB0002")
    (lib.vault / "Ideas").mkdir()
    for name in ["Planning", "Control"]:
        (lib.vault / "Ideas" / f"{name}.md").write_text(
            f"---\nCategory: [Concept]\n---\n{name}\n"
        )
    r = lib.scan("--item", "BBBB0002")["run_id"]
    record(lib, r, lib.work(r)[0], keywords=["Planning", "Control"])
    lib.cli("publish", "--run", r)
    neighbor = lib.vault / "Ideas/Research/paperBBBB0002.md"
    assert "[[Ideas/Control]]" in neighbor.read_text()
    r = lib.scan("--item", "AAAA0001")["run_id"]
    record(lib, r, lib.work(r)[0], keywords=["Planning"])
    lib.cli("publish", "--run", r)
    assert "[[Ideas/Control]]" in neighbor.read_text()


def test_partial_book_published_index_resumes(lib):
    import fitz

    lib.data["items"][0]["metadata"]["itemType"] = "book"
    d = fitz.open()
    d.new_page().insert_text((72, 72), "Book.")
    data = d.tobytes()
    d.close()
    f = pdf(lib, data=data)
    helper = Path.home() / ".codex/skills/long-work-summarizer-cdx/scripts/long_work.py"

    def long(*args):
        p = subprocess.run(
            [sys.executable, str(helper), "--vault", str(lib.vault), *args],
            capture_output=True,
            text=True,
        )
        assert p.returncode == 0, (p.stdout, p.stderr)
        return json.loads(p.stdout)

    book = long("prepare", str(f), "--citation-key", "paperAAAA0001")["book_id"]
    mpath = lib.vault / ".long-work-summarizer/works" / book / "manifest.json"
    m = json.loads(mpath.read_text())
    m["identity"] = "local:server-test:users/0:AAAA0001"
    mpath.write_text(json.dumps(m))
    r = lib.scan("--item", "AAAA0001")["run_id"]
    w = lib.work(r)[0]
    long("publish", book)
    record(
        lib,
        r,
        w,
        book_result_path=f".long-work-summarizer/works/{book}/run-result.json",
    )
    r2 = lib.scan("--item", "AAAA0001")["run_id"]
    assert lib.work(r2)[0]["operation"] == "book"


def test_removed_source_reappearance_releases_block(lib):
    note, _ = generate(lib)
    saved = copy.deepcopy(lib.data)
    lib.data["items"] = []
    lib.data["citationKeys"] = {}
    lib.scan()
    lib.data = saved
    out = lib.scan()
    assert not out["items"][0]["blocked"]
    assert out["actionable"] == 0 and note.exists()


def test_projection_counts_entire_current_collection(lib):
    lib.data = snapshot("AAAA0001", "BBBB0002")
    lib.data["collections"] = [
        dict(
            key="COLL0001",
            collectionName="Completed",
            path="Completed",
            parentCollection=None,
        )
    ]
    for x in lib.data["items"]:
        x["metadata"]["collections"] = ["COLL0001"]
    r = lib.scan("--item", "AAAA0001")["run_id"]
    record(lib, r, lib.work(r)[0])
    lib.cli("publish", "--run", r)
    progress = (lib.vault / "Ideas/Research/_batch-progress.md").read_text()
    assert "| Completed | 2 | 1 | 1 |" in progress


def test_revision_assets_and_stale_worker_contract(lib):
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    stage = lib.vault / w["staging_dir"]
    stage.mkdir(parents=True)
    asset = stage / "figure.svg"
    asset.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    dest = "Files/Images/" + w["assignment_id"] + "-figure.svg"
    record(
        lib,
        r,
        w,
        "Figure: ![[" + dest + "]]",
        assets=[
            dict(
                staged_path=str(asset.relative_to(lib.vault)),
                path=dest,
                sha256=sha(asset.read_bytes()),
            )
        ],
    )
    lib.cli("publish", "--run", r)
    assert (lib.vault / dest).read_bytes() == asset.read_bytes()
    r2 = lib.scan("--refresh")["run_id"]
    w2 = lib.work(r2)[0]
    lib.data["items"][0]["metadata"]["title"] = "Changed title"
    lib.scan()
    result = {
        k: copy.deepcopy(w2[k])
        for k in [
            "schema_version",
            "assignment_id",
            "item",
            "operation",
            "revision",
            "source_fingerprints",
            "expected_destination_hashes",
        ]
    }
    result.update(
        outcome="success", sections={"content": "Stale"}, assets=[], keywords=[]
    )
    f = lib.source.parent / "stale.json"
    f.write_text(json.dumps(result))
    assert "Stale" in lib.cli("record", "--run", r2, "--input", str(f), code=2)["error"]
    assert (lib.vault / dest).exists()


def test_status_is_read_only(lib):
    generate(lib)
    before = {str(p): p.read_bytes() for p in lib.vault.rglob("*") if p.is_file()}
    lib.cli("status")
    after = {str(p): p.read_bytes() for p in lib.vault.rglob("*") if p.is_file()}
    assert before == after


def test_new_notes_have_standard_quality_and_preserve_manual_tags(lib):
    import yaml

    note, _ = generate(lib)
    data = yaml.safe_load(note.read_text().split("---")[1])
    assert data["Source-Quality"] == "abstract-only"
    assert "tags" in data and "Keywords" in data
    text = note.read_text().replace("tags: []", "tags: [personal] # my tag")
    note.write_text(text)
    pdf(lib)
    r = lib.scan()["run_id"]
    record(lib, r, lib.work(r)[0])
    out = lib.cli("publish", "--run", r)
    assert out["status"] == "complete"
    assert "tags: [personal] # my tag" in note.read_text()
    assert (
        yaml.safe_load(note.read_text().split("---")[1])["Source-Quality"] == "pdf-full"
    )


def test_legacy_metadata_update_does_not_claim_summary_freshness(lib):
    pdf(lib)
    note = lib.vault / "Ideas/Research/legacy.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\nZotero-Key: AAAA0001\nSource-Quality: pdf-full\n---\nUnverified legacy summary\n"
    )
    lib.scan()
    lib.data["citationKeys"]["AAAA0001"] = "newCitation"
    r = lib.scan()["run_id"]
    w = lib.work(r)[0]
    assert w["operation"] == "metadata"
    record(lib, r, w, sections={})
    out = lib.cli("publish", "--run", r)
    item = out["items"][0]
    assert item["adoption"] == "adopted_unverified"
    assert "pdf" not in item["published"] and "abstract" not in item["published"]
    progress = (lib.vault / "Ideas/Research/_batch-progress.md").read_text()
    assert "| adopted_unverified |" in progress
    assert "| Unfiled | 1 | 0 | 1 |" in progress
    assert lib.scan()["actionable"] == 0
