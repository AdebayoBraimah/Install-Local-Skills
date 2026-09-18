#!/usr/bin/env python3
"""Incremental librarian public commands. JSON stdout; no reader synthesis here."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys
import uuid

import publication as pub
import inventory as inv
from state import atomic, confined, digest, file_hash, load, locked, save


def report(state, run_id=None):
    keys = state["runs"][run_id]["keys"] if run_id else list(state["items"])
    rows = [dict(key=k, **state["items"][k]) for k in keys]
    actionable = sum(
        bool(x.get("pending"))
        and not x.get("blocked")
        and not x.get("deferred")
        and (
            not run_id
            or bool(x.get("proposal"))
            or x["attempts"].get(run_id + ":" + x["pending"][0], 0) < 3
        )
        for x in rows
    )
    unfinished = sum(
        bool(x.get("pending") or x.get("blocked")) and not x.get("deferred")
        for x in rows
    )
    return dict(
        schema_version=1,
        run_id=run_id,
        actionable=actionable,
        unfinished=unfinished,
        status=(
            "blocked"
            if unfinished and not actionable
            else "partial" if unfinished else "complete"
        ),
        items=rows,
    )


def scan(a, root, state):
    source = inv.capture(a.snapshot)
    ident = inv.identity(source)
    if state["identity"] and state["identity"] != ident:
        raise ValueError("Incompatible library identity")
    previous = state.get("snapshot")
    delta = inv.diff(previous, source) if previous else None
    state["identity"] = ident
    selected = inv.selected_keys(source, a.item, a.collection)
    selections = {}
    for v in a.attachment:
        parts = v.split("=")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Use --attachment ITEM=ATTACHMENT")
        if parts[0] not in selected:
            raise ValueError("Attachment item is outside selected scope")
        selections[parts[0]] = parts[1]
    current = inv.sources(source, state["items"], selections)
    candidates = inv.notes(a.vault)
    keys = []
    for key in sorted(selected & current.keys()):
        src = current[key]
        old = state["items"].get(key)
        if a.retry_failed and not (old and old.get("errors")):
            continue
        if old is None:
            adopted, problem = inv.adopt(a.vault, src, candidates)
            path = (
                adopted["path"]
                if adopted
                else "Ideas/Research/" + src["citation_key"] + ".md"
            )
            if not re.fullmatch(r"[^/\\\x00-\x1f]+", src["citation_key"]):
                problem = "unsafe_citation_filename"
            old = dict(
                item=src["item"],
                path=path,
                adoption="adopted_unverified" if adopted else "new",
                baseline=src["fingerprints"] if adopted else None,
                published=None,
                sections={},
                owned_metadata={},
                legacy_quality=(
                    inv.scalar(adopted["data"].get("Source-Quality"))
                    if adopted
                    else None
                ),
                pending=[],
                errors=[],
                attempts={},
                revision=0,
                blocked=problem,
            )
            state["items"][key] = old
        prior = old.get("observed")
        if (
            not prior
            or inv.relevant(prior) != inv.relevant(src["fingerprints"])
            or old.get("blocked") == "source_removed"
        ):
            old["revision"] += 1
            if old.get("proposal"):
                prior_run, prior_token = old.pop("proposal")
                state["runs"][prior_run]["results"][prior_token][
                    "publication"
                ] = "superseded"
            if old.get("blocked") in {
                "source_unavailable",
                "source_removed",
                "source_drift",
                "attachment_ambiguous",
                "selected_attachment_missing",
                "worker_blocked",
                "publication_conflict",
            }:
                old["blocked"] = None
        old.update(
            observed=src["fingerprints"],
            source=src,
            selected_attachment=src["selected_attachment"],
        )
        old["reports"] = []
        if prior and prior["annotations"] != src["fingerprints"]["annotations"]:
            old["reports"].append("annotations_changed_report_only")
        if not src["fingerprints"]["pdf"] and (prior or {}).get("pdf"):
            old["reports"].append("pdf_unavailable")
        if src["problem"]:
            old["blocked"] = src["problem"]
        if (
            old["adoption"] == "new"
            and not old["sections"]
            and confined(a.vault, old["path"]).exists()
        ):
            old["blocked"] = "filename_collision"
        if old["adoption"] != "new" and not confined(a.vault, old["path"]).exists():
            old["blocked"] = "established_note_missing"
        op = inv.action(src, old, a.refresh)
        if src["metadata"]["itemType"] == "book":
            old["deferred"] = not bool(a.item or a.collection)
            if not old["deferred"] and old.get("blocked") in {
                "book_partial",
                "book_blocked",
            }:
                old["blocked"] = None
            old["reports"].append("book_study_deferred")
            op = (
                "book"
                if (a.item or a.collection) and (op or old.get("pending"))
                else None
            )
        if op:
            if op == "generate":
                old["pending"] = [p for p in old["pending"] if p != "metadata"]
            if op not in old["pending"] and not (
                op == "metadata" and "generate" in old["pending"]
            ):
                old["pending"].insert(0, op)
        old["destination_hash"] = file_hash(confined(a.vault, old["path"]))
        keys.append(key)
    for key, old in state["items"].items():
        if key not in current:
            old["reports"] = ["source_removed"]
            old["blocked"] = "source_removed"
            if not a.item and not a.collection:
                keys.append(key)
    # Destination identity conflicts apply to every claimant.
    paths = {}
    for key, old in state["items"].items():
        paths.setdefault(old["path"].casefold(), []).append(key)
    for same in paths.values():
        if len(same) > 1:
            for key in same:
                state["items"][key]["blocked"] = "filename_collision"
    rid = uuid.uuid4().hex
    state["runs"][rid] = dict(
        keys=sorted(set(keys)),
        assignments={},
        results={},
        snapshot=source,
        delta=delta,
        explicit=bool(a.item or a.collection),
    )
    state["snapshot"] = source
    if not a.dry_run:
        atomic(root / "runs" / rid / "manifest.json", state["runs"][rid])
        save(root, state)
    out = report(state, rid)
    out["dry_run"] = a.dry_run
    return out


def next_work(a, root, state):
    run = state["runs"][a.run]
    assignments = []
    for key in run["keys"]:
        x = state["items"][key]
        if (
            x.get("blocked")
            or x.get("deferred")
            or bool(x.get("proposal"))
            or not x["pending"]
        ):
            continue
        op = x["pending"][0]
        if x["attempts"].get(a.run + ":" + op, 0) >= 3:
            continue
        token = digest(
            [
                a.run,
                key,
                op,
                x["revision"],
                x["destination_hash"],
                x["attempts"].get(a.run + ":" + op, 0),
            ]
        )[:24]
        entry = dict(
            schema_version=1,
            assignment_id=token,
            item=x["item"],
            operation=op,
            revision=x["revision"],
            source_fingerprints=x["observed"],
            expected_destination_hashes={x["path"]: x["destination_hash"]},
            path=x["path"],
            source_quality=x["source"]["source_quality"],
            source=x["source"],
            staging_dir=f".obsidian-librarian/staging/{a.run}/{token}",
        )
        if op == "book":
            library = "local:" + x["item"]["server_id"] + ":users/0"
            identity = library + ":" + key
            existing = []
            for f in (a.vault / ".long-work-summarizer/works").glob("*/manifest.json"):
                m = json.loads(f.read_text())
                if m.get("identity") == identity:
                    existing.append(m)
            if len(existing) > 1:
                raise ValueError("Duplicate long-work book identity")
            if existing and existing[0]["index_path"] != x["path"]:
                raise ValueError(
                    "Book index path disagrees with existing long-work identity"
                )
            entry["book"] = dict(
                library_id=library,
                identity=identity,
                index_path=x["path"],
                book_id=existing[0]["book_id"] if existing else None,
                resume_selector=x.get("book_result", {}).get("resume_selector"),
                attachment=x["selected_attachment"],
            )
        run["assignments"][token] = entry
        assignments.append(entry)
        if len(assignments) >= a.limit:
            break
    save(root, state)
    return dict(schema_version=1, run_id=a.run, assignments=assignments)


def resolve(a, root, state, result):
    key = result.get("item", {}).get("key")
    x = state["items"].get(key)
    if (
        not x
        or result.get("schema_version") != 1
        or result.get("item") != x["item"]
        or result.get("revision") != x["revision"]
    ):
        raise ValueError("Resolution identity or revision mismatch")
    path = result.get("path", x["path"])
    target = confined(a.vault, path)
    if result.get("expected_destination_hashes") != {path: file_hash(target)}:
        raise ValueError("Resolution destination changed")
    action = result.get("action")
    if action == "adopt_note":
        if x["sections"] or x.get("published"):
            raise ValueError(
                "Cannot discard an established publication ledger through adoption"
            )
        if not target.is_file():
            raise ValueError("Adoption needs an existing note")
        if any(
            k != key and other["path"].casefold() == path.casefold()
            for k, other in state["items"].items()
        ):
            raise ValueError("Path belongs to another work")
        inv.frontmatter(target.read_text())
        x.update(
            path=path,
            adoption="adopted_unverified",
            baseline=x["observed"],
            published=None,
            sections={},
            owned_metadata={},
            pending=[],
        )
    elif action == "approve_replacement":
        names = result.get("approve_sections", [])
        if not names or not set(names) <= set(x["sections"]) | {"links"}:
            raise ValueError("Name owned sections to approve")
        text = target.read_text()
        for name in names:
            h = digest(pub.region(text, name)[2])
            if name == "links":
                state.setdefault("links", {})[path] = h
            else:
                x["sections"][name] = h
    elif action == "retry":
        if x.get("blocked") not in {
            "worker_blocked",
            "source_unavailable",
            "book_partial",
            "book_blocked",
        }:
            raise ValueError(
                "This conflict requires adoption or named-section approval"
            )
    else:
        raise ValueError("Unknown resolution action")
    if x.get("proposal"):
        r, t = x.pop("proposal")
        state["runs"][r]["results"][t]["publication"] = "superseded_by_resolution"
    x["blocked"] = None
    x["revision"] += 1
    x["destination_hash"] = file_hash(target)
    x["attempts"] = {}
    atomic(root / "resolutions" / (digest(result) + ".json"), result)
    save(root, state)
    return report(state, a.run)


def record_work(a, root, state):
    result = json.loads(a.input.read_text())
    run = state["runs"][a.run]
    if result.get("kind") == "resolution":
        return resolve(a, root, state, result)
    token = result.get("assignment_id")
    assignment = run["assignments"].get(token)
    if not assignment:
        raise ValueError("Unknown assignment")
    for k in [
        "schema_version",
        "item",
        "operation",
        "revision",
        "source_fingerprints",
        "expected_destination_hashes",
    ]:
        if result.get(k) != assignment[k]:
            raise ValueError("Invalid worker contract: " + k)
    key = result["item"]["key"]
    x = state["items"][key]
    if x["revision"] != result["revision"]:
        raise ValueError("Stale worker state revision")
    if result.get("outcome") not in {"success", "failed", "blocked"}:
        raise ValueError("Invalid worker outcome")
    prior = run["results"].get(token)
    if prior and prior["record"] == result:
        return dict(schema_version=1, status="already_recorded")
    if prior and prior["record"]["outcome"] == "success":
        raise ValueError("Assignment already has a result")
    if result["outcome"] == "success":
        if result["operation"] == "book":
            return record_book(a, root, state, result, assignment)
        if result["operation"] == "link":
            raise ValueError("Linking is deterministic; run publish to resume")
        if result["operation"] == "generate" and (
            not isinstance(result.get("sections", {}).get("content"), str)
            or not result["sections"]["content"].strip()
        ):
            raise ValueError("Missing generated content")
        if any(k != "content" for k in result.get("sections", {})):
            raise ValueError("Unknown generated section")
        if any("<!-- librarian:" in v for v in result.get("sections", {}).values()):
            raise ValueError("Reserved managed marker")
        for asset in result.get("assets", []):
            if not asset["staged_path"].startswith(assignment["staging_dir"] + "/"):
                raise ValueError("Asset is outside assigned staging")
            if not asset["path"].startswith("Files/Images/" + token + "-"):
                raise ValueError("Asset must use revision-specific name")
            if file_hash(confined(a.vault, asset["staged_path"])) != asset["sha256"]:
                raise ValueError("Asset hash mismatch")
            confined(a.vault, asset["path"])
        if not isinstance(result.get("keywords", []), list) or any(
            not isinstance(k, str) for k in result.get("keywords", [])
        ):
            raise ValueError("Keywords must be strings")
        x["proposal"] = [a.run, token]
    else:
        transient = result.get("transient") is True
        x["attempts"][a.run + ":" + result["operation"]] = (
            x["attempts"].get(a.run + ":" + result["operation"], 0) + 1
        )
        x["errors"].append(
            dict(
                stage=result["operation"],
                reason=result.get("error", "Worker failed"),
                run=a.run,
                transient=transient,
            )
        )
        if not transient:
            x["blocked"] = "worker_blocked"
    run["results"][token] = dict(
        record=result,
        publication="pending" if result["outcome"] == "success" else result["outcome"],
    )
    atomic(root / "runs" / a.run / "results" / (token + ".json"), run["results"][token])
    save(root, state)
    return dict(schema_version=1, status="recorded")


def record_book(a, root, state, result, assignment):
    import subprocess

    key = result["item"]["key"]
    x = state["items"][key]
    relative = result.get("book_result_path", "")
    if not re.fullmatch(
        r"\.long-work-summarizer/works/[A-Za-z0-9._-]+/run-result.json", relative
    ):
        raise ValueError("Expected long-work run-result path")
    path = confined(a.vault, relative)
    m = json.loads((path.parent / "manifest.json").read_text())
    if (
        m.get("identity") != assignment["book"]["identity"]
        or m.get("index_path") != x["path"]
    ):
        raise ValueError("Book identity or index mismatch")
    if m.get("source_hash") != x["observed"]["pdf"]:
        raise ValueError("Book source fingerprint mismatch")
    fresh = inv.capture(a.snapshot)
    if inv.identity(fresh) != state["identity"]:
        raise ValueError("Book library identity changed")
    current_sources = inv.sources(fresh, state["items"], {})
    if key not in current_sources or inv.relevant(
        current_sources[key]["fingerprints"]
    ) != inv.relevant(assignment["source_fingerprints"]):
        raise ValueError("Book source changed since assignment")
    helper = Path.home() / ".codex/skills/long-work-summarizer-cdx/scripts/long_work.py"
    p = subprocess.run(
        [sys.executable, str(helper), "--vault", str(a.vault), "verify", m["book_id"]],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if p.returncode:
        raise ValueError("Long-work verification failed: " + p.stdout + p.stderr)
    current = json.loads(p.stdout)
    saved = json.loads(path.read_text())
    for field in [
        "status",
        "book_coverage",
        "coverage",
        "resume_selector",
        "output_paths",
    ]:
        if current.get(field) != saved.get(field):
            raise ValueError("Long-work result does not match verified coverage")
    x["book_result"] = saved
    x.pop("proposal", None)
    x["revision"] += 1
    if confined(a.vault, x["path"]).is_file():
        x["adoption"] = "book_managed"
    x["destination_hash"] = file_hash(confined(a.vault, x["path"]))
    if saved.get("status") == "complete" and saved.get("book_coverage") == "full":
        x["pending"] = []
        x["published"] = copy.deepcopy(x["observed"])
        x["adoption"] = "book_managed"
        x["published_quality"] = "pdf-full"
        x["blocked"] = None
    else:
        x["blocked"] = (
            "book_partial"
            if saved.get("status") in {"partial", "complete"}
            else "book_blocked"
        )
    state["runs"][a.run]["results"][result["assignment_id"]] = dict(
        record=result, publication="delegated", book_result=saved
    )
    atomic(
        root / "runs" / a.run / "results" / (result["assignment_id"] + ".json"),
        state["runs"][a.run]["results"][result["assignment_id"]],
    )
    save(root, state)
    return report(state, a.run)


def publish(a, root, state):
    fresh = inv.capture(a.snapshot)
    if inv.identity(fresh) != state["identity"]:
        raise ValueError("Incompatible source identity")
    current = inv.sources(fresh, state["items"], {})
    run = state["runs"][a.run]
    proposals = [
        state["items"][key]["proposal"]
        for key in run["keys"]
        if state["items"][key].get("proposal")
    ]
    for owner_run, token in proposals:
        value = state["runs"][owner_run]["results"][token]
        if value["publication"] != "pending":
            continue
        result = value["record"]
        key = result["item"]["key"]
        x = state["items"][key]
        try:
            if key not in current or inv.relevant(
                current[key]["fingerprints"]
            ) != inv.relevant(result["source_fingerprints"]):
                raise ValueError("Source drift since assignment")
            if x["revision"] != result["revision"]:
                raise ValueError("State revision changed")
            if (
                current[key]["pdf_path"]
                and inv.hash_file(current[key]["pdf_path"])[0]
                != result["source_fingerprints"]["pdf"]
            ):
                raise ValueError("PDF changed before publication")
            for path, expected in result["expected_destination_hashes"].items():
                if file_hash(confined(a.vault, path)) != expected:
                    raise ValueError("Destination changed since assignment")
            after, writes = pub.prepare(a.vault, x, result)
            pub.transact(
                a.vault, root, state, key, after, writes, token, [owner_run, token]
            )
        except (ValueError, OSError) as e:
            pub.conflict(root, state, owner_run, token, result, str(e))
    for key in run["keys"]:
        x = state["items"][key]
        if x.get("blocked") or x["pending"] != ["link"]:
            continue
        attempt_key = a.run + ":link"
        if x["attempts"].get(attempt_key, 0) >= 3:
            continue
        try:
            pub.link(a.vault, root, state, key, a.run)
        except (ValueError, OSError) as e:
            x["attempts"][attempt_key] = x["attempts"].get(attempt_key, 0) + 1
            x["errors"].append(
                dict(
                    stage="link",
                    reason=str(e),
                    run=a.run,
                    transient=isinstance(e, OSError),
                )
            )
            if not isinstance(e, OSError):
                x["blocked"] = "link_conflict"
            save(root, state)
    pub.progress(a.vault, root, state)
    atomic(root / "runs" / a.run / "report.json", report(state, a.run))
    return report(state, a.run)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vault", required=True, type=Path)
    p.add_argument(
        "--snapshot",
        type=Path,
        help="Controlled complete source snapshot with citationKeys; tests/pilots only",
    )
    sub = p.add_subparsers(dest="op", required=True)
    s = sub.add_parser("scan")
    for name in ["item", "collection", "attachment"]:
        s.add_argument("--" + name, action="append", default=[])
    for name in ["dry-run", "refresh", "retry-failed"]:
        s.add_argument("--" + name, action="store_true")
    n = sub.add_parser("next")
    n.add_argument("--run", required=True)
    n.add_argument("--limit", type=int, default=5)
    s = sub.add_parser("status")
    s.add_argument("--run")
    r = sub.add_parser("record")
    r.add_argument("--run", required=True)
    r.add_argument("--input", required=True, type=Path)
    r = sub.add_parser("publish")
    r.add_argument("--run", required=True)
    a = p.parse_args()
    a.vault = a.vault.resolve()
    root = a.vault / ".obsidian-librarian"
    try:
        if not a.vault.is_dir():
            raise ValueError("Vault directory does not exist")
        if a.op == "status":
            out = report(load(root), a.run)
        elif a.op == "scan" and a.dry_run:
            out = scan(a, root, load(root))
        else:
            with locked(root):
                state = load(root)
                pub.recover(a.vault, root, state)
                if a.op == "scan":
                    out = scan(a, root, state)
                else:
                    if a.run not in state["runs"]:
                        raise ValueError("Unknown run")
                    if a.op == "next":
                        if a.limit < 1:
                            raise ValueError("Limit must be positive")
                        out = next_work(a, root, state)
                    elif a.op == "record":
                        out = record_work(a, root, state)
                    else:
                        out = publish(a, root, state)
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    except (ValueError, KeyError, OSError, TypeError) as e:
        print(json.dumps(dict(schema_version=1, status="blocked", error=str(e))))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
