# CLI and records

Interpreter: `~/anaconda3/bin/python`, Python 3.11 with requests and keyring. Entry point: `~/.codex/skills/lit-search-cdx/scripts/lit_search.py`. Runtime data: `~/.local/share/lit-search-cdx/`. Dependencies: `pdfinfo`, `pdftotext`, and the installed cli-anything-zotero package. Automatic import additionally requires Zotero 10 running with its local API and server-bound write authorization.

| Operation | Arguments |
|---|---|
| search | `QUERY --provider scholar|openalex --limit 20` |
| enrich | `--input candidates.json [--cite-export]` |
| citations | `SEED --provider scholar|openalex --direction forward|backward --limit 20` |
| versions | `SCHOLAR_CLUSTER --limit 20` |
| fetch | `--input candidates.json --select CANDIDATE_ID ...` |
| bundle | `--input fetched.json --select CANDIDATE_ID ...` |
| import | `--input fetched.json --select CANDIDATE_ID ... --collection KEY_OR_EXACT_PATH [--create-collection] (--dry-run or --selection-approved)` |
| doctor | `[--live]` |
| auth | `status` or `import` |

Common options follow the operation: `--run-id ID`, `--output FILE`, `--report FILE`, `--state-dir DIR`. Discovery and enrichment support `--refresh`. Environment `LIT_SEARCH_RUN_ID` supplies the parent ID when omitted. Fetch and bundle are separate operations; bundle does not silently download.

Envelopes contain `schema_version`, `run_id`, `status`, `records`, `remaining_work`, and `usage`. Search also supplies completed query/pages and credential-source/account diagnostics. Exit codes: 0 complete, 2 partial, 3 blocked, 1 failed. Stdout is always JSON for operational outcomes. Resume by repeating the original command with the same run ID and without refresh. Successful pages come from durable steps; incomplete work retries against the remaining quota. A timeout stays charged even if the provider may not have billed it. Ledger reconciliation is conservative and may underuse capacity.

A record contains `id`, `title`, `authors` as an array of names, `year`, `venue`, `doi`, canonical `arxiv`, `abstract`, `snippet`, `url`, `identifiers`, `citation_counts`, `provenance`, `pdf_locations`, and `triage_flags`. Unknown metadata is null or an empty list. `identifiers` may contain `scholar_cid`, `scholar_cites`, `scholar_cluster`, and `openalex`. Preserve strings exactly. Each provenance entry identifies provider, normalized request and retrieval time. Supplemental records must use a distinct stable ID and the same fields. Add relevance, tier and topic during triage, without overwriting provider evidence.

OpenAlex citation seeds accept `W...` identifiers or DOI URLs. Scholar forward seeds require the numeric `scholar_cites`; versions require `scholar_cluster`; optional citation export uses `scholar_cid`. Backward traversal resolves each `referenced_works` ID. Missing DOI/OpenAlex identities during enrichment stay unresolved. Scholar's BibTeX endpoint provides a link; a failed second fetch records a fallback flag. Exported text is retained as evidence; bundle BibTeX uses verified metadata.

Bundles include `library.bib`, `pdfs/`, `manifest.json`. Known existing items are excluded from new-item import. Never rename or move the bibliography away from the attachment directory before import. Missing author/title/year prevents an import entry. Uncertain PDFs are stored in `quarantine/` and never attached automatically. Download checks use the first two pages and PDF title metadata; scanned or heavily reformatted papers may require manual identity review. No automatic uncertainty override exists.

## Approved Zotero import

Use the `import` operation after actual user approval of the selected papers and destination. `--selection-approved` records that approval; the flag does not authorize an unapproved selection. Do not ask for a second confirmation once approval exists. Import blocks if neither `--dry-run` nor `--selection-approved` is supplied, and the two flags are mutually exclusive. For example:

```bash
~/anaconda3/bin/python ~/.codex/skills/lit-search-cdx/scripts/lit_search.py import --input fetched.json --select CANDIDATE_ID --collection COLLECTION_KEY --selection-approved --run-id PARENT_RUN --output import.json --report import.md
```

Replace the placeholders with actual selected IDs, the approved destination and the persistent run ID. Preview the same request by replacing `--selection-approved` with `--dry-run`. Dry run reads current Zotero state without Zotero mutations, import-journal changes or credential setup; requested output files and ordinary state-directory initialization remain possible.

Personal libraries only. Resolve a destination by exact key or full path; ambiguous names block. `--create-collection` permits an approved missing top-level name, with no implicit nested hierarchy. Creation first uses a unique temporary marker name. After the returned key is durable, a version-guarded update sets the approved name. An interruption can leave that temporary name visible; resume uses its saved key and the exact temporary or intended name, never a common-name match. New records currently use Zotero `journalArticle` with single-field creator names. Missing author/title/year prevents new-item creation. Verified normalized fields and provenance are retained in new-item Extra.

Fresh library metadata controls matching. Exact DOI/arXiv identity or a unique normalized title with author evidence may reuse an item when strong identifiers do not conflict. Ambiguous or conflicting matches block the candidate; cached input Zotero keys are not authoritative. Import preserves existing metadata, tags, notes, files and all memberships, adding only the target membership and a missing verified PDF. Existing uncertain PDFs require manual resolution and are never knowingly replaced. Complete references may import without a PDF; attachment gaps remain in the output. New PDFs are copied into Zotero-managed storage, preserving downloaded originals.

The import result reports created/reused keys, collection actions, attachment states and remaining work. Partial completion retains successful earlier records. Verify returned identities, target membership and actual verified PDFs before summarization. Keep metadata-only imports in the report and outside the PDF summarization queue. The manual `bundle` operation remains available when requested or automatic import is blocked.

