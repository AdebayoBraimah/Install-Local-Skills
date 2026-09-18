"""Approved personal-library imports with durable creation markers and reconciliation."""

import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import tempfile
from difflib import SequenceMatcher
from html.parser import HTMLParser
from .state import Blocked, digest
from .records import title_key, doi, arxiv, bibtex
from .acquisition import select, verify_pdf


def identity(r):
    return digest(
        ["doi", doi(r["doi"])]
        if r.get("doi")
        else (
            ["arxiv", r["arxiv"]]
            if r.get("arxiv")
            else [
                "title",
                title_key(r["title"]),
                sorted(title_key(a) for a in r.get("authors", [])),
            ]
        )
    )


def compatible(row, payload):
    class NoteText(HTMLParser):
        def __init__(self, value):
            super().__init__()
            self.parts = []
            self.feed(value)

        def handle_data(self, data):
            self.parts.append(data)

        def text(self):
            return " ".join("".join(self.parts).split())

    def equal(k, v):
        actual = row.get(k, "" if v == "" else None)
        if k == "note" and isinstance(actual, str) and isinstance(v, str):
            return NoteText(actual).text() == NoteText(v).text()
        return actual == v

    return all(
        equal(k, v)
        for k, v in payload.items()
        if k not in ("key", "version", "collections")
    )


def match(r, rows):
    exact = []
    uncertain = []
    for row in rows:
        if row.get("itemType") in ("attachment", "note", "annotation") or row.get(
            "deleted"
        ):
            continue
        rd = doi(row.get("DOI"))
        ra = arxiv(row.get("url", "")) or arxiv(row.get("extra", ""))
        strong = bool(r.get("doi") and rd == doi(r["doi"])) or bool(
            r.get("arxiv") and ra == r["arxiv"]
        )
        conflict = bool(
            (r.get("doi") and rd and rd != doi(r["doi"]))
            or (r.get("arxiv") and ra and ra != r["arxiv"])
        )
        if strong and conflict:
            raise Blocked("ambiguous_or_conflicting_identity")
        a, b = title_key(r["title"]), title_key(row.get("title", ""))
        names = {
            title_key((x.get("name") or x.get("lastName") or "").split()[-1])
            for x in row.get("creators", [])
            if x.get("name") or x.get("lastName")
        }
        authors = {title_key(x.split()[-1]) for x in r.get("authors", []) if x.split()}
        if strong and not conflict:
            exact.append(row)
        elif a and b and (a == b or SequenceMatcher(None, a, b).ratio() >= 0.8):
            if a == b and names & authors and not conflict:
                exact.append(row)
            else:
                uncertain.append(row)
    if len(exact) > 1 or (not exact and uncertain):
        raise Blocked("ambiguous_or_conflicting_identity")
    return exact[0] if exact else None


