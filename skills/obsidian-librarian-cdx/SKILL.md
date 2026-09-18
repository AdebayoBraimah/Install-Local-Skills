---
name: obsidian-librarian-cdx
description: Maintain Zotero literature notes incrementally in an Obsidian vault. Use for library scans, new or changed papers, PDF upgrades, conservative note adoption, targeted hub maintenance, and resumable librarian runs.
---

# Incremental Obsidian librarian

Use the deterministic helper for source inventory, assignments, publication and state. Delegate paper reading to `~/.agents/skills/lit-summarizer-cdx/SKILL.md` in librarian worker mode. Delegate explicitly selected books to `~/.codex/skills/long-work-summarizer-cdx/SKILL.md`. Read [maintenance.md](references/maintenance.md) for operation and [records.md](references/records.md) for worker and resolution contracts.

Use `$OBSIDIAN_VAULT`, the current vault, or the user's explicit path. Invoke:

```bash
~/anaconda3/bin/python ~/.codex/skills/obsidian-librarian-cdx/scripts/librarian.py --vault /absolute/vault scan
```

1. Scan the whole personal library unless the user supplies repeated `--item KEY` or `--collection KEY_OR_EXACT_PATH` selectors. Previously completed collections and unfiled items remain eligible. `scan --dry-run` is read-only and stops before workers. Do not convert a requested dry run into a real scan.
2. For an existing run, resume it directly. Run `next --run ID --limit N`. Metadata assignments need an empty sections object and no reader. Paper `generate` assignments control eligibility regardless of historical progress. Dispatch bounded summarizer workers with the assignment, the worker reference and its source; only assigned staging paths are writable by paper workers.
3. Record each worker JSON using `record --run ID --input FILE`. Run `publish --run ID` after results. On resume, call publish even if next returns no assignments; saved proposals, recovery or linking may still be pending. Publication and linking have distinct checkpoints. A `link` assignment means call publish to retry deterministic targeted linking; do not regenerate the paper.
4. Repeat within the bounded retry allowance, then inspect `status --run ID`. A successful child exit or successful record is not publication success. Report conflicts, unavailable sources, deferred books, failures and actual coverage. Continue independent items.

A routine scan records book changes and defers study. For `book` assignments, use the supplied `book.library_id`, attachment, index path and existing book ID/resume selector with long-work prepare. This maps the actual personal-library identity onto the helper's existing server-bound identity. Preserve its chapter evidence and exclusive book publication ownership. Record its run-result path after long-work verify. Partial coverage remains incomplete here.

Workers never publish paper notes, rewrite the progress tracker, run the final library-wide linker pass, commit, or notify. The librarian orchestrator owns one direct-invocation completion or observed-stop alert via `alert-me`. For launcher-driven runs or `--no-notify` requests, leave notifications to the launcher or suppress them. No scheduling, paper acquisition, Zotero writes, group libraries or automatic commits are part of this workflow.

Use a supplied attachment choice as `scan --attachment ITEM=ATTACHMENT`. For conflicts, show the saved proposal and current destination. Record a resolution only when the user's instructions authorize that exact adoption or replacement; never infer approval from a worker's success. Missing or malformed markers require repair by an authorized edit before replacement can proceed.
