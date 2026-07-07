---
name: gr-review-clc
description: |
  Gr-style AI code review with full-repo graph context. Use when the user
  invokes /gr-review-clc, asks to review a PR or diff "with codebase context",
  wants a bug-focused review that looks "beyond the diff", or wants inline/summary
  review comments on a GitHub PR. Resolves a review target (PR number, branch, or
  the working diff), pulls cross-file impact from the gitnexus knowledge graph,
  dispatches a parallel swarm of dimension reviewers (correctness, security,
  graph-impact, conventions), verifies each finding adversarially, applies
  repo-specific LEARNINGS rules, and emits a ranked report — optionally posting it
  to the PR.
version: 0.1.0
---

# Gr Review

A local, skills-native reimplementation of Gr's hero feature: an AI code
review that reads a change **with full knowledge of the surrounding codebase**,
not just the diff hunks. It builds cross-file context from the gitnexus graph,
runs a parallel reviewer swarm, verifies findings before reporting them, and
enforces plain-English team rules from a `LEARNINGS.md` file.

This skill reviews and reports. It does **not** modify product code.

## Invocation

- `/gr-review-clc` — review the current working diff against the merge-base
  (`git diff $(git merge-base HEAD <base>)...HEAD`, plus staged + unstaged).
- `/gr-review-clc 123` — review GitHub PR #123 (fetched via `gh`).
- `/gr-review-clc <branch>` — review `<branch>` vs the base branch.
- `/gr-review-clc --comment [target]` — after reviewing, post the report to the
  PR as a summary comment (`gh pr comment`). Requires a PR target.
