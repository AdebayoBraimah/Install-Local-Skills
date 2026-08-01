---
name: gr-review-cdx
description: |
  Gr-style AI code review with full-repository graph context for Codex. Use when
  the user invokes gr-review-cdx, asks to review a PR, branch, or working diff
  with codebase context, wants a bug-focused review that looks beyond the diff,
  or wants a ranked GitHub PR review summary. Resolves the target, gathers
  GitNexus impact evidence, dispatches independent correctness, security,
  graph-impact, and conventions reviewers, adversarially verifies findings,
  enforces repository LEARNINGS rules, and optionally posts an authorized PR
  comment. Reviews and reports only; it does not modify product code.
---

# GR Review CDX

Review a change with repository-wide context rather than diff hunks alone. Build
a Context Pack from the GitNexus graph, run four independent review dimensions,
adversarially verify findings, enforce plain-English `LEARNINGS.md` rules, and
emit the original ranked Gr Review report.

This skill requires Codex collaboration operations matching `spawn_agent`,
`wait_agent`, `followup_task`, `send_message`, `interrupt_agent`, and
`list_agents`. If unavailable, stop and tell the user to run from a Codex session
with subagents enabled. Do not impersonate the reviewer swarm inline.

## Invocation And Arguments

```text
gr-review-cdx
gr-review-cdx 123
gr-review-cdx feature-branch
gr-review-cdx --base release feature-branch
gr-review-cdx --comment 123
```

- No target reviews the working change against the merge base, plus staged and
  unstaged changes.
- An all-digits token selects a GitHub PR.
- Any other positional token selects a branch.
- `--base` consumes the next token as the base ref.
- `--comment` authorizes one PR summary comment and is valid only with a PR.
- Whole-token matching applies. If both a PR number and branch occur, the PR wins.

## Phase 1: Preflight And Run Ownership

1. Resolve `repo_root` with `git rev-parse --show-toplevel`. Stop outside Git.
2. Resolve base as `--base` > `origin/HEAD` > `main`.
3. For a PR, require an installed and authenticated `gh`; otherwise offer the
   working-diff mode and stop.
4. Resolve this skill directory to an absolute path. Resolve LEARNINGS in order:
   `<repo>/LEARNINGS.md`, `<repo>/.gr/LEARNINGS.md`, then this skill's
   `LEARNINGS.example.md`.
5. Derive a collision-safe `run_token` from a timestamp plus lowercase hexadecimal
   entropy. It may contain only lowercase letters, digits, and underscores.
6. Create only this workspace-local tree:

```text
<repo>/.codex/gr-review/<run-token>/
  diff.patch
  target.json
  changed-files.txt
  context.md
  reviews/
  verification/
  report.md
  workers/
  run-owned-paths.json
```

Resolve and validate the exact run root before creating it. In
`run-owned-paths.json`, record the run root and every disposable worker root
before a worker receives that path. Never use shared system temporary paths,
scan broad directories for cleanup candidates, or record the repository root as
disposable.

## Phase 2: Resolve The Diff

Write target metadata to `target.json`, the unified diff to `diff.patch`, and one
repository-relative path per line to `changed-files.txt`.

- PR: use `gh pr diff <N> --patch` and `gh pr view <N> --json
  title,body,headRefName,headRefOid,baseRefName,files`; record `headRefOid` as the
  immutable target commit.
- Branch: resolve and record `git rev-parse <branch>`, then diff
  `git merge-base <base> <branch>` through that commit.
- Working target: record `git rev-parse HEAD`, then append the merge-base-to-HEAD
  diff, unstaged diff, and staged diff. Preserve uncommitted user state; run only
  read-only Git commands.

If the combined diff is empty, report “no changes to review,” clean the owned run
root, and stop. If it exceeds about 1,500 changed lines, prioritize the largest or
most impactful files and explicitly list deferred files; never silently truncate.

## Phase 3: Build The Context Pack

