---
name: gr-learnings-clc
description: |
  Gr-style "learnings" miner. Use when the user invokes /gr-learnings-clc,
  wants to auto-generate or refresh a repo's review rules, asks to "learn our
  standards from past PRs", or wants to seed/update the LEARNINGS.md that
  gr-review-clc enforces. Harvests historical PR review comments via gh, clusters
  the recurring, normative ones into plain-English rules with provenance, and
  merges them into LEARNINGS.md without clobbering hand-written rules.
version: 0.1.0
---

# GR Learnings — Mine Team Rules from Past Reviews

Gr "reads other engineers' comments to understand your coding standards." This
skill does the same locally: it harvests past pull-request review comments, distills
the **recurring, normative** ones into plain-English rules, and writes them into the
repo's `LEARNINGS.md` — the file `gr-review-clc` enforces on every future review.

This skill only writes to `LEARNINGS.md` (or a dry-run report). It never touches
product code.

## Invocation

- `/gr-learnings-clc` — mine and update `LEARNINGS.md` (shows a diff, then writes).
- `/gr-learnings-clc --dry-run` — propose rules only; write nothing.
- `/gr-learnings-clc --since <N|date>` — limit to the last `N` merged PRs or PRs
  since a date (default: last 100 merged PRs).
- `/gr-learnings-clc --min-occurrences <k>` — a candidate rule needs `k` supporting
  comments to be included (default: 2).

### Argument tokenizer
`--dry-run` → propose only. `--since` / `--min-occurrences` → the next token is the
value. Bare number after `--since` = PR count; anything date-shaped = date.

## Step 0 — Preflight

```bash
repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "NOT_A_GIT_REPO"; exit 0; }
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && echo "GH_OK" || echo "GH_UNAVAILABLE"
slug="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)"; echo "SLUG=${slug:-none}"
[ -f "$repo_root/LEARNINGS.md" ] && echo "LEARNINGS_ROOT" \
  || ([ -f "$repo_root/.gr/LEARNINGS.md" ] && echo "LEARNINGS_DOT" || echo "LEARNINGS_NONE")
```

- `NOT_A_GIT_REPO`: stop.
- `GH_UNAVAILABLE`: the primary signal is GitHub review comments. Tell the user to
  install/authenticate `gh`. Offer the **local fallback** (Step 1b) which mines
  signals from the repo itself instead — weaker, but works offline.
- Record the existing `LEARNINGS.md` path (or that there is none → we will create one
  at `$repo_root/LEARNINGS.md`).

## Step 1a — Harvest review comments (primary, needs gh)

Pull the corpus of human review comments. These are the standards, stated in situ.

```bash
# Inline (diff-anchored) review comments across recent PRs
gh api --paginate "repos/$slug/pulls/comments?per_page=100" \
  --jq '.[] | {pr:.pull_request_url, path:.path, line:.line, user:.user.login, body:.body, url:.html_url}' \
  > /tmp/gr-learn-review-comments.jsonl
# PR-level conversation comments (often contain "please always…"/"we don't do…")
for n in $(gh pr list --state merged --limit <SINCE_N> --json number -q '.[].number'); do
  gh api "repos/$slug/issues/$n/comments" \
    --jq ".[] | {pr:$n, user:.user.login, body:.body, url:.html_url}" 2>/dev/null
done > /tmp/gr-learn-pr-comments.jsonl
```

Filter out noise before clustering: drop bot authors, pure approvals ("LGTM", "👍"),
questions, and one-off comments tied to a single line with no general phrasing.

## Step 1b — Local fallback (no gh)

When `gh` is unavailable, mine weaker proxies for team standards from the repo:
- Existing linter/formatter/config (`.eslintrc`, `ruff.toml`, `.editorconfig`,
  `CONTRIBUTING.md`, `CODEOWNERS`, `pre-commit` config) — codified rules already.
- `git log` commit messages matching corrective patterns (`fix: `, "revert",
  "don't", "should not", "always").
- Read `CONTRIBUTING.md` / existing `LEARNINGS.md` for stated conventions.

Label everything derived this way as lower-confidence in the provenance.

## Step 2 — Cluster into candidate rules

Distill the corpus into recurring, actionable standards. For a corpus above a few
dozen comments, dispatch a miner subagent (`<agent_dir>/miner.md`, resolve
`${HOME}/.claude/skills/gr-learnings-clc/agents` to an absolute path first) with the
harvested JSONL; otherwise cluster inline. The miner returns candidate rules as JSON:

```json
{
  "rule": "imperative one-sentence standard a reviewer can check against a diff",
  "group": "correctness|security|style|testing|architecture",
  "occurrences": 3,
  "evidence": ["<comment html_url>", "..."],
  "confidence": 0.0
}
```

Keep a candidate only if it is **normative** (a standard, not a one-off fix) **and**
recurs at least `--min-occurrences` times, or is a single but unambiguous policy
statement ("never commit secrets"). Merge near-duplicates. Discard taste-only nits
with no recurrence.

## Step 3 — Reconcile with existing LEARNINGS.md

Read the current `LEARNINGS.md` (or the bundled example from `gr-review-clc` as a
template if none exists). Then:
- **Never delete or rewrite hand-written rules.** They are authoritative.
- Drop candidates already covered by an existing rule (semantic dedupe).
- Keep the file's structure/grouping; append new rules under the right group.
- Attach provenance to each new rule as an HTML comment so it is auditable but
  doesn't clutter the prose:

```markdown
- Never build a shell command by concatenating user input; use an argument array.
  <!-- gr-learnings: 4 occurrences · https://github.com/…/pull/12#discussion_r… -->
```

## Step 4 — Present and write

Show the user a **diff**: rules to be added (with occurrence counts + example links)
and any candidates you rejected and why (so the mining is transparent, not a black
box).

- `--dry-run`: stop here; write nothing. Save the proposal to
  `/tmp/gr-learnings-proposal.md` and report its path.
- Otherwise: write the merged `LEARNINGS.md` to `$repo_root/LEARNINGS.md` (create it
  if absent). Tell the user it now feeds `gr-review-clc` automatically, and that they
  should edit/prune rules they disagree with — the file is theirs to own.

## Step 5 — Cleanup

```bash
rm -f /tmp/gr-learn-review-comments.jsonl /tmp/gr-learn-pr-comments.jsonl \
      /tmp/gr-learnings-proposal.md
```
(Keep the proposal file if `--dry-run` and the user may still want it.)

## Scope guardrails

- Writes only `LEARNINGS.md` (or a dry-run proposal). Never edits product code.
- Never overwrites or deletes human-authored rules — only appends and dedupes.
- Every mined rule is auditable: occurrence count + source comment links.
- Recurrence-gated: a single stray comment does not become a team standard.
