---
name: gr-learnings-cdx
description: |
  Codex-native Gr-style learnings miner. Use when the user invokes
  gr-learnings-cdx, wants to generate or refresh repository review rules, asks
  to learn team standards from past pull requests, or wants to seed or update
  the LEARNINGS.md that gr-review-cdx enforces. Harvests historical human review
  comments with gh, extracts recurring normative rules with provenance, and
  merges them without clobbering hand-written rules. Supports dry runs and a
  lower-confidence local fallback when GitHub is unavailable.
---

# GR Learnings CDX — Mine Team Rules from Past Reviews

Mine past pull-request review comments for **recurring, normative** standards,
turn those standards into checkable plain-English rules, and reconcile them
with the repository's `LEARNINGS.md`. That file feeds future `gr-review-cdx`
reviews.

The authoritative write boundary is narrow: update only the selected
`LEARNINGS.md`, or produce only a proposal in dry-run mode. Workspace-local run
files are disposable operational state and must stay beneath the owned run root.
Never edit product code.

## Invocation

```text
gr-learnings-cdx
gr-learnings-cdx --dry-run
gr-learnings-cdx --since <N|date>
gr-learnings-cdx --min-occurrences <k>
```

- `--dry-run` proposes rules without modifying `LEARNINGS.md`.
- `--since` accepts either a count of recent merged PRs or a date. The default
  is the last 100 merged PRs.
- `--min-occurrences` sets the recurring-comment threshold. The default is 2.

Tokenize arguments exactly: `--dry-run` is a flag; `--since` and
`--min-occurrences` consume the next token. A bare integer supplied to
`--since` is a PR count; date-shaped input is a date. Reject a missing value,
non-positive count, or non-positive occurrence threshold before mining.

## Phase 0: Preflight And Owned State

Resolve the repository without changing it:

```bash
git rev-parse --show-toplevel
git status --short
command -v gh
gh auth status
gh repo view --json nameWithOwner -q .nameWithOwner
```

Stop if the current directory is not in a Git repository. If `gh` is absent,
unauthenticated, or cannot resolve the repository slug, explain that GitHub
review comments are the primary signal and offer the local fallback in Phase
1b. The fallback is weaker but works offline.

Select an existing learnings file in this order:

1. `<repo-root>/LEARNINGS.md`
2. `<repo-root>/.gr/LEARNINGS.md`
3. otherwise, the new target is `<repo-root>/LEARNINGS.md`

Never silently move an existing `.gr/LEARNINGS.md` to the root. Record the
chosen path before reconciliation.

Create a unique legal `run_token` from a timestamp plus lowercase hexadecimal
entropy, using only lowercase letters, digits, and underscores. Create this
exact workspace-local layout:

```text
<repo-root>/.codex/gr-learnings/<run-token>/
  review-comments.jsonl
  pr-comments.jsonl
  candidates.json
  proposal.md
  workers/miner/
  run-owned-paths.json
```

Resolve the run root to an absolute path. Before launching a worker, write
`run-owned-paths.json` with every disposable path this run owns. The run root
and `workers/miner/` are cleanup boundaries; never infer cleanup targets by
scanning the workspace, home directory, or a system temporary directory.

## Phase 1a: Harvest GitHub Review Comments

When authenticated `gh` access is available, first select merged PR numbers:

- integer `--since N`: the newest `N` merged PRs;
- date `--since DATE`: merged PRs whose `mergedAt` is on or after that date;
- default: the newest 100 merged PRs.

For each selected PR, collect both human signal sources:

```text
repos/<slug>/pulls/<number>/comments
repos/<slug>/issues/<number>/comments
```

Normalize inline comments into JSONL objects shaped as:

```json
{"pr": 42, "path": "src/example.ts", "line": 18, "user": "reviewer", "body": "...", "url": "https://..."}
```

Normalize PR conversation comments to the same shape with `path` and `line`
omitted. Write them respectively to the run-local `review-comments.jsonl` and
`pr-comments.jsonl`. Do not use shared filenames or `/tmp`.

Filter obvious noise before clustering: bot authors, pure approvals such as
`LGTM` or a thumbs-up, praise without a standard, questions, and one-off
line-specific corrections with no general normative language. Preserve source
URLs for every surviving comment.

## Phase 1b: Local Fallback

When GitHub harvesting is unavailable and the user accepts the fallback, mine
weaker repository-local signals:

- linter, formatter, and hook configuration such as `.editorconfig`, ESLint,
  Ruff, and pre-commit files;
- `CONTRIBUTING.md`, `CODEOWNERS`, and the existing `LEARNINGS.md`;
- commit messages expressing corrective patterns such as `fix`, `revert`,
  `don't`, `should not`, or `always`.

Do not claim that these proxies are PR-review recurrence. Give every locally
derived candidate provenance identifying its file or commit and label it
lower-confidence in the proposal. Apply the same normative, checkable-rule
test. Existing explicit policy may qualify on its own; a commit-message pattern
must meet the requested recurrence threshold.

## Phase 2: Mine Candidate Rules

Resolve this skill's own directory and the absolute miner persona path
`agents/miner.md` before dispatch. Combine the harvested GitHub JSONL sources
into one corpus reference without writing outside the run root.

