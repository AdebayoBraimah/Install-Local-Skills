---
name: orchestrator-cdx
description: |
  Codex phase pipeline over GSD. Use with `orchestrator-cdx <mode> <phase>`
  to plan, review, execute, verify, and review a single GSD phase with durable
  terminal-state artifacts.
version: 0.1.0
---

# Orchestrator CDX

Drive one existing GSD phase through planning, plan review, execution,
verification, post-execution review, handoff, and notification gates. This skill
is a policy layer over GSD, `plan-review-cdx`, `deep-review`, and optional
notification or issue-creation skills.

Every invocation must end by running the terminal handler exactly once, including
usage errors, dependency errors, checkpoints, gate failures, and successful runs.

## Invocation

Accept exactly this grammar:

```text
orchestrator-cdx <mode> <phase>
```

Both tokens are required. Valid modes:

- `plan`: prerequisites, Stage 1, Stage 2, terminal handler.
- `full`: prerequisites, Stages 1, 2, 4, 5, 6, terminal handler.
- `verify`: prerequisites, Stages 5, 6, terminal handler.

Invalid token count or invalid mode is terminal state `error:usage`. The usage
message must show the grammar above and list `plan`, `full`, and `verify`.

Successful terminal states:

- `plan`: after Stage 2 convergence, record terminal state `done`.
- `full`: use the terminal state selected by Stage 6.
- `verify`: use the terminal state selected by Stage 6.

## Phase Resolution

Resolve `PHASE_DIR` under `.planning/phases/`.

1. Exact directory-name match wins.
2. If no exact match exists, use a unique prefix match.
3. Zero matches is terminal state `error:phase-not-found`.
4. More than one prefix match is terminal state `error:phase-ambiguous`; list
   the matching directory names in the terminal message.

Never create a phase directory. Phase creation remains owned by GSD.

## Prerequisites

Run all required dependency checks before any stage mutates artifacts. If a
required dependency is missing, set terminal state
`error:missing-dependency:<name>` and run the terminal handler.

Required dependencies:

- GSD command skill `gsd:plan-phase`.
- GSD command skill `gsd:execute-phase`.
- GSD command skill `gsd:verify-work`.
- GSD worker skill `gsd-executor`.
- GSD worker skill `gsd-verifier`.
- `plan-review-cdx`.
- `plan-review-cdx` reviewer file
  `${HOME}/.agents/skills/plan-review-cdx/agents/plan-reviewer-spec.md`.
- `plan-review-cdx` reviewer file
  `${HOME}/.agents/skills/plan-review-cdx/agents/plan-reviewer-exec.md`.
- `deep-review`.
- Codex worker capability for any mode that needs Stage 2 or Stage 6.

Codex worker capability is available only when the runtime exposes worker start
and wait primitives. Use `spawn_agent` as the worker start primitive and
`wait_agent` as the worker wait primitive. If the runtime exposes different
names, define a tiny adapter with these two names before any stage starts. If
neither native primitives nor an adapter is available, stop during prerequisites
with terminal state `error:subagents-unavailable`.

Optional dependencies:

- `ntfy-notify`: fail soft. If the send script cannot be found, skip
  notification without changing the terminal state.
- `handoff`: if unavailable, write the built-in handoff fallback described in
  the terminal handler.
- `security-review`: if unavailable, use the built-in security checklist in
  Stage 6.
- `to-issues`: if unavailable, write `FOLLOWUPS.md` in Stage 6 when follow-up
  creation is selected.

### Verify Mode Entry Checks

Mode `verify` is allowed only when all of these are true:

- `$PHASE_DIR/START-SHA` exists and is non-empty.
- `$PHASE_DIR/END-SHA` exists and is non-empty.
- `$PHASE_DIR/.stage4-complete` exists.
- `git rev-parse HEAD` equals the value in `END-SHA`.

Failure is terminal state `error:verify-precondition-failed`; name the failed
condition in the message.

## Worker Contract

Stage 2 and Stage 6 must use the same worker ordering.

1. Start every independent worker for the round before waiting for any worker.
2. Record every returned worker handle in the stage transcript or sentinel before
   the first wait.
3. Pass the complete handle set to `wait_agent`.
4. Give each worker a fresh prompt, its own input artifact, and its own output
   artifact.
