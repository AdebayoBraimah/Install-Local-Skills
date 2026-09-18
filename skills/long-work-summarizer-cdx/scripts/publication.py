"""Managed regions with write-ahead recovery and optimistic edit protection."""

import copy
import json
import re
from datetime import datetime
from pathlib import Path
import yaml
from state import atomic, contained, digest, report, save, require, read_pages, chapter

BEGIN = "<!-- long-work-study:start -->"
END = "<!-- long-work-study:end -->"


def region(text):
    require(
        text.count(BEGIN) == 1 and text.count(END) == 1,
        "Managed region removed or duplicated",
    )
    a = text.index(BEGIN)
    b = text.index(END) + len(END)
    require(a < b, "Invalid managed markers")
    return a, b, text[a:b]


def fm(text):
    require(
        text.startswith("---\n") and "\n---\n" in text[4:],
        "Valid YAML frontmatter required",
    )
    end = text.index("\n---\n", 4)
    data = yaml.safe_load(text[4:end])
    require(isinstance(data, dict), "Frontmatter must be a mapping")
    return data, end


def header(m, cid=None):
    now = datetime.now()
    data = {
        "Title": "[["
        + (m["note_prefix"] + "-" + cid if cid else Path(m["index_path"]).stem)
        + "]]",
        "Medium": ["Misc-source"],
        "Category": ["Literature"],
        "tags": ["textbook"],
        "Book-ID": m["book_id"],
        "Source-Quality": "pdf-full",
        "Reading-Coverage": "unread",
        "Date Created": now.strftime("%a-%m-%d-%Y"),
        "Time Created": now.strftime("%I:%M:%S %p").lower(),
    }
    if cid:
        data.update(
            {"Chapter-ID": cid, "Parent-Book": "[[" + Path(m["index_path"]).stem + "]]"}
        )
    elif m["metadata"].get("key"):
        data["Zotero-Key"] = m["metadata"]["key"]
    return (
        "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True) + "---\n\n"
    )


def coverage_field(text, value, previous):
    data, end = fm(text)
    if "Reading-Coverage" in data:
        require(
            previous is not None and data["Reading-Coverage"] == previous,
            "Reading-Coverage was edited or is unmanaged",
        )
        prefix = re.sub(
            r"^Reading-Coverage:.*$",
            f"Reading-Coverage: {value}",
            text[:end],
            flags=re.M,
        )
        return prefix + text[end:]
    return text[:end] + f"\nReading-Coverage: {value}" + text[end:]


def reconcile(vault, root, m):
    tx = root / "works" / m["book_id"] / "pending.json"
    if not tx.exists():
        return
    data = json.loads(tx.read_text())
    path = contained(vault, data["path"])
    actual = digest(path.read_bytes()) if path.exists() else None
    if actual == data["after_hash"]:
        m["published"][data["key"]] = data["checkpoint"]
        save(root, m)
        tx.unlink()
    elif actual == data["before_hash"]:
        atomic(path, data["text"])
        m["published"][data["key"]] = data["checkpoint"]
        save(root, m)
        tx.unlink()
    else:
        conflict(
            root,
            m,
            data["key"],
            data["text"],
            "Interrupted publication conflicts with current file",
        )
        save(root, m)
        tx.unlink()


def conflict(root, m, key, proposal, reason):
    atomic(
        root
        / "works"
        / m["book_id"]
        / "conflicts"
        / (key + "-" + digest(proposal)[:12] + ".md"),
        proposal,
    )
    message = key + ": " + reason
    if message not in m["conflicts"]:
        m["conflicts"].append(message)