Determine whether the repository has a current GitNexus index with `list_repos`.
Follow `pagination.nextOffset` until the canonical repository path is matched or
`hasMore` is false. Retain the match's exact GitNexus repository identifier and
pass it as `repo` to every graph operation. Select the target's indexed branch
when available and prove that its indexed commit equals the immutable target
commit recorded in `target.json`. Repository-level dates or primary-branch commit
metadata are diagnostic only and never prove freshness for another branch. If
the repository, selected branch, or exact target commit cannot be matched, tell
the user how to index it and continue in explicit `degraded` mode for the affected
target. Otherwise use `full` mode.

Route graph questions through current GitNexus operations:

- active-checkout changed surface: `detect_changes` and `query`;
- symbol structure and intent: `context`;
- callers/dependents and public breakage: `impact` and `api_impact`;
- cross-symbol flow: `trace`;
- architectural routes and tool groupings: `route_map`, `tool_map`, or `cypher`;
- statement-level control/data evidence: `pdg_query` when available;
- persisted taint findings only: `explain`.

Do not use `explain` as a general symbol explanation operation. In degraded mode,
use `rg`, `git grep`, and direct reads of related files.

Use `detect_changes` only when the reviewed target is represented by the active
worktree or active HEAD. For the default working target, combine an appropriate
`compare` call against the base ref with `all` for staged and unstaged changes.
For a branch target, use `detect_changes` only when that branch is the active HEAD.
For a PR or a non-checked-out branch, derive changed symbols from `diff.patch` and
`changed-files.txt`, then call `query`, `context`, `impact`, `api_impact`, and
`trace` with the matching indexed `branch` when available. If that branch revision
is not indexed, label target-specific graph context degraded rather than analyzing
unrelated active-checkout changes.

Write a compact `context.md` describing, for each changed symbol, its callers,
downstream dependents, participating API or contract, relevant invariants, and
evidence source. State `Graph context: full` or `Graph context: degraded` at the
top. This is the beyond-the-diff evidence all reviewers receive.

## Phase 4: Reviewer Fan-Out

Read the resolved LEARNINGS file. Treat each applicable rule as an additional
review check, with the conventions reviewer owning full enforcement.

Use `list_agents` to observe occupied capacity. Queue these independent seats and
spawn as many as capacity permits before waiting:

| Key | Persona | Task suffix |
|---|---|---|
| `correctness` | `agents/reviewer-correctness.md` | `correctness` |
| `security` | `agents/reviewer-security.md` | `security` |
| `impact` | `agents/reviewer-impact.md` | `impact` |
| `conventions` | `agents/reviewer-conventions.md` | `conventions` |

Task names are `gr_review_<run_token>_<suffix>`. They must be unique and contain
only lowercase letters, digits, and underscores. A capacity rejection leaves the
seat pending; wait for a running GR review worker and retry. Never reuse an agent for
another dimension because that compromises independence.

Before spawning each reviewer, create and record
`workers/<task-name>/`. Give the worker only:

1. the absolute repository root, which remains read-only;
2. its absolute persona path;
3. absolute `diff.patch`, `context.md`, and LEARNINGS paths;
4. its absolute output path `reviews/<key>.json`;
5. its absolute worker scratch root;
6. this exact finding schema:

```json
{
  "file": "relative/path.py",
  "line": 42,
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "category": "reviewer-specific category",
  "title": "one-line defect statement",
  "body": "failure, impact, and evidence",
  "suggestion": "concrete fix",
  "confidence": 0.0
}
```

Require one JSON array, `[]` when clean. Require source and repository files to
remain read-only and resolve every finding path beneath the supplied repository
root. Apart from the required output file, require all generated state to stay
beneath the supplied worker root.
Track agent ID, key, and output path. Wait with `wait_agent` in bounded intervals
and provide concise progress updates. Use `send_message` only for a necessary
clarification, never to reveal another reviewer's findings. A wait timeout is not a
failure. If a worker is demonstrably stuck, request status once, then use
`interrupt_agent` only for that worker and record the missing dimension.

## Phase 5: Validate, Correct, And Deduplicate

For each completed seat, require a non-empty file, parse it as a JSON array, and
validate every object:

- all eight fields exist;
- `file`, `category`, `title`, `body`, and `suggestion` are strings;
- `line` is a positive integer;
- severity is `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW` (conventions only permits
  `MEDIUM` or `LOW`);