5. Do not give paired reviewers each other's output until both have returned.
6. Wait for all workers in the batch.
7. Treat a missing worker result, timeout, or malformed status as the terminal
   error named by the stage.

Stage 2 uses exactly two reviewer workers per round: one spec reviewer and one
execution reviewer. Stage 6 uses exactly two review workers per run: one quality
reviewer and one security reviewer or security-checklist fallback worker.

## Stage 1: Plan

Purpose: establish the starting commit and require a single GSD plan artifact.

Rules:

- If `.stage1-complete` exists, validate its `start_sha` against `START-SHA` and
  its `phase_plan_sha256` against `phase-plan.md`, then skip Stage 1.
- If `START-SHA` exists but `.stage1-complete` is missing, stop with terminal
  state `error:partial-stage1-state`.
- Never overwrite an existing `START-SHA`.
- Forced replan requires the user to delete `START-SHA`, `.stage1-complete`,
  every `.stage2-*` sentinel, and `phase-plan-REVIEW.md`.
- Capture the starting commit with `git rev-parse HEAD` and write it to
  `$PHASE_DIR/START-SHA`.
- Follow `gsd:plan-phase` for the requested phase.
- Require `$PHASE_DIR/phase-plan.md` to exist and be non-empty after GSD
  planning. Missing or empty artifact is terminal state
  `error:missing-phase-plan`.
- Compute the SHA-256 of `phase-plan.md`.
- Write `$PHASE_DIR/.stage1-complete` atomically:

```text
start_sha=<40-hex git sha>
phase_plan_sha256=<64-hex sha256>
```

Stage 1 owns only `START-SHA`, the GSD-emitted `phase-plan.md`, and
`.stage1-complete`.

## Stage 2: Plan-Review Gate

Purpose: review and correct `phase-plan.md` before any execution starts, using
`plan-review-cdx` as the normative review contract.

Rules:

- Be compatible with `plan-review-cdx` default parallel mode.
- Use the `plan-review-cdx` reviewer files, delimiter format, reviewer
  independence rules, and correction rules.
- You may inline the steps below to preserve durable sentinels, but do not
  invent a different review algorithm.
- Never execute the plan during Stage 2.
- Source file is exactly `$PHASE_DIR/phase-plan.md`.
- Working candidate is exactly `$PHASE_DIR/.stage2-working-plan.md`.
- Review history file is exactly `$PHASE_DIR/phase-plan-REVIEW.md`.
- Required clean review streak is exactly two consecutive clean rounds.
- Maximum review rounds before cap-hit is five.
- Create the per-run temp directory with:

```bash
mktemp -d "${TMPDIR:-/tmp}/orchestrator-cdx-stage2.XXXXXX"
```

### Stage 2 Resume Rules

- At Stage 2 start, copy `phase-plan.md` to `.stage2-working-plan.md` if no
  working candidate exists.
- Write `$PHASE_DIR/.stage2-in-progress` atomically before launching reviewers:

```text
original_source_sha256=<sha256 of phase-plan.md at Stage 2 start>
current_candidate_sha256=<sha256 of .stage2-working-plan.md>
current_candidate_path=$PHASE_DIR/.stage2-working-plan.md
round=<current round number>
clean_round_streak=<0|1|2>
required_clean_rounds=2
review_copy=$PHASE_DIR/phase-plan-REVIEW.md
tmp_dir=<absolute temp dir>
worker_handles=<space-separated handles, empty before dispatch>
```

- On resume, if `.stage2-in-progress` exists and the current `phase-plan.md`
  SHA-256 differs from `original_source_sha256`, stop with terminal state
  `error:stale-stage2-review`.
- On resume, if `.stage2-working-plan.md` is missing or its SHA-256 differs from
  `current_candidate_sha256`, stop with terminal state
  `error:stale-stage2-review`.
- If `.stage2-complete` exists and the current plan SHA-256 matches its recorded
  `phase_plan_sha256_after`, skip Stage 2.
- If `.stage2-complete` is absent, resume from `.stage2-in-progress` only when
  both source and candidate hashes match.
- If the recorded `tmp_dir` no longer exists on resume, create a new temp
  directory and atomically update only the `tmp_dir` field before launching
  reviewers.

### Stage 2 Round Algorithm

For rounds one through five:

