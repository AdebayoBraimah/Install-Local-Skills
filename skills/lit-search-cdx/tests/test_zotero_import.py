import copy
import hashlib
import json
from pathlib import Path
import secrets
import pytest
from litsearch.state import State, Blocked
from litsearch.zotero_import import Importer
from test_acquisition import record, make_pdf


def object_key():
    return "".join(
        secrets.choice("23456789ABCDEFGHIJKLMNPQRSTUVWXYZ") for _ in range(8)
    )


class FakeZotero:
    server_id = "fixture-server"

    def __init__(self):
        self.objects = {
            "collections": {
                "ABCDEFGH": {
                    "key": "ABCDEFGH",
                    "version": 1,
                    "name": "Review",
                    "parentCollection": False,
                }
            },
            "items": {},
        }
        self.writes = []
        self.files = {}
        self.lose_create = False

    def all(self, kind):
        return copy.deepcopy(list(self.objects[kind].values()))

    def get(self, kind, key):
        return copy.deepcopy(self.objects[kind].get(key))

    def create(self, kind, data):
        assert "key" not in data and "version" not in data
        key = object_key()
        self.writes.append(("create", kind, copy.deepcopy(data)))
        self.objects[kind][key] = {**copy.deepcopy(data), "key": key, "version": 1}
        if self.lose_create:
            self.lose_create = False
            raise Blocked("timeout_uncertain")
        return self.get(kind, key)

    def rename_collection(self, key, version, name):
        row = self.objects["collections"][key]
        if row["version"] != version:
            raise Blocked("concurrent_change")
        self.writes.append(("rename_collection", key))
        row["name"] = name
        row["version"] += 1

    def collections(self, key, version, memberships):
        row = self.objects["items"][key]
        if row["version"] != version:
            raise Blocked("concurrent_change")
        self.writes.append(("collections", key))
        row["collections"] = memberships
        row["version"] += 1

    def file(self, key):
        return self.files.get(key)

    def upload(self, key, path):
        import shutil

        destination = path.parent.parent / (key + ".pdf")
        shutil.copyfile(path, destination)
        self.writes.append(("upload", key))
        self.files[key] = str(destination)


def test_metadata_import_reuses_on_new_run_and_reports_missing_pdf(tmp_path):
    api = FakeZotero()
    r = record()
    s = State(tmp_path)
    out = Importer(s, api).run("r", [r], [r["id"]], "Review", approved=True)
    assert out["status"] == "partial" and out["records"][0]["zotero_import"]["item_key"]
    again = Importer(State(tmp_path), api).run(
        "different", [r], [r["id"]], "Review", approved=True
    )
    assert len(api.objects["items"]) == 1 and len(api.writes) == 1
    assert again["remaining_work"][0]["reason"] == "pdf_missing"


def test_dry_run_and_unapproved_never_write(tmp_path):
    api = FakeZotero()
    r = record()
    i = Importer(State(tmp_path), api)
    out = i.run("r", [r], [r["id"]], "Review", dry_run=True)
    assert out["dry_run"] and not api.writes
    with pytest.raises(Blocked, match="selection_approval"):
        i.run("r", [r], [r["id"]], "Review")


def test_existing_metadata_preserved_and_membership_added(tmp_path):
    api = FakeZotero()
    r = record()
    r["doi"] = "10.1234/existing"
    original = {
        "key": "EXISTING",
        "version": 2,
        "itemType": "journalArticle",
        "title": "My corrected title",
        "DOI": r["doi"],
        "creators": [{"name": "My Author"}],
        "collections": ["OTHERKEY"],
        "tags": [{"tag": "personal"}],
        "extra": "My writing",
    }
    api.objects["items"]["EXISTING"] = copy.deepcopy(original)
    out = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    new = api.objects["items"]["EXISTING"]
    assert {k: v for k, v in new.items() if k not in ("version", "collections")} == {
        k: v for k, v in original.items() if k not in ("version", "collections")
    }
    assert new["collections"] == ["OTHERKEY", "ABCDEFGH"]