class Importer:
    def __init__(self, state, api):
        self.state, self.api = state, api

    def entry(self, key):
        with self.state.db() as db:
            try:
                row = db.execute(
                    "SELECT data FROM zotero_imports WHERE server=? AND identity=?",
                    (self.api.server_id, key),
                ).fetchone()
            except sqlite3.OperationalError:
                return None
            return json.loads(row[0]) if row else None

    def save(self, key, data):
        with self.state.db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS zotero_imports(server TEXT,identity TEXT,data TEXT,PRIMARY KEY(server,identity))"
            )
            db.execute(
                "INSERT OR REPLACE INTO zotero_imports VALUES(?,?,?)",
                (self.api.server_id, key, json.dumps(data)),
            )

    def ensure(self, kind, ident, payload, dry=False, expected_sha256=None):
        saved = self.entry(ident)
        if not saved:
            if dry:
                return {**payload, "key": "<new-item>", "version": 0}
            marker = "lit-search-cdx:" + secrets.token_hex(16)
            marked = dict(payload)
            if kind == "collections":
                marked["name"] = payload["name"] + " [" + marker + "]"
            elif payload.get("itemType") == "attachment":
                marked["note"] = "<p>" + marker + "</p>"
            else:
                marked["extra"] = (payload.get("extra", "") + "\n" + marker).strip()
            saved = {
                "key": None,
                "payload": marked,
                "desired_payload": payload,
                "marker": marker,
                "attempted": False,
                "verified": False,
                "create_outcome": "prepared",
            }
            if expected_sha256:
                saved["expected_sha256"] = expected_sha256
            self.save(ident, saved)
        if expected_sha256 and saved.get("expected_sha256") != expected_sha256:
            raise Blocked("attachment_journal_hash_missing_or_conflicting")
        outcome = saved.get("create_outcome")
        if outcome == "rejected":
            raise Blocked("journal_create_rejected")
        key = saved.get("key")
        if key:
            existing = self.api.get(kind, key)
            if not existing:
                if saved.get("verified") or outcome == "acknowledged":
                    raise Blocked("journaled_item_deleted")
                # Legacy keyed journals are reconciled, never replayed as POSTs.
                raise Blocked("uncertain_create_requires_review")
        else:
            marker = saved["marker"]
            matches = [
                row
                for row in self.api.all(kind)
                if any(
                    marker in str(row.get(field, ""))
                    for field in ("extra", "note", "name")
                )
            ]
            if len(matches) > 1:
                raise Blocked("ambiguous_creation_marker")
            if matches:
                if not saved.get("attempted"):
                    raise Blocked("journal_key_collision_or_changed_item")
                existing = matches[0]
                if not compatible(existing, saved["payload"]):
                    raise Blocked("journal_key_collision_or_changed_item")
                saved["key"] = existing["key"]
                saved["create_outcome"] = "acknowledged"
                if not dry:
                    self.save(ident, saved)
            elif outcome not in ("prepared", "not_created"):
                raise Blocked("uncertain_create_requires_review")
            elif dry:
                return {**saved["desired_payload"], "key": "<new-item>", "version": 0}
            else:
                saved["attempted"] = True
                saved["create_outcome"] = "uncertain"
                self.save(ident, saved)
                try:
                    created = self.api.create(kind, saved["payload"])
                except Blocked as e:
                    if e.code in (
                        "zotero_create_rejected",
                        "zotero_concurrent_change",
                        "zotero_create_key_mismatch",
                    ):
                        saved["create_outcome"] = "rejected"
                        self.save(ident, saved)
                    elif e.code == "zotero_authorization_required":
                        saved["create_outcome"] = "not_created"
                        saved["attempted"] = False
                        self.save(ident, saved)
                    raise
                if not isinstance(created, dict) or not created.get("key"):
                    raise Blocked("uncertain_create_requires_review")
                saved["key"] = created["key"]
                saved["create_outcome"] = "acknowledged"
                self.save(ident, saved)
                existing = self.api.get(kind, saved["key"])
                if not existing:
                    raise Blocked("create_not_verified")
        if existing.get("deleted"):
            raise Blocked("journaled_item_deleted")
        compatible_payload = compatible(existing, saved["payload"])
        if kind == "collections" and saved.get("desired_payload"):
            compatible_payload = compatible_payload or compatible(
                existing, saved["desired_payload"]
            )
        if not saved.get("attempted") or not compatible_payload:
            raise Blocked("journal_key_collision_or_changed_item")
        saved["verified"] = True
        if not dry:
            self.save(ident, saved)
        return existing

    def collection(self, name, create, dry):
        rows = self.api.all("collections")
        bykey = {r["key"]: r for r in rows}

        def path(row, seen=None):
            seen = set() if seen is None else seen
            if row["key"] in seen:
                raise Blocked("invalid_collection_hierarchy")
            seen.add(row["key"])
            parent = row.get("parentCollection")
            if parent and parent not in bykey:
                raise Blocked("invalid_collection_hierarchy")
            return (path(bykey[parent], seen) + "/" if parent else "") + row["name"]

        matches = [r for r in rows if r["key"] == name or path(r) == name]
        if len(matches) > 1:
            raise Blocked("ambiguous_collection")
        ident = "collection:" + digest(name)
        saved = self.entry(ident)
        if saved:
            owned = self.ensure(
                "collections",
                ident,
                saved.get("desired_payload", saved["payload"]),
                dry=dry,
            )
            if matches and matches[0]["key"] != owned["key"]:
                raise Blocked("journal_identity_conflict")
            if owned["name"] != name and not dry:
                self.api.rename_collection(owned["key"], owned["version"], name)
                owned = self.api.get("collections", owned["key"])
                if (
                    not owned
                    or owned.get("name") != name
                    or owned.get("parentCollection")
                ):
                    raise Blocked("collection_rename_not_verified")
            return owned["key"]
        if matches:
            return matches[0]["key"]
        if not create or "/" in name or not name.strip():
            raise Blocked("explicit_collection_required")
        if dry:
            return "<new-collection>"
        self.ensure("collections", ident, {"name": name, "parentCollection": False})
        # Re-enter only after the generated key is durable and verified.
        return self.collection(name, create, dry)

    def parent(self, r, collection, dry):
        ident = "parent:" + identity(r)
        saved = self.entry(ident)
        rows = self.api.all("items")
        existing = match(r, rows)
        if saved:
            owned = self.ensure("items", ident, saved["payload"], dry=dry)
            if existing and existing["key"] != owned["key"]:
                raise Blocked("journal_identity_conflict")
            existing = owned
        if existing:
            key = existing["key"]
            action = "reused"
        else:
            if not bibtex(r):
                raise Blocked("insufficient_verified_metadata")
            if dry:
                return {
                    "key": "<new-item>",
                    "version": 0,
                    "collections": [collection],
                }, "would_create"
            payload = {
                "itemType": "journalArticle",
                "title": r["title"],
                "creators": [
                    {"creatorType": "author", "name": a} for a in r["authors"]
                ],
                "date": str(r["year"]),
                "DOI": r.get("doi") or "",
                "url": r.get("url")
                or ("https://arxiv.org/abs/" + r["arxiv"] if r.get("arxiv") else ""),
                "publicationTitle": r.get("venue") or "",
                "abstractNote": r.get("abstract") or "",
                "extra": "lit-search-cdx provenance: "
                + json.dumps(r.get("provenance", []), ensure_ascii=False),
                "collections": [collection],
            }
            existing = self.ensure("items", ident, payload)
            key = existing["key"]
            action = "created"
        memberships = existing.get("collections", [])
        if collection not in memberships and not dry:
            self.api.collections(key, existing["version"], memberships + [collection])
            updated = self.api.get("items", key)
            if not updated or not set(memberships + [collection]) <= set(
                updated.get("collections", [])
            ):
                raise Blocked("collection_membership_not_verified")
            existing = updated
        if not dry and not self.entry(ident):
            self.save(
                ident,
                {
                    "key": key,
                    "verified": True,
                    "attempted": True,
                    "payload": {
                        k: existing[k]
                        for k in ("itemType", "title", "DOI", "creators")
                        if k in existing
                    },
                },
            )
        return existing, action

    def verify_owned_attachments(self, r, parent):
        with self.state.db() as db:
            if not db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='zotero_imports'"
            ).fetchone():
                return
            entries = db.execute(
                "SELECT identity,data FROM zotero_imports WHERE server=? AND identity LIKE 'attachment:%'",
                (self.api.server_id,),
            ).fetchall()
        for ident, raw in entries:
            saved = json.loads(raw)
            payload = saved.get("payload", {})
            if payload.get("parentItem") != parent["key"]:
                continue
            expected = saved.get("expected_sha256")
            if not isinstance(expected, str) or len(expected) != 64:
                raise Blocked("attachment_journal_hash_missing_or_conflicting")
            # Read-only reconciliation validates every owned child before any
            # generic PDF can satisfy this parent, including deleted/moved rows.
            row = self.ensure(
                "items", ident, payload, dry=True, expected_sha256=expected
            )
            if row["key"] == "<new-item>":
                continue
            path = self.api.file(row["key"])
            if path and Path(path).is_file():
                checked = verify_pdf(path, r)
                if checked.get("sha256") != expected or checked["status"] != "verified":
                    raise Blocked("attachment_hash_mismatch")

    def attachment(self, r, parent, dry):
        self.verify_owned_attachments(r, parent)
        for child in self.api.all("items"):
            if (
                child.get("parentItem") != parent["key"]
                or child.get("itemType") != "attachment"
                or child.get("contentType") != "application/pdf"
                or child.get("deleted")
            ):
                continue
            path = self.api.file(child["key"])
            if path and Path(path).is_file():
                check = verify_pdf(path, r)
                if check["status"] != "verified":
                    raise Blocked("existing_pdf_requires_review")
                return {
                    "status": "present",
                    "key": child["key"],
                    "sha256": check["sha256"],
                }
        source = r.get("download", {}).get("path")
        if not source:
            return {"status": "missing"}
        source = Path(source)
        if not source.is_file() or source.stat().st_size > 100 * 1024 * 1024:
            return {"status": "unverified"}
        with tempfile.TemporaryDirectory(
            prefix="zotero-import-", dir=self.state.root
        ) as temp:
            snapshot = Path(temp) / "paper.pdf"
            shutil.copyfile(source, snapshot)
            checked = verify_pdf(snapshot, r)
            if checked["status"] != "verified":
                return {"status": "unverified"}
            if dry:
                return {"status": "would_attach", "sha256": checked["sha256"]}
            ident = "attachment:" + digest([parent["key"], checked["sha256"]])
            payload = {
                "itemType": "attachment",
                "parentItem": parent["key"],
                "title": "Full Text",
                "linkMode": "imported_file",
                "contentType": "application/pdf",
                "filename": "paper.pdf",
            }
            row = self.ensure(
                "items", ident, payload, expected_sha256=checked["sha256"]
            )
            path = self.api.file(row["key"])
            if not path or not Path(path).is_file():
                self.api.upload(row["key"], snapshot)
            path = self.api.file(row["key"])
            if not path or not Path(path).is_file():
                raise Blocked("attachment_not_available")
            verified = verify_pdf(path, r)
            if (
                verified.get("sha256") != checked["sha256"]
                or verified["status"] != "verified"
            ):
                raise Blocked("attachment_hash_mismatch")
            return {
                "status": "attached",
                "key": row["key"],
                "sha256": checked["sha256"],
            }

    def run(
        self,
        run,
        records,
        ids,
        collection,
        approved=False,
        dry_run=False,
        create_collection=False,
    ):
        if not approved and not dry_run:
            raise Blocked("selection_approval_required")
        selected = select(records, ids)
        output = []
        remaining = []
        with self.state.request_lock("zotero-import:" + self.api.server_id):
            target = self.collection(collection, create_collection, dry_run)
            for r in selected:
                info = {}
                try:
                    parent, action = self.parent(r, target, dry_run)
                    info = {
                        "item_key": parent["key"],
                        "action": action,
                        "collection_key": target,
                    }
                    attachment = self.attachment(r, parent, dry_run)
                    info["attachment"] = attachment
                    if attachment["status"] in ("missing", "unverified"):
                        remaining.append(
                            {
                                "id": r["id"],
                                "item_key": parent["key"],
                                "reason": "pdf_" + attachment["status"],
                            }
                        )
                except (Blocked, OSError, ValueError) as e:
                    remaining.append(
                        {
                            "id": r["id"],
                            **info,
                            "reason": (
                                e.code
                                if isinstance(e, Blocked)
                                else "local_import_io_error"
                            ),
                        }
                    )
                r["zotero_import"] = info
                output.append(r)
        return {
            "schema_version": 1,
            "run_id": run,
            "status": "partial" if remaining else "complete",
            "dry_run": dry_run,
            "collection_key": target,
            "records": output,
            "remaining_work": remaining,
            "completed": [
                r["id"]
                for r in output
                if r["zotero_import"].get("attachment", {}).get("status")
                in ("attached", "present", "would_attach")
            ],
            "usage": self.state.usage(run),
        }