def write_region(vault, root, m, key, path, body, coverage, extra=None):
    p = contained(vault, path)
    old = p.read_text() if p.exists() else None
    previous = m["published"].get(key)
    require(
        BEGIN not in body and END not in body, "Reserved marker in generated content"
    )
    generated = BEGIN + "\n" + body.strip() + "\n" + END
    try:
        if old is None:
            require(previous is None, "Previously published note was deleted")
            require(
                not any(x.resolve() != p for x in Path(vault).rglob(p.name)),
                "Note filename is not globally unique",
            )
            text = header(m, None if key == "index" else key) + generated + "\n"
            previous_coverage = "unread"
        elif previous:
            a, b, found = region(old)
            require(
                digest(found) == previous["region_hash"], "Generated region was edited"
            )
            text = old[:a] + generated + old[b:]
            previous_coverage = previous["coverage"]
        else:
            require(key == "index", "Chapter filename already exists")
            existing, _ = fm(old)
            require(
                existing.get("Book-ID", m["book_id"]) == m["book_id"],
                "Index belongs to another book",
            )
            require(
                BEGIN not in old and END not in old, "Unowned managed region exists"
            )
            text = old + "\n\n" + generated + "\n"
            previous_coverage = None
        text = coverage_field(text, coverage, previous_coverage)
        # User-owned metadata is kept; generated chapter identities must remain truthful.
        data, _ = fm(text)
        if key != "index":
            require(
                data.get("Book-ID") == m["book_id"]
                and data.get("Chapter-ID") == key
                and "Zotero-Key" not in data,
                "Chapter identity metadata edited",
            )
    except ValueError as e:
        conflict(root, m, key, generated, str(e))
        return False
    checkpoint = {
        "path": path,
        "region_hash": digest(generated),
        "source_hash": m["source_hash"],
        "coverage": coverage,
        **(extra or {}),
    }
    tx = root / "works" / m["book_id"] / "pending.json"
    data = {
        "key": key,
        "path": path,
        "before_hash": digest(old) if old is not None else None,
        "after_hash": digest(text),
        "text": text,
        "checkpoint": checkpoint,
    }
    atomic(tx, data)
    # Recheck immediately before replacement. The OS lock serializes helper writers.
    require(
        (digest(p.read_bytes()) if p.exists() else None) == data["before_hash"],
        "Note changed during publication; pending transaction retained",
    )
    if old != text:
        atomic(p, text)
    m["published"][key] = checkpoint
    save(root, m)
    tx.unlink()
    m["conflicts"] = [x for x in m["conflicts"] if not x.startswith(key + ":")]
    return True


