# Maintenance operations

All helper outputs are JSON with `schema_version: 1`. Exit 0 means the command executed; inspect `status`, `actionable`, `unfinished` and item details for completion. Exit 2 is an invalid command, blocked source capture, lock contention or invalid contract. The launcher maps final partial to exit 3 and blocked to exit 4.

Global arguments precede the operation. `--vault PATH` is required. `--snapshot FILE` is only for controlled test or pilot sources and requires a complete installed-CLI snapshot plus a canonical `citationKeys` map. Available PDF hashes must match actual bytes. Production omits that option, captures the installed CLI's complete personal inventory and resolves canonical citation keys every time. Missing/failed captures cannot establish removal.

| Command | Inputs and behavior |
|---|---|
| scan | Repeated `--item`, `--collection`, `--attachment ITEM=ATTACHMENT`; `--refresh`, `--retry-failed`, `--dry-run` |
| next | `--run ID --limit N`; durable bounded assignments with revision and destination hashes |
| record | `--run ID --input FILE`; worker outcome or authorized resolution |
| publish | `--run ID`; recover interrupted writes, check current sources, apply saved results, link and project progress |
| status | Optional `--run ID`; read-only state, including prior errors and outcomes |

State is under `.obsidian-librarian/`. `state.json` is the atomic checkpoint and includes versioned run histories. `runs/` retains source manifests, worker results and reports. `transactions/` contains before/after hashes and proposed bytes before replacement. `conflicts/` and `resolutions/` preserve review evidence. Transient `staging/`, caches and locks can be ignored by Git. Keep transactions and state together when backing up. Every writing command holds the local OS lock; dry-run/status create no lock file. Status does not recover pending writes; run publish to recover.

A source fingerprint tracks bibliography, citation key, abstract, selected PDF bytes, availability, memberships, tags and annotations separately. Only annotations are report-only. PDF relocation updates the locator without summary regeneration. A lost PDF never downgrades an existing full-PDF summary. Observed state does not establish published freshness. Legacy identity matches record an unverified baseline and preserve the complete body. Filename/DOI-only candidates require review. Citation renames retain the note path.

Managed citation, content and links use independent comment markers and hashes. Existing frontmatter fields are preserved. New notes receive the standard Source-Quality, tags and Keywords fields as well as current `Librarian-*` metadata. The helper tracks ownership. Existing personal fields and creation dates stay intact. If a user edits a standard tags/Keywords list, it becomes personal metadata and is preserved; current source values continue in the separate Librarian fields. Owned-field edits require review. Source tags and worker keywords occupy separate managed fields so removals do not remove personal values. All legacy body text remains outside the new regions. Never manually delete publication journals to clear a conflict.

Publication checks fresh relevant source fingerprints, item revision and exact assignment destination hashes, then checks ownership hashes. It retains conflicting proposals. Assets must be staged under the assignment directory and published under the assignment ID prefix in `Files/Images/`; older figures remain. A transaction interrupted after replacement recognizes the after hash and completes its checkpoint without appending again. Concurrent external edits that match neither before nor after become recovery conflicts. Locks protect one maintenance host, not Google Drive peers or an editor that writes during a filesystem operation.

Targeted linking considers the changed work's previous/current concepts and relevant existing works. It writes only librarian link regions, preserves handwritten links, uses full vault-relative wikilinks and skips book/chapter writes. A new hub requires at least three distinct works, with chapters collapsed by Book-ID/Parent-Book. Generic keywords cannot create hubs. The summarizer must provide substantive concept keywords grounded in the source. Linking failure retains a separate pending stage.

Transient worker/link failures permit three attempts total in a run. A later scan retains failed stages and starts a new retry budget. `--retry-failed` restricts selection to failed work. Source absence and edit conflicts wait for source changes or authorized resolution. Repeated failed records for the same assignment are idempotent; request the next assignment for a new attempt.

Both launchers use the installed summarizer script as the authoritative implementation. The vault wrapper derives its default vault from its own location. `VAULT_PATH` takes precedence over `OBSIDIAN_VAULT`. `CODEX_BIN`, `LIBRARIAN_PYTHON`, `CLI_ZOTERO`, and `LIBRARIAN_SCRIPT` support explicit runtime overrides. Test-only `LIBRARIAN_SNAPSHOT` is forwarded through the controlled source adapter. Dry runs do not invoke Codex or write vault logs. The launcher owns one final notification and honors `--no-notify`.