def test_lost_create_response_and_deleted_item_do_not_duplicate(tmp_path):
    api = FakeZotero()
    r = record()
    s = State(tmp_path)
    api.lose_create = True
    first = Importer(s, api).run("r", [r], [r["id"]], "Review", approved=True)
    assert first["status"] == "partial" and len(api.objects["items"]) == 1
    second = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert len(api.writes) == 1 and second["records"][0]["zotero_import"]["item_key"]
    api.objects["items"].clear()
    third = Importer(s, api).run("r", [r], [r["id"]], "Review", approved=True)
    assert third["remaining_work"][0]["reason"] == "journaled_item_deleted"
    assert len(api.writes) == 1


def test_pdf_is_copied_and_repeat_does_not_add_attachment(tmp_path):
    api = FakeZotero()
    r = record()
    pdf = tmp_path / "source.pdf"
    make_pdf(pdf, r["title"])
    r["download"] = {"path": str(pdf)}
    s = State(tmp_path / "state")
    first = Importer(s, api).run("r", [r], [r["id"]], "Review", approved=True)
    assert first["status"] == "complete"
    key = first["records"][0]["zotero_import"]["attachment"]["key"]
    assert api.files[key] != str(pdf)
    again = Importer(State(tmp_path / "state"), api).run(
        "new-run", [r], [r["id"]], "Review", approved=True
    )
    assert again["status"] == "complete" and len(api.objects["items"]) == 2
    assert len([w for w in api.writes if w[0] == "upload"]) == 1


def test_ambiguous_or_conflicting_identity_does_not_create(tmp_path):
    api = FakeZotero()
    r = record()
    r["doi"] = "10.1234/new"
    api.objects["items"]["EXISTING"] = {
        "key": "EXISTING",
        "version": 1,
        "itemType": "journalArticle",
        "title": r["title"],
        "DOI": "10.1234/old",
        "creators": [{"name": r["authors"][0]}],
    }
    out = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert (
        out["remaining_work"][0]["reason"] == "ambiguous_or_conflicting_identity"
        and not api.writes
    )