def publish(vault, root, m):
    reconcile(vault, root, m)
    for key, pub in list(m["published"].items()):
        if key == "index":
            continue
        current = pub["source_hash"] == m["source_hash"]
        valid = current and key in m["results"]
        target = "partial" if current and read_pages(m, key) else "unread"
        if valid or pub["coverage"] == target:
            continue
        try:
            path = contained(vault, pub["path"])
            text = path.read_text()
            require(
                digest(region(text)[2]) == pub["region_hash"],
                "Stale generated region was edited",
            )
            write_region(
                vault,
                root,
                m,
                key,
                pub["path"],
                region(text)[2][len(BEGIN) : -len(END)].strip(),
                target,
                {
                    "source_hash": pub["source_hash"],
                    "result_hash": pub.get("result_hash"),
                },
            )
        except (ValueError, OSError) as e:
            conflict(root, m, key, "Source changed. Prior coverage is stale.", str(e))
    for cid in m["scope"]:
        if cid not in m["results"]:
            continue
        result = m["results"][cid]
        for f in result.get("figures", []):
            if f.get("path"):
                require(contained(vault, f["path"]).is_file(), "Figure file missing")
        path = (
            m["published"].get(cid, {}).get("path")
            or f"{m['chapter_dir']}/{m['note_prefix']}-{cid}.md"
        )
        write_region(
            vault,
            root,
            m,
            cid,
            path,
            result["note"],
            "full",
            {"result_hash": digest(json.dumps(result, sort_keys=True))},
        )
    syn = m.get("synthesis", {})
    provisional = copy.deepcopy(m)
    provisional["published"]["index"] = {
        "synthesis_hash": digest(json.dumps(syn, sort_keys=True))
    }
    coverage = report(provisional)["book_coverage"]
    rows = []
    for c in m["chapters"]:
        pub = m["published"].get(c["id"])
        current = (
            pub
            and pub.get("source_hash") == m["source_hash"]
            and c["id"] in m["results"]
        )
        label = (
            "full"
            if current
            else (
                "partial"
                if any(x["chapter_id"] == c["id"] for x in m["chunks"].values())
                else "unread"
            )
        )
        title = (
            "[[" + Path(pub["path"]).stem + "\\|" + c["title"] + "]]"
            if pub
            else c["title"]
        )
        rows.append(f"| {c['id']} | {title} | PDF {c['start']}–{c['end']} | {label} |")
    stale = [
        p
        for key, p in m["published"].items()
        if key != "index" and p.get("source_hash") != m["source_hash"]
    ]
    body = (
        "## Managed study index\n\nReading coverage: "
        + coverage
        + ". Source SHA-256: `"
        + m["source_hash"]
        + "`.\n\n"
    )
    if m.get("stale"):
        body += "Prior-source notes are stale until remapped and reread.\n\n"
    body += "| Chapter | Note | Pages | Coverage |\n|---|---|---|---|\n" + "\n".join(
        rows
    )
    if stale:
        body += "\n\n### Preserved stale notes\n\n" + "\n".join(
            "- [[" + Path(p["path"]).stem + "]]" for p in stale
        )
    body += "\n\n### Scope synthesis\n\n" + (
        "Coverage: " + ", ".join(syn.get("chapters", [])) + ".\n\n" + syn["note"]
        if syn
        else "Pending. No final book synthesis is claimed."
    )
    body += (
        "\n\n### Current citation\n\n```bibtex\n"
        + (m["metadata"].get("citation") or "Bibliographic citation unknown.")
        + "\n```"
    )
    write_region(
        vault,
        root,
        m,
        "index",
        m["index_path"],
        body,
        coverage,
        {"synthesis_hash": digest(json.dumps(syn, sort_keys=True))},
    )
    save(root, m)
    return report(m)


def verify(vault, root, m):
    errors = []
    for key, pub in m["published"].items():
        try:
            p = contained(vault, pub["path"])
            text = p.read_text()
            data, _ = fm(text)
            require(
                digest(region(text)[2]) == pub["region_hash"],
                "Published region changed",
            )
            require(
                data.get("Reading-Coverage") == pub["coverage"],
                "Coverage property changed",
            )
            if key != "index":
                require("Zotero-Key" not in data, "Chapter repeats Zotero key")
                if pub["coverage"] == "full":
                    c = chapter(m, key)
                    require(
                        key in m["results"]
                        and set(range(c["start"], c["end"] + 1)) <= read_pages(m, key),
                        "Full published coverage lacks reading evidence",
                    )
                    require(
                        pub["result_hash"]
                        == digest(json.dumps(m["results"][key], sort_keys=True)),
                        "Published result is out of date",
                    )
            # Only generated links are owned by this helper; legacy links are untouched.
            for raw_link in re.findall(r"\[\[([^\]]+)\]\]", region(text)[2]):
                target, separator, _ = raw_link.partition("|")
                # Obsidian table aliases escape the separator: [[target\\|label]].
                if separator and target.endswith("\\"):
                    target = target[:-1]
                link = target.split("#", 1)[0]
                if not link:  # A heading in the current note needs no file lookup.
                    continue
                require(
                    (
                        any(vault.rglob(Path(link).name))
                        if Path(link).suffix
                        else any(vault.rglob(Path(link).name + ".md"))
                    ),
                    "Unresolved link: " + link,
                )
        except (ValueError, OSError) as e:
            errors.append(key + ": " + str(e))
    r = report(m)
    r["verification_errors"] = errors
    require(
        not errors and not m.get("conflicts"),
        "Verification failed: " + "; ".join(errors + m.get("conflicts", [])),
    )
    return r