- confidence is a number from 0 through 1;
- category matches the persona contract.

On malformed or missing output, call `followup_task` once on the same agent with
the exact error and require correction at the same path. After one failed
correction, record that dimension as missing. Continue if at least one reviewer
succeeded; if all fail, interrupt only this run's active agents, clean owned state,
and stop without fabricating findings.

Merge valid arrays. Deduplicate by `(file, line, category)`, retain the
highest-severity instance, and annotate corroboration without changing the finding
schema used for verification. Use stable IDs `F-001`, `F-002`, and so on after
ranking by severity and confidence.

## Phase 6: Adversarial Verification

LOW findings skip verification and remain clearly marked as unverified. Queue each
MEDIUM-or-higher finding for an independent verifier. Use task names such as
`gr_review_<run_token>_verify_f_001`, with a fresh agent per finding; use
capacity-limited waves when they cannot all run at once. Never reuse the originating
reviewer.

Give each verifier only the absolute read-only repository root, its absolute
`agents/verifier.md` persona path, one finding, the absolute diff and Context Pack
paths, an absolute unique output path `verification/F-001.json`, and a recorded
unique worker root. Require it to resolve finding paths beneath the supplied
repository root and return:

```json
{ "verdict": "real|refuted|uncertain", "reason": "one or two evidence sentences" }
```

Launch at maximum available concurrency in capacity-limited waves. Validate that
the object contains only a permitted verdict and a non-empty reason. Use one
`followup_task` correction for malformed or missing output. A verifier failure
leaves the finding `uncertain`; it does not silently delete it.

Apply results exactly:

- `real`: keep the finding at its original severity;
- `refuted`: drop it from the main report and note it as refuted;
- `uncertain`: keep it, cap severity at MEDIUM, and label it `[unverified]`;
- LOW or verifier failure: keep it clearly labeled `[unverified]`.

## Phase 7: Report

Rank surviving findings by severity, then confidence. Write the authoritative
report to `report.md` using this unchanged structure:

```markdown
## Gr Review — <target>

**<n> findings** · <c> critical · <h> high · <m> medium · <l> low
Graph context: <full | degraded> · Rules: <LEARNINGS source>

### 🔴 CRITICAL / 🟠 HIGH
- **`path/to/file.py:42` — <title>** (<category>, confidence <x>)
  <body, including caller/dependent evidence when relevant>
  _Suggestion:_ <concrete fix>

### 🟡 MEDIUM / ⚪ LOW
...

### Notes
- <degraded-mode caveats, deferred files, missing dimensions, unverified or
  refuted findings, and rules applied>
```

Present the report in the conversation. A clean review is a valid outcome. Disclose
missing review dimensions and verification failures as reduced confidence.

If and only if `--comment` was explicit and the target is a PR, run
`gh pr comment <N> --body-file <absolute-report-path>`. Confirm the returned URL.
If posting fails, retain and return the local report and disclose the posting error;
do not fail or discard the review. Do not create inline comments unless separately
requested and authorized.

## Phase 8: Cleanup

Cleanup runs after success, partial failure, or error.

1. Use `list_agents` and identify agents by this run's exact task-name prefix.
2. Interrupt only those still active after their work is no longer needed.
3. Read `run-owned-paths.json`. Remove generated state only when its resolved path
   is beneath the validated run root recorded there.
4. Preserve the report when it is the user-facing deliverable. Remove worker roots,
   reviewer intermediates, verification intermediates, and other disposable state.
5. If keeping `report.md`, leave the minimal run directory and disclose its path;
   otherwise remove the exact run root. Never recursively target the repository
   root, a home directory, an unresolved variable, or a path discovered by scanning.
6. Leave uncertain targets untouched and disclose cleanup failures.

## Scope Guardrails

- Review and report only; never modify product code.
- Do not create persistent state outside the collision-safe run root.
- Read but never auto-edit repository LEARNINGS rules.
- Degrade graph context explicitly and lower confidence accordingly.
- Never silently truncate a large diff.
- Never post externally without explicit `--comment` authorization on a PR.