def test_existing_uncertain_pdf_is_not_replaced(tmp_path):
    api = FakeZotero()
    r = record()
    p = tmp_path / "bad.pdf"
    make_pdf(p, "Some unrelated paper")
    api.objects["items"]["EXISTING"] = {
        "key": "EXISTING",
        "version": 1,
        "itemType": "journalArticle",
        "title": r["title"],
        "creators": [{"name": r["authors"][0]}],
        "collections": ["ABCDEFGH"],
    }
    api.objects["items"]["ATTACHED"] = {
        "key": "ATTACHED",
        "version": 1,
        "itemType": "attachment",
        "parentItem": "EXISTING",
        "contentType": "application/pdf",
    }
    api.files["ATTACHED"] = str(p)
    out = Importer(State(tmp_path / "state"), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert (
        out["remaining_work"][0]["reason"] == "existing_pdf_requires_review"
        and not api.writes
    )


def test_duplicate_selection_alias_uses_one_parent(tmp_path):
    api = FakeZotero()
    r = record()
    other = {**r, "id": "alias"}
    out = Importer(State(tmp_path), api).run(
        "r", [r, other], [r["id"], "alias"], "Review", approved=True
    )
    assert len(api.objects["items"]) == 1
    assert (
        out["records"][0]["zotero_import"]["item_key"]
        == out["records"][1]["zotero_import"]["item_key"]
    )


def test_collection_creation_is_explicit_and_resumable(tmp_path):
    api = FakeZotero()
    r = record()
    i = Importer(State(tmp_path), api)
    with pytest.raises(Blocked, match="explicit_collection"):
        i.run("r", [r], [r["id"]], "New", approved=True)
    i.run("r", [r], [r["id"]], "New", approved=True, create_collection=True)
    i.run("r2", [r], [r["id"]], "New", approved=True, create_collection=True)
    assert len(api.objects["collections"]) == 2


def test_zotero_omits_empty_metadata_fields(tmp_path):
    class OmitsEmpty(FakeZotero):
        def create(self, kind, data):
            created = super().create(kind, data)
            self.objects[kind][created["key"]] = {
                k: v for k, v in self.objects[kind][created["key"]].items() if v != ""
            }
            return created

    api = OmitsEmpty()
    r = record()
    out = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert out["records"][0]["zotero_import"].get("item_key")


def test_strong_identifier_conflict_blocks_despite_different_titles(tmp_path):
    api = FakeZotero()
    r = record()
    r.update(doi="10.1234/shared", arxiv="2401.00001")
    api.objects["items"]["EXISTING"] = {
        "key": "EXISTING",
        "version": 1,
        "itemType": "journalArticle",
        "title": "Zebras and planetary geology",
        "DOI": r["doi"],
        "url": "https://arxiv.org/abs/2402.00002",
        "collections": [],
    }
    out = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert out["remaining_work"][0]["reason"] == "ambiguous_or_conflicting_identity"
    assert not api.writes and len(api.objects["items"]) == 1


def test_trashed_journaled_parent_is_not_reused(tmp_path):
    api = FakeZotero()
    r = record()
    state = State(tmp_path)
    first = Importer(state, api).run("r", [r], [r["id"]], "Review", approved=True)
    key = first["records"][0]["zotero_import"]["item_key"]
    api.objects["items"][key]["deleted"] = 1
    count = len(api.writes)
    again = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert again["remaining_work"][0]["reason"] == "journaled_item_deleted"
    assert len(api.writes) == count


def test_explicit_key_collision_is_never_adopted_on_resume(tmp_path):
    class Collision(FakeZotero):
        def create(self, kind, data):
            # A definitive rejection must not be reconciled as our success.
            self.objects[kind]["EXISTING"] = {
                **copy.deepcopy(data),
                "key": "EXISTING",
                "version": 1,
                "collections": [],
            }
            raise Blocked("zotero_create_rejected")

    api = Collision()
    r = record()
    Importer(State(tmp_path), api).run("r", [r], [r["id"]], "Review", approved=True)
    again = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert again["remaining_work"][0]["reason"] == "journal_create_rejected"
    assert not api.writes


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("items", {"itemType": "journalArticle", "title": "Reference"}),
        (
            "items",
            {"itemType": "attachment", "parentItem": "ABCDEFGH", "title": "Full Text"},
        ),
        ("collections", {"name": "New", "parentCollection": False}),
    ],
)
def test_acknowledged_create_cannot_recreate_after_failed_verification_and_deletion(
    tmp_path, kind, payload
):
    class VerificationFailure(FakeZotero):
        fail_get = False

        def create(self, kind, data):
            created = super().create(kind, data)
            self.fail_get = True
            return created

        def get(self, kind, key):
            if self.fail_get:
                self.fail_get = False
                raise Blocked("zotero_timeout_or_unavailable")
            return super().get(kind, key)

    api = VerificationFailure()
    importer = Importer(State(tmp_path), api)
    with pytest.raises(Blocked, match="timeout"):
        importer.ensure(kind, "owned", payload)
    key = importer.entry("owned")["key"]
    del api.objects[kind][key]
    with pytest.raises(Blocked, match="journaled_item_deleted"):
        Importer(State(tmp_path), api).ensure(kind, "owned", payload)
    assert len(api.writes) == 1


def test_trashed_owned_attachment_blocks_recovery(tmp_path):
    api = FakeZotero()
    importer = Importer(State(tmp_path), api)
    payload = {"itemType": "attachment", "parentItem": "ABCDEFGH", "title": "Full Text"}
    row = importer.ensure("items", "attachment", payload)
    api.objects["items"][row["key"]]["deleted"] = 1
    with pytest.raises(Blocked, match="journaled_item_deleted"):
        Importer(State(tmp_path), api).ensure("items", "attachment", payload)
    assert len(api.writes) == 1


