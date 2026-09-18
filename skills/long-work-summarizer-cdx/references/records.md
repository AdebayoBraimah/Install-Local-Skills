# CLI and records

Invoke `python scripts/long_work.py --vault /absolute/vault OP ...`. Every output is JSON with schema_version 1. Errors return exit 2 and blocked status; unexpected failures return exit 1 and failed status. Error records retain the resume selector and unresolved reason, with empty output_paths and null coverage when this failed operation could not establish them. A successful operation may return a partial or blocked reading status without a CLI error. Inspect status, not just exit code.

| Operation | Arguments | Meaning |
|---|---|---|
| prepare | PDF, item key or BBT key; optional --library-id, --attachment, --book-id, --citation-key, --index-path, --dry-run | Resolve identity, inspect source, resume or invalidate changed hash |
| prepare | --collection NAME | Read-only unique-item routing inventory; process returned books individually |
| next | BOOK-ID; optional --chapters ch-02 ch-03, --ocr | Persist requested scope, extract next bounded unread chunk or identify next synthesis step |
| record | BOOK-ID --input JSON | Validate and save mapping, chunk, chapter or synthesis; refresh existing publications so invalidated coverage cannot stay full |
| publish | BOOK-ID | Publish available verified chapters and update index, keeping conflicts separate |
| status | BOOK-ID | Reconcile interrupted publication; report scope and coverage |
| verify | BOOK-ID | Check managed hashes, YAML and generated links; incomplete reading remains partial |

Work manifests include identity, metadata/citation, PDF hash/path, bookmarks, page labels, mapping, chunk evidence, results, selected scope, synthesis, published region/result hashes, and conflicts. Zotero identity is server ID + users/0 + item key. Local IDs persist in this vault's manifests; same path or unchanged PDF hash resumes. Use --book-id for explicit relocation with changed content. A caller-supplied library ID must identify the same personal library used by its configured CLI. Group libraries are not supported by the installed CLI.

Every input has `schema_version: 1`, `kind`, and `source_hash`. Examples below omit no required fields, except the actual book's hash must replace the example string.

```json
{"schema_version":1,"kind":"mapping","source_hash":"actual SHA-256","chapters":[{"id":"ch-01","title":"Foundations","start":1,"end":2,"confirmed":true,"boundary_evidence":"Contents and visible chapter heading agree"}],"exclusions":[{"pages":[3],"reason":"Blank after chapter"}]}
```

The mapping must account for every page exactly once. Uncertain chapters have confirmed false. A changed source requires `match_evidence` for every reused old ID. New chapters use fresh IDs. Optional `labels` is a full-length array of strings or null, accompanied by `label_evidence` describing visual checks; this overrides misleading embedded PDF labels.

```json
{"schema_version":1,"kind":"chunk","source_hash":"actual SHA-256","chapter_id":"ch-01","pages":[1,2],"sections":[{"title":"1.1 State and transition","pages":[1,2],"evidence":"Read the state definition and transition example; checked that transition probabilities sum to one."}],"unresolved":[]}
```

A chunk holds 1–8 unique pages within its confirmed chapter. Every page needs section evidence. Retry unresolved chunks with exactly the original page set. Overlaps are rejected. A nonempty unresolved list prevents those pages from counting as read. Chunk evidence can explicitly inventory blank end pages or exercises.

```json
{"schema_version":1,"kind":"chapter","source_hash":"actual SHA-256","chapter_id":"ch-01","note":"## 1.1 State and transition\n\nA source-grounded explanation, with PDF page citations.","citations":[1,2],"verified":true,"verification":{"sections":true,"mathematics":true,"citations":true,"figures":true},"figures":[],"unresolved":[]}
```

All chapter pages must have resolved chunk evidence. Verification flags are reader attestations, not automatic mathematical proof. Each figure includes `path` relative to the vault, `page` as a PDF number and `inspected: true`. If export fails after successful inspection, omit path and supply `description` and `export_error`; keep the page citation in the note.

```json
{"schema_version":1,"kind":"synthesis","source_hash":"actual SHA-256","chapters":["ch-01"],"verified":true,"note":"Synthesis of the specified chapters, naming dependencies and shared notation."}
```

Synthesis chapter IDs must equal the persisted requested scope. `run-result.json` records status, output paths, coverage totals, unresolved work and resume_selector. `complete` applies to requested scope only. `book_coverage` is unread, scanned, partial or full. A helper cannot establish that an agent actually comprehended text; the saved specific evidence and reader verification make that claim reviewable.

Conflict proposals stay in `works/BOOK-ID/conflicts/`. Original-region edits, removed markers, identity edits or filename collisions block replacement. The pending transaction includes before/after hashes and is reconciled when a command resumes. If files changed concurrently, preserve the proposed transaction separately.