1. Create two independent snapshots in the temp directory from
   `.stage2-working-plan.md`:

   ```text
   stage2-spec-r<round>.md
   stage2-exec-r<round>.md
   ```

2. Each snapshot starts with:

   ```markdown
   # Review Snapshot

   ## Source Context

   - Skill: orchestrator-cdx
   - Review contract: plan-review-cdx
   - Phase: <phase argument>
   - Phase directory: <absolute PHASE_DIR>
   - Source plan: <absolute PHASE_DIR>/phase-plan.md
   - Working candidate: <absolute PHASE_DIR>/.stage2-working-plan.md
   - Original source SHA-256: <original_source_sha256>
   - Current candidate SHA-256: <current_candidate_sha256>
   - Round: <round>
   - Required clean rounds: 2 consecutive clean rounds
   - Current clean round streak: <clean_round_streak>
   - Reviewer instruction: <absolute reviewer instruction file>

   ## Plan Under Review

   <current .stage2-working-plan.md content>
   ```

3. Start the spec reviewer and execution reviewer before waiting for either
   reviewer.
4. The spec reviewer reads `plan-reviewer-spec.md`, reviews only the spec
   snapshot, and returns the exact review section.
5. The execution reviewer reads `plan-reviewer-exec.md`, reviews only the
   execution snapshot, and returns the exact review section.
6. Neither reviewer receives the other reviewer output.
7. Record both worker handles in `.stage2-in-progress` before the first wait.
8. Wait for both reviewers.
9. Merge returned reviews into `phase-plan-REVIEW.md` using this delimiter
   before the spec section:

   ```text

   ---

   ## Spec Review - Round <N>
   ```

10. Append the execution section immediately after the spec section:

    ```text

    ## Execution Review - Round <N>
    ```

11. Run the corrector pass using `plan-review-cdx` correction rules:
    - Fix every issue raised by both reviewers.
    - Fix every non-contradictory MEDIUM, HIGH, and CRITICAL issue.
    - LOW issues are advisory unless they can be fixed without scope growth.
    - If reviewers contradict on a CRITICAL or HIGH issue, record both
      positions in `phase-plan-REVIEW.md`, transition to
      `checkpoint:plan-review-decision`, and resume after the user provides a
      decision.
    - If reviewers contradict on a MEDIUM or LOW issue, defer to the execution
      reviewer and record the reason in `phase-plan-REVIEW.md`.
    - After addressing an issue, mark it resolved in `phase-plan-REVIEW.md`.
    - If an issue requires a user decision or external information, mark it
      `[UNRESOLVED]` in `phase-plan-REVIEW.md`.
12. Write the corrected candidate back to `.stage2-working-plan.md`.
13. Parse convergence from `phase-plan-REVIEW.md`.
14. Rewrite `.stage2-in-progress` atomically with the new
    `current_candidate_sha256`, updated `clean_round_streak`, next `round`
    value, active `tmp_dir`, and empty `worker_handles` before starting another
    reviewer batch.

### Stage 2 Convergence Parser

- The review delimiter is exactly this byte sequence:

  ```text
  \n\n---\n\n## Spec Review - Round <N>\n
  ```

- Review history starts at the first delimiter for Round 1.
- A round is clean only when that round's spec and execution sections contain no
  `[UNRESOLVED]` MEDIUM, HIGH, or CRITICAL issue and no unresolved MEDIUM, HIGH,
  or CRITICAL issue line.
- A resolved issue line is one that is struck through or explicitly marked
  `resolved`, `addressed`, or `fixed` in the same bullet.
- If the current round is clean, increment `clean_round_streak`.
- If the current round is not clean, reset `clean_round_streak` to zero after
  correction.
- Converged means `clean_round_streak=2`. Final convergence is impossible before
  Round 2.
- Cap-hit means five spec review rounds exist and `clean_round_streak` is less
  than two.
- If the delimiter is absent after a non-empty review run, stop with terminal
  state `error:stage2-delimiter-absent`.

On convergence:

- Atomically replace `$PHASE_DIR/phase-plan.md` with `.stage2-working-plan.md`.
- Preserve `$PHASE_DIR/phase-plan-REVIEW.md`.
- Write `$PHASE_DIR/.stage2-complete` atomically:

```text
source_sha256_before=<sha256 before Stage 2>
phase_plan_sha256_after=<sha256 after correction>
rounds=<number of rounds used>
clean_round_streak=2
required_clean_rounds=2
```

On cap-hit:

- Write `$PHASE_DIR/.stage2-cap-hit` with the original source hash, current
  candidate hash, round count, clean-round streak, and unresolved issue summary.
- Transition to terminal state `gate-failed:plan-review`.

## Stage 3: Reserved

Stage 3 is intentionally unused. Do not add behavior here in this release.

## Stage 4: Execute

Purpose: execute the reviewed plan through GSD and capture the ending commit.

Before execution, inspect:

```bash
git status --porcelain --untracked-files=all
```

If any dirty path is outside `$PHASE_DIR`, stop with terminal state
`error:dirty-worktree-before-execute`. Dirty files inside `$PHASE_DIR` are
allowed because prior stages write plan and sentinel artifacts there.

Execution rules:

- Follow `gsd:execute-phase` for the requested phase.
- Preserve the executor return text for parsing and handoff context.

Checkpoint extraction precedence:

1. XML-like task marker containing `checkpoint:<reason>` wins.
2. Markdown line `**Type:** <reason>` wins if no XML-like marker exists.
3. If `## CHECKPOINT REACHED` exists but no reason is found, use
   `checkpoint:unknown`.

Success requires all of these in the executor return text:

- `## PLAN COMPLETE`
- `**SUMMARY:** <path>`
- The referenced summary file exists and is non-empty.

On success:

- Write `git rev-parse HEAD` to `$PHASE_DIR/END-SHA`.
- Write `$PHASE_DIR/.stage4-complete` containing the same commit SHA.

If the executor returns without a checkpoint and without success markers, stop
with terminal state `error:execute-incomplete`.

## Stage 5: Verify

Purpose: run GSD verification against the executed phase.

Rules:

- Follow `gsd:verify-work` for the requested phase.
- Preserve the verifier return text for parsing and handoff context.
- If the return text contains `gaps_found`, stop with terminal state
  `gate-failed:verification`.
- If the return text contains `human_needed`, stop with terminal state
  `checkpoint:human-verify`.

Success requires all of these:

- Return text contains `## Verification Complete`.
- Return text contains `**Status:** passed`.
- A verification report is found under `$PHASE_DIR`.
- The report has frontmatter containing `status: passed`.

Report resolution:

1. Prefer an explicit report path from the verifier return text.
2. Otherwise search `$PHASE_DIR` for a single verification report whose filename
   contains `verification` case-insensitively.
3. If zero or multiple reports are found, stop with terminal state
   `error:verification-report-ambiguous`.

On success, write `$PHASE_DIR/.stage5-complete` containing the verification
report path and the report SHA-256.

## Stage 6: Post-Execution Review

Purpose: review the executed diff for quality and security before final
completion.

Rules:

- Diff range is exactly `START-SHA..END-SHA`.
- Require `START-SHA`, `END-SHA`, and `.stage4-complete`.
- If `git rev-parse HEAD` does not equal `END-SHA`, stop with terminal state
  `error:head-drift-before-review`.
- Start the deep-review worker and security-review worker before waiting for
  either worker.
- Record both worker handles before the first wait.
- Wait for both workers before interpreting either result.
- The deep-review worker must write `$PHASE_DIR/DEEP-REVIEW.md`.
- The security worker must write `$PHASE_DIR/SECURITY-REVIEW.md`.

Security fallback:

- If `security-review` is available, the security worker uses it.
- If unavailable, the security worker runs this built-in checklist against the
  diff:
  - Secrets or credentials added.
  - Unsafe shell execution or unsanitized path handling.
  - Authentication or authorization bypass.
  - Unvalidated external input reaching file, network, or process boundaries.
  - Dependency or install-script changes that expand trust or execution surface.
  - Sensitive data written to logs, reports, or terminal output.

Worker status contract:

- Each worker returns one status line in the last ten non-empty lines.
- Accepted forms:

```text
STATUS: clean
STATUS: findings:N
STATUS: error:<reason>
```

- `N` is a non-negative integer.
- `findings:0` is normalized to `clean`.
- Missing or malformed status is `error:stage6-status-malformed`.
- Any worker error other than the documented security fallback failure is
  terminal state `error:stage6-worker:<reason>`.