def test_authorization_denial_can_resume_without_adopting_collisions(tmp_path):
    class Denied(FakeZotero):
        deny = True

        def create(self, kind, data):
            if self.deny:
                raise Blocked("zotero_authorization_required")
            return super().create(kind, data)

    api = Denied()
    r = record()
    first = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert first["remaining_work"][0]["reason"] == "zotero_authorization_required"
    api.deny = False
    again = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert again["records"][0]["zotero_import"]["item_key"]
    assert len(api.writes) == 1


def test_rejected_collection_create_is_not_adopted_by_name(tmp_path):
    class Collision(FakeZotero):
        def create(self, kind, data):
            self.objects[kind]["EXISTING"] = {
                **copy.deepcopy(data),
                "key": "EXISTING",
                "version": 1,
            }
            raise Blocked("zotero_create_rejected")

    api = Collision()
    importer = Importer(State(tmp_path), api)
    with pytest.raises(Blocked, match="zotero_create_rejected"):
        importer.collection("New", True, False)
    with pytest.raises(Blocked, match="journal_create_rejected"):
        Importer(State(tmp_path), api).collection("New", True, False)
    assert not api.writes


def test_uncertain_unkeyed_create_without_marker_never_reposts(tmp_path):
    class Uncertain(FakeZotero):
        attempts = 0

        def create(self, kind, data):
            self.attempts += 1
            raise Blocked("zotero_timeout_or_unavailable")

    api = Uncertain()
    r = record()
    Importer(State(tmp_path), api).run("r", [r], [r["id"]], "Review", approved=True)
    again = Importer(State(tmp_path), api).run(
        "r", [r], [r["id"]], "Review", approved=True
    )
    assert again["remaining_work"][0]["reason"] == "uncertain_create_requires_review"
    assert api.attempts == 1


def test_lost_collection_create_response_recovers_marker_then_renames(tmp_path):
    api = FakeZotero()
    api.lose_create = True
    with pytest.raises(Blocked, match="timeout"):
        Importer(State(tmp_path), api).collection("New", True, False)
    key = Importer(State(tmp_path), api).collection("New", True, False)
    assert api.objects["collections"][key]["name"] == "New"
    assert len([w for w in api.writes if w[0] == "create"]) == 1


def test_lost_collection_rename_response_does_not_duplicate(tmp_path):
    class LostRename(FakeZotero):
        def rename_collection(self, key, version, name):
            super().rename_collection(key, version, name)
            raise Blocked("zotero_timeout_or_unavailable")

    api = LostRename()
    with pytest.raises(Blocked, match="timeout"):
        Importer(State(tmp_path), api).collection("New", True, False)
    key = Importer(State(tmp_path), api).collection("New", True, False)
    assert api.objects["collections"][key]["name"] == "New"
    assert len(api.writes) == 2


def test_attachment_note_wrappers_normalize_without_weakening_marker(tmp_path):
    class Wrapped(FakeZotero):
        def create(self, kind, data):
            created = super().create(kind, data)
            self.objects[kind][created["key"]]["note"] = (
                '<div data-schema-version="9">' + data["note"] + "</div>"
            )
            return created

    api = Wrapped()
    importer = Importer(State(tmp_path), api)
    payload = {"itemType": "attachment", "parentItem": "ABCDEFGH", "title": "Full Text"}
    row = importer.ensure("items", "attachment", payload)
    api.objects["items"][row["key"]]["note"] += "Changed text"
    with pytest.raises(Blocked, match="journal_key_collision_or_changed_item"):
        importer.ensure("items", "attachment", payload)