For a corpus above 40 comments, use a fresh Codex subagent. Confirm native
`spawn_agent`, `wait_agent`, `followup_task`, `send_message`, `interrupt_agent`,
and `list_agents` operations are available. If they are not available, or the
corpus has 40 or fewer comments, perform the same mining method inline.

For subagent mining, use the unique legal task name:

```text
gr_learnings_<run_token>_miner
```

Give the miner only:

1. the absolute `agents/miner.md` path;
2. the absolute corpus paths and their source type;
3. the `--min-occurrences` threshold;
4. the absolute `workers/miner/` owned scratch root;
5. the absolute output path `candidates.json`;
6. the candidate JSON schema below.

Require it to read and follow the persona, treat repository inputs as read-only,
write all generated state beneath its supplied worker root, and return only a
short completion status after writing the output. Use `wait_agent` in bounded
intervals rather than shell polling. Never reuse an agent from another task.

Each candidate has this schema:

```json
{
  "rule": "imperative one-sentence standard a reviewer can check against a diff",
  "group": "correctness|security|style|testing|architecture",
  "occurrences": 3,
  "evidence": ["<comment URL or local provenance>", "..."],
  "confidence": 0.0
}
```

Validate `candidates.json` as one JSON array. Every element requires a non-empty
`rule`, an allowed `group`, an integer `occurrences` greater than zero, a
non-empty string array `evidence`, and numeric `confidence` between 0 and 1.
Also enforce the configured occurrence threshold except for a single explicit,
unambiguous policy such as “never commit secrets.”

If a completed miner omits or malforms its output, call `followup_task` once
with the exact validation error and require correction at the same output path.
If that correction fails—or if the miner otherwise fails—record the failure and
run the same sound clustering method inline from the source corpus. Never treat
an invalid partial file as valid evidence.

Whether mined by a worker or inline:

- retain standards, not one-off fixes;
- merge semantic near-duplicates;
- discard non-recurring taste-only nits;
- require each rule to be actionable and checkable against a diff;
- keep a single occurrence only for an unambiguous policy statement;
- preserve occurrence counts and real provenance;
- prefer a small set of high-confidence rules over a long weak list.

## Phase 3: Reconcile With Existing Learnings

Read the selected `LEARNINGS.md`, if present. If none exists, create a minimal
grouped document suitable for `gr-review-cdx`; do not depend on another skill's
installation to obtain a template.

Reconcile conservatively:

- Human-authored rules are authoritative: never delete, rewrite, reorder, or
  weaken them.
- Drop candidates already covered semantically by an existing rule.
- Preserve the file's current headings and grouping.
- Append each accepted rule under the best matching existing group, adding a
  group heading only when required.
- Attach auditable provenance as an HTML comment immediately beneath each new
  rule.

For GitHub-derived rules, use:

```markdown
- Never build a shell command by concatenating user input; use an argument array.
  <!-- gr-learnings: 4 occurrences · https://github.com/... -->
```

For fallback rules, identify the local source and confidence explicitly in the
comment. Never fabricate a URL or occurrence count.

## Phase 4: Present And Write

Write `proposal.md` inside the run root before making an authoritative change.
It must show:

- the exact target `LEARNINGS.md` path;
- the proposed diff;
- each accepted rule with occurrences, confidence, and example provenance;
- rejected candidates and the reason for rejection;
- whether GitHub or lower-confidence local fallback signals were used;
- any miner failure followed by inline fallback.

Present this diff to the user before applying the update.

- In `--dry-run`, do not modify or create `LEARNINGS.md`. Preserve
  `proposal.md`, report its absolute path, and stop after cleanup of the other
  disposable run files.
- Otherwise, apply exactly the proposed append-only reconciliation to the
  selected path. If the target did not exist, create only that file. Re-read it
  to confirm all previous content remains byte-for-byte in order and each new
  rule has provenance. Report that it now feeds `gr-review-cdx`, while making
  clear that the repository owners should edit or prune mined rules they reject.

Do not write the update until the diff has been shown. A normal invocation may
then apply that displayed diff; `--dry-run` always stops without an
authoritative write.

## Phase 5: Cleanup

Cleanup runs after success, dry run, partial failure, and error.

1. Use `list_agents` to identify only the miner for this run. Interrupt it only
   if it remains active after its output is no longer needed.
2. Read and validate `run-owned-paths.json`.
3. Remove only paths whose resolved locations are descendants of the recorded
   absolute run root. Leave uncertain paths untouched and disclose them.
4. For a normal update, remove the validated run root after the proposal is no
   longer needed.
5. For a dry run, preserve `proposal.md` and its parent directories; remove the
   corpus, candidates, worker scratch, and other disposable children
   individually.

Never target the repository root, home directory, an unresolved variable, or a
broad directory with recursive deletion.

## Invariants

- Authoritative writes are limited to the selected `LEARNINGS.md`; dry runs
  never modify it.
- Product code is read-only.
- Hand-written rules are never overwritten or deleted.
- Every mined rule has actual provenance and an honest occurrence count.
- Recurrence gates ordinary comments; one stray opinion does not become policy.
- Local fallback evidence is clearly distinguished and lower-confidence.
- Operational state stays under the unique, manifest-owned run root.