Findings flow:

- If both workers are clean, write `.stage6-complete` and terminal state `done`.
- If one or both workers report findings, present the user with two choices:
  - Acknowledge findings and finish: terminal state `done (reviews:findings)`.
  - Create follow-ups: use `to-issues` when available; otherwise write
    `$PHASE_DIR/FOLLOWUPS.md`; terminal state `done-with-followups`.
- If user input is unavailable or times out, write
  `$PHASE_DIR/.stage6-default-applied` and terminal state
  `done (reviews:findings, auto-acknowledged)`.

On every non-error Stage 6 path, write `$PHASE_DIR/.stage6-complete`:

```text
diff=<START-SHA>..<END-SHA>
deep=<clean|findings:N>
security=<clean|findings:N|fallback-clean|fallback-findings:N>
terminal=<terminal state selected by Stage 6>
```

## Terminal Handler

Run this handler exactly once per invocation for every terminal state.

Terminal artifact directory:

- If `PHASE_DIR` has been resolved, set `TERMINAL_DIR=$PHASE_DIR`.
- If `PHASE_DIR` has not been resolved but `.planning/` exists, set
  `TERMINAL_DIR=.planning/orchestrator-cdx-terminal`.
- If `.planning/` does not exist, set `TERMINAL_DIR=.orchestrator-cdx-terminal`
  under the current working directory.
- Create `TERMINAL_DIR` before writing terminal artifacts.

Required behavior:

- Write `$TERMINAL_DIR/.terminal-state` atomically:

```text
state=<terminal state>
phase=<phase>
mode=<mode>
timestamp_utc=<ISO-8601 UTC timestamp>
```

- If `$TERMINAL_DIR/.handoff-complete` exists, skip handoff.
- If `handoff` is available, use it to create a concise recovery handoff and
  record the output path in `$TERMINAL_DIR/HANDOFF-PATH.txt`.
- If `handoff` is unavailable, write `$TERMINAL_DIR/HANDOFF.md` with:
  - Phase and mode.
  - Terminal state.
  - Current git HEAD.
  - Values of `START-SHA` and `END-SHA` when present.
  - Existing stage sentinel files.
  - The next action needed to recover or continue.
- After either handoff path succeeds, write `$TERMINAL_DIR/.handoff-complete`.
- If `.notify-complete` exists, skip notification.
- If an `ntfy-notify` send script exists, send one notification summarizing
  phase, mode, terminal state, and important artifact paths.
- On notification success, write `$TERMINAL_DIR/.notify-complete`.
- On notification failure, write `$TERMINAL_DIR/.notify-failed` and keep the
  terminal state unchanged.
- If no send script exists, do not write `.notify-complete` or
  `.notify-failed`; notification absence is not a failure.

## Artifact Reference

Stage artifacts live in the resolved phase directory unless the terminal handler
falls back to a repo-level terminal directory.

```text
START-SHA
END-SHA
phase-plan.md
phase-plan-REVIEW.md
.stage1-complete
.stage2-working-plan.md
.stage2-in-progress
.stage2-complete
.stage2-cap-hit
.stage4-complete
.stage5-complete
.stage6-complete
.stage6-default-applied
DEEP-REVIEW.md
SECURITY-REVIEW.md
FOLLOWUPS.md
.terminal-state
HANDOFF.md
HANDOFF-PATH.txt
.handoff-complete
.notify-complete
.notify-failed
```

All sentinel writes must be atomic: write to a sibling temp file in the same
directory, then rename into place.

## Verification Notes

Before considering repo changes complete, run the static checks used by this
skill's implementation plan:

```bash
python - <<'PY'
from pathlib import Path
path = Path("skills/orchestrator-cdx/SKILL.md")
text = path.read_text()
assert text.startswith("---\n"), "missing opening frontmatter fence"
end = text.index("\n---\n", 4)
data = {}
for line in text[4:end].splitlines():
    if ":" in line and not line.startswith(" "):
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
assert data.get("name") == "orchestrator-cdx", data
print("frontmatter name OK")
PY

bash -n install-skills.sh
```

Also verify installer and README registry entries, run the documented Stage 2
parser fixtures, and smoke-test `plan`, `full`, and worker-unavailable flows in
scratch GSD repositories when the required worker tooling is available.