Import uses the installed cli-anything-zotero server-bound Keychain authorization with the local API at localhost:23119. Missing authority or changed server identity blocks writes. Resolve local authorization through Zotero's supported UI; never bypass it or forward credentials to download/upload hosts. Search-provider `auth import` below does not configure Zotero authorization.

Preserve the import journal under the state directory. Resume with the same selected input, collection and parent run ID. Zotero assigns new object keys. Before sending a create, the importer saves its UUID marker, payload and uncertain state. New parents retain the marker in Extra, new attachments in their note, and new collections initially in a unique temporary name. The returned key is saved immediately. A lost response is reconciled only through an exact unique marker and compatible payload in fresh inventory. If an uncertain create has no match, import blocks for review and does not repeat the create, even when the request may never have reached Zotero. Do not delete state or issue replacement creates. Known authorization denial can retry after authorization is resolved; explicit conflicts or rejections remain blocked. Saved owned attachment keys govern upload recovery. Unexpected collisions, changed/deleted journaled items, ambiguous identity, file changes or concurrent version changes require resolution before retry. A local lock serializes this client's imports; it does not lock Zotero UI or other clients. File and version rechecks reduce overwrite risk, but Zotero's upload precondition is not an atomic file-absence check. Another writer can race the final upload operation. Imports across records are not a library-wide transaction.

`auth import` expects owner-only permissions, for example after `chmod 600 ~/etc/search_api.env`. It reads one `SEARCH_API_KEY=...` assignment literally and refreshes Keychain through the native keyring backend. It never invokes a shell or exposes the value. Optional OpenAlex setup uses Keychain service `lit-search-cdx`, account `openalex`; supply the value through a password prompt or Keychain Access, never CLI arguments. Status reports availability, not credential validity.

Compatibility adapters retain `scholarly_search.py QUERY [MAX]` and `scholarly_snowball.py seeds.json [MAX]`. Stdout remains an array with legacy fields plus normalized metadata. Structured coverage status is on stderr and partial output returns nonzero. Set `LIT_SEARCH_RUN_ID` once for the parent review. Title-only seeds require a unique exact normalized title and usable citing ID. Ambiguous or missing seeds return per-seed errors.

## Dialog handling during Codex runs

The user wants routine dialogs handled without stopping the whole workflow. This is a Codex supervision procedure using native UI tools when available; the standalone Python CLI does not contain a GUI watchdog.

1. Launch live import commands with a short tool yield (about one second) so Codex retains control while the process runs. If a command remains pending after about ten seconds, inspect Zotero's current windows through the available native UI tool. Use observed dialog text and controls; never assume a dialog exists merely because the command is slow. Keep waits short enough to inspect again and provide progress within 60 seconds. Do not use voice-only screen-capture tools in a text task.
2. For a task-related informational or completion dialog, use its observed Close, OK or dismiss control when doing so only acknowledges the message. Routine dismissal is already authorized; do not ask the user again. Do not send global Escape keystrokes, click unrelated windows or infer a button's effect from its position alone.
3. For a task-related error dialog, record its title/message without secrets, then dismiss it if dismissal only acknowledges the error. Recheck the original process and resulting item/file state. Closing a dialog is not evidence that the import succeeded. Keep failed or uncertain records in remaining work and continue unaffected records or independent search, enrichment and reporting work.
4. Do not approve permission grants, credential prompts, deletion, overwrites or other consequential choices unless the existing task authorization covers that exact action. When a new decision is required, ask concisely while continuing independent work. If native UI inspection is unavailable or the dialog cannot be classified, record the UI dependency rather than waiting silently.
5. After dismissal, resume monitoring the original process. Never launch a duplicate importer while it is still running. If it has exited, reconcile using the same journal and approved input before resuming; uncertain creates still cannot be blindly repeated. If the same dialog recurs after one dismissal/recovery attempt, stop retrying that affected operation, preserve its state and continue independent work. If Zotero itself remains blocked, defer Zotero-dependent stages and complete what can proceed without it.

Record any dialog handled, its action and the verified outcome in the run report. A successful live assertion following human dismissal is assisted validation, not evidence of unattended dialog handling.

## Offline fixtures and verification

`--fixture FILE --state-dir ISOLATED_DIR` disables provider network access and uses a fixed clock, default 2026-09-11 UTC. A fixture has `account` in SearchAPI account format and `responses` entries with `params`, optional exact `url`, `data`, optional `status` and `headers`. Missing fixture requests fail closed. CLI `import --fixture` is deliberately unsupported and blocks before accessing live Zotero or credentials; import tests inject a fake transport directly. Optional `zotero` maps JSON arrays of CLI arguments to returned metadata; `downloads` maps URLs to local PDF files. Legacy adapters use `LIT_SEARCH_FIXTURE` and `LIT_SEARCH_STATE_DIR`.

Run tests with `~/anaconda3/bin/python -m pytest ~/.codex/skills/lit-search-cdx/tests -q`. Fixtures exercise public workflows and real SQLite, subprocess CLI and Poppler parsing. Live tests must respect the shared allowance and use no more than three Scholar searches.

## Provider references

Verified 2026-09-10: [SearchAPI account](https://www.searchapi.io/docs/account-api), [Scholar](https://www.searchapi.io/docs/google-scholar), [Scholar cite](https://www.searchapi.io/docs/google-scholar-cite), [OpenAlex authentication and usage](https://help.openalex.org/api/authentication/), [costs](https://help.openalex.org/access/example-costs/), and [cached full text](https://help.openalex.org/access/fulltext/). Recheck these before changing quotas or provider schemas.

Scholar author lists marked with an ellipsis are incomplete. Bundling leaves those entries unresolved until verified OpenAlex or Zotero metadata supplies the authors.