- `/gr-review-clc --base <ref> [target]` — override the base branch (default:
  the repo's default branch, else `main`).

### Argument tokenizer

Each argument is exactly one of:

- `--comment` → set `post=true` (only valid with a PR target).
- `--base` → the **next** token is the base ref.
- an all-digits token → the PR number (`target_kind=pr`).
- any other token → a branch name (`target_kind=branch`).

Whole-token matching. If both a PR number and a branch are given, the PR wins.

## Step 0 — Preflight

Run this Bash preflight and record the results:

```bash
# Repo + base branch
repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "NOT_A_GIT_REPO"; exit 0; }
default_base="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')"
[ -z "$default_base" ] && default_base="main"
# Tooling availability
command -v gh >/dev/null 2>&1 && echo "GH_OK" || echo "GH_MISSING"
# Learnings file (repo-local rules override the bundled example)
[ -f "$repo_root/LEARNINGS.md" ] && echo "LEARNINGS_REPO" \
  || ([ -f "$repo_root/.gr/LEARNINGS.md" ] && echo "LEARNINGS_DOT" || echo "LEARNINGS_NONE")
```

- If `NOT_A_GIT_REPO`: stop and tell the user this skill needs a git repository.
- If a PR target was requested but `GH_MISSING`: stop and ask them to install/auth
  `gh`, or re-run against the working diff.
- Resolve the base: `--base` argument > `origin/HEAD` > `main`.

## Step 1 — Resolve the diff

Produce two artifacts in the scratchpad: the **diff** and the **changed-file list**.

```bash
# PR target
gh pr diff <N> --patch > /tmp/gr-diff.patch
gh pr view <N> --json title,body,headRefName,baseRefName,files > /tmp/gr-pr.json

# Branch target
git diff "$(git merge-base <base> <branch>)".."<branch>" > /tmp/gr-diff.patch

# Working-diff target (default)
base_sha="$(git merge-base HEAD <base>)"
git diff "$base_sha"...HEAD > /tmp/gr-diff.patch
git diff >> /tmp/gr-diff.patch          # unstaged
git diff --cached >> /tmp/gr-diff.patch # staged
```

Extract the changed-file list (`git diff --name-only` equivalent, or the `files`
field of the PR JSON). If the diff is empty, report "no changes to review" and stop.

**Guardrail:** if the diff exceeds ~1500 changed lines, tell the user you'll review
the largest/most-impactful files first and name what you're deferring — never
silently truncate.

## Step 2 — Build graph context (the "beyond the diff" step)

This is what separates this skill from a plain diff review. For the changed files
and symbols, pull cross-file context from the **gitnexus** knowledge graph.

1. Confirm the repo is indexed:
   - Call `mcp__gitnexus__list_repos`. If this repo is absent or stale, tell the
     user to index it (the `gitnexus-cli` skill / `Index this repo`) and offer to
     proceed in **degraded mode** (graph tools unavailable → context comes only
     from `git grep` + reading files).
2. For the changed surface, gather context with whichever tools are available:
   - `mcp__gitnexus__detect_changes` — what the graph thinks changed.
   - `mcp__gitnexus__impact` / `mcp__gitnexus__api_impact` — **callers and
     downstream dependents** of each changed function/class/endpoint. This is the
     core signal: a change is only safe in the context of what depends on it.
   - `mcp__gitnexus__context` / `mcp__gitnexus__explain` — surrounding structure
     and intent of the changed code.
   - `mcp__gitnexus__trace` — data/control flow through changed code when a finding
     needs it.
3. Write a compact **Context Pack** to `/tmp/gr-context.md`: for each changed
   symbol, its callers, its dependents, the API/contract it participates in, and any
   invariant the graph reveals. Reviewers read this so their findings account for
   the whole repo, not just the hunk.

Degraded mode (no gitnexus): build the Context Pack from `git grep` of changed
symbol names + reading the immediately-related files. Note in the final report that
graph context was unavailable so impact findings are lower-confidence.

## Step 3 — Load LEARNINGS (repo-specific rules)

Resolve the rules file from the preflight:

- `LEARNINGS_REPO` → `$repo_root/LEARNINGS.md`
- `LEARNINGS_DOT` → `$repo_root/.gr/LEARNINGS.md`
- `LEARNINGS_NONE` → fall back to the bundled `LEARNINGS.example.md` in this skill
  directory (resolve `${HOME}/.claude/skills/gr-review-clc/LEARNINGS.example.md`
  to an absolute path first; the Read tool does not expand `${HOME}`).

Read it and treat every rule as an additional review dimension the conventions
reviewer must enforce. This is Gr's "write standards in plain English" surface.

## Step 4 — Dispatch the reviewer swarm

Pre-resolve the agents directory once (the Read tool inside a subagent does **not**
expand `${HOME}`/`~` — pass an absolute path):

```bash
agent_dir="${HOME}/.claude/skills/gr-review-clc/agents"
echo "$agent_dir"
```

Spawn all four reviewers **in a single message** (four Agent tool calls) so they run
in parallel. Each reviewer receives the same three inputs: the diff
(`/tmp/gr-diff.patch`), the Context Pack (`/tmp/gr-context.md`), and the
resolved LEARNINGS path. Each writes findings as a JSON array to its own output file.

For each reviewer `<dim>` in `correctness`, `security`, `impact`, `conventions`:

```
Agent({
  description: "gr <dim> review",
  prompt: "You are the <dim> reviewer. Read your instructions at
    <agent_dir>/reviewer-<dim>.md and follow them exactly. Inputs:
    diff=/tmp/gr-diff.patch, context=/tmp/gr-context.md,
    learnings=<resolved LEARNINGS path>. Write your findings as a JSON array to
    /tmp/gr-findings-<dim>.json using the schema in your instructions.",
  mode: "auto"
})
```

Each finding object: `{file, line, severity (CRITICAL|HIGH|MEDIUM|LOW), category,
title, body, suggestion, confidence (0-1)}`.

**Optional ultra mode:** if the user explicitly opted into multi-agent orchestration
(said "use a workflow"/"ultra"), this whole swarm+verify pipeline is a natural
`Workflow` (pipeline: review dimension → verify each finding as it lands). Do **not**
reach for `Workflow` otherwise — the Agent dispatch above is the default.

## Step 5 — Verify findings (adversarial pass)

Merge the four JSON files. **Deduplicate** by `(file, line, category)` — the same
issue often surfaces from two reviewers; keep the highest-severity instance and note
the corroboration.

For each surviving finding at MEDIUM+ severity, spawn a verifier
(`<agent_dir>/verifier.md`) whose job is to **refute** it. Batch these in parallel.
The verifier returns `{verdict: real|refuted|uncertain, reason}`.

- Drop findings the verifier refutes.
- Keep `uncertain` findings but cap their severity at MEDIUM and label them
  `[unverified]`.
- LOW findings skip verification (cheap, low stakes) but are clearly marked.

This mirrors Gr's runtime-validation instinct: don't report a bug you couldn't
stand behind. (A future `gr-verify` skill would replace refutation-by-reasoning
with actually generating and running a test — the TREX analogue.)

## Step 6 — Synthesize the report

Rank surviving findings by severity, then confidence. Write `/tmp/gr-report.md`:

```markdown
## Gr Review — <target>

**<n> findings** · <c> critical · <h> high · <m> medium · <l> low
Graph context: <full | degraded> · Rules: <LEARNINGS source>

### 🔴 CRITICAL / 🟠 HIGH
- **`path/to/file.py:42` — <title>** (<category>, confidence <x>)
  <body — what's wrong and why it matters, referencing the caller/dependent from
  the Context Pack when relevant>
  _Suggestion:_ <concrete fix>

### 🟡 MEDIUM / ⚪ LOW
...

### Notes
- <degraded-mode caveats, deferred files, rules applied>
```

Present the report in the conversation. If **no** findings survive, say so plainly —
a clean review is a valid result, not a failure.

## Step 7 — Post (only with `--comment`)

Only if `post=true` and the target is a PR:

```bash
gh pr comment <N> --body-file /tmp/gr-report.md
```

Confirm the URL back to the user. Inline per-line comments via `gh api
.../pulls/<N>/comments` (needs `commit_id` + `path` + `line`) are a documented
stretch — do not attempt them in this MVP unless the user asks.

## Step 8 — Cleanup

```bash
rm -f /tmp/gr-diff.patch /tmp/gr-pr.json /tmp/gr-context.md \
      /tmp/gr-report.md /tmp/gr-findings-*.json
```

## Scope guardrails

- Reviews and reports only — never edits product code.
- No persistent state across invocations (learnings live in the repo's
  `LEARNINGS.md`, which the user maintains — this MVP reads rules, it does not yet
  auto-mine them from past comments; that is the future `gr-learnings` skill).
- Graph context degrades gracefully; the report always states which mode ran.
- Never silently truncate a large diff — name what was deferred.
```