def test_ambiguous_creation_marker_blocks_adoption(tmp_path):
    api = FakeZotero()
    api.lose_create = True
    importer = Importer(State(tmp_path), api)
    with pytest.raises(Blocked):
        importer.ensure(
            "items", "parent", {"itemType": "journalArticle", "title": "Reference"}
        )
    row = next(iter(api.objects["items"].values()))
    api.objects["items"]["DUPLICAT"] = {**copy.deepcopy(row), "key": "DUPLICAT"}
    with pytest.raises(Blocked, match="ambiguous_creation_marker"):
        importer.ensure(
            "items", "parent", {"itemType": "journalArticle", "title": "Reference"}
        )
    assert len(api.writes) == 1


@pytest.mark.parametrize("change", ["bytes", "metadata", "deleted", "missing_hash"])
def test_owned_attachment_integrity_checked_before_existing_pdf_shortcut(
    tmp_path, change
):
    api = FakeZotero()
    r = record()
    pdf = tmp_path / "source.pdf"
    make_pdf(pdf, r["title"])
    r["download"] = {"path": str(pdf)}
    state = State(tmp_path / "state")
    importer = Importer(state, api)
    first = importer.run("r", [r], [r["id"]], "Review", approved=True)
    assert first["status"] == "complete"
    result = first["records"][0]["zotero_import"]
    key = result["attachment"]["key"]
    stored = Path(api.files[key])
    # Even another valid PDF appearing first must not hide owned-object damage.
    api.objects["items"] = {
        "OTHERPDF": {
            "key": "OTHERPDF",
            "version": 1,
            "itemType": "attachment",
            "parentItem": result["item_key"],
            "contentType": "application/pdf",
        },
        **api.objects["items"],
    }
    api.files["OTHERPDF"] = str(pdf)
    if change == "bytes":
        stored.write_bytes(stored.read_bytes() + b"\n% valid PDF comment\n")
    elif change == "metadata":
        api.objects["items"][key]["title"] = "User changed title"
    elif change == "deleted":
        api.objects["items"][key]["deleted"] = 1
    else:
        with state.db() as db:
            rows = db.execute(
                "SELECT identity,data FROM zotero_imports WHERE identity LIKE 'attachment:%'"
            ).fetchall()
        for ident, raw in rows:
            saved = json.loads(raw)
            saved.pop("expected_sha256", None)
            importer.save(ident, saved)
    count = len(api.writes)
    before = stored.read_bytes()
    again = Importer(State(state.root), api).run(
        "again", [r], [r["id"]], "Review", approved=True
    )
    assert again["status"] == "partial" and not again["completed"]
    assert len(api.writes) == count and stored.read_bytes() == before


def test_owned_attachment_hash_saved_before_create_and_dry_run_never_changes_journal(
    tmp_path,
):
    state = State(tmp_path / "state")

    class InspectJournal(FakeZotero):
        def create(self, kind, data):
            if data.get("itemType") == "attachment":
                with state.db() as db:
                    raw = db.execute(
                        "SELECT data FROM zotero_imports WHERE identity LIKE 'attachment:%'"
                    ).fetchone()[0]
                saved = json.loads(raw)
                assert saved.get("expected_sha256") == expected
            return super().create(kind, data)

    api = InspectJournal()
    r = record()
    pdf = tmp_path / "source.pdf"
    make_pdf(pdf, r["title"])
    expected = hashlib.sha256(pdf.read_bytes()).hexdigest()
    r["download"] = {"path": str(pdf)}
    first = Importer(state, api).run("r", [r], [r["id"]], "Review", approved=True)
    assert first["status"] == "complete"
    with state.db() as db:
        before = db.execute("SELECT * FROM zotero_imports ORDER BY identity").fetchall()
    count = len(api.writes)
    dry = Importer(State(state.root), api).run(
        "r", [r], [r["id"]], "Review", dry_run=True
    )
    with state.db() as db:
        after = db.execute("SELECT * FROM zotero_imports ORDER BY identity").fetchall()
    assert dry["status"] == "complete" and before == after and len(api.writes) == count
