---
name: orchestrate-clc
description: Thin policy layer over GSD that drives a phase end-to-end with a Claude-only plan-review gate, parallel post-execution review via subagent dispatch, ntfy notifications, and a handoff document on terminal state. Triggers on "/orchestrate-clc", "/orchestrate-clc full <phase>", "/orchestrate-clc plan <phase>", "/orchestrate-clc verify <phase>", "run the pipeline", "orchestrate this phase".
version: 0.1.0
---

<!-- no-codex-audit: 2026-05-23 -->

# orchestrate-clc

## 1. Purpose

`orchestrate` is a thin policy layer over the GSD skill that drives a single phase end-to-end (plan → execute → verify → review) with strong quality gates between stages. GSD provides the spine (`gsd:plan-phase`, `gsd:execute-phase`, `gsd:verify-work`); `orchestrate` substitutes a Claude-only two-reviewer plan QA loop for GSD's single plan-checker, dispatches `deep-review` (+ `security-review` when available) in parallel after execution as Claude `Agent` subagents, calls `/handoff` once at any terminal state, and pushes an `ntfy` notification with the terminal state. The pipeline is autonomous between stage boundaries but has documented hard-stop terminal states (plan-review cap-hit, GSD checkpoint, Stage-6 findings) at designed user-intervention points.

## 2. Documented constants

```
NTFY_TOPIC                = "ab-mac"                 # author default; see Section 13 — migrate to ~/.config/orchestrate-clc/.env
NTFY_SCRIPT_CANDIDATES    = [
  "$HOME/.claude/sandbox/skills/ntfy-notify/scripts/ntfy_send.sh",
  "$HOME/.claude/skills/ntfy-notify/scripts/ntfy_send.sh"
]
PLAN_REVIEW_DISPATCH      = ["claude-only", "<abs-path-to-PLAN-file>"]
                           # two whitespace-separated whole tokens; never concatenated
PLAN_REVIEW_MAX_ROUNDS    = 5                        # plan-review internal default
SHA256_CMD                = "shasum -a 256 | awk '{print \$1}'"
                           # pinned 64-lowercase-hex format, no trailing newline; POSIX-portable
```

`PLAN_REVIEW_DISPATCH` MUST be constructed as two whitespace-separated tokens. The orchestrator asserts the serialized args string matches `^claude-only /` before dispatch. Never concatenate.

## 3. When to use / not to use

**Use** when you want a full, gated, audit-friendly run of a phase that has a written roadmap entry: plan creation, plan QA, execution with atomic commits, goal-backward verification, parallel post-execution code review, handoff, and notification.

**Do NOT use** for:
- Ad-hoc fixes that don't have a roadmap entry.
- Exploratory questions / one-shot edits.
- Unroadmapped work (the orchestrator requires `.planning/ROADMAP.md`).
- Tasks that don't fit GSD's phase contract.

## 4. Prerequisite check (run before any stage)

1. **Working directory**: must contain `.planning/`. Abort with usage if not at project root.
2. **Roadmap**: `.planning/ROADMAP.md` must exist. Abort otherwise.
3. **Argument grammar**: `/orchestrate-clc <mode> <phase>` — both arguments required. **No defaulting on a single token** (avoids the ambiguity between phase-name "full" and mode "full"). If only one token is supplied, abort with usage.
4. **Mode validation**: `<mode>` ∈ {`full`, `plan`, `verify`}. Abort otherwise.
5. **Phase resolution** against `.planning/phases/`:
   - Exact directory-name match wins → `PHASE_DIR=.planning/phases/<phase>`.
   - Else prefix match: if exactly one directory has `<phase>` as a prefix, use it.
   - Zero matches or multi-prefix matches: abort with the candidate list.
6. **Security-review availability** (optimistic-dispatch policy):
   - `/security-review` is a built-in slash command with no on-disk SKILL.md confirmed. A filesystem probe would always be false and would silently disable Stage-6 security checks — wrong.
   - Set `SECURITY_REVIEW_AVAILABLE=true` unconditionally.
   - Stage 6 dispatches the security-review subagent unconditionally. If the subagent's `Skill(security-review, …)` invocation fails (skill not found), the subagent returns `STATUS: error:security-review-unavailable`. The orchestrator maps that specific error to `n/a` rather than terminal `error`.
   - **Do NOT** probe via `Skill(security-review, "dry-run")` — `dry-run` is not a defined arg and would trigger a real review.
7. **plan-review name-collision check**: probe all three skill roots:
   ```bash
   find ~/.claude/skills ~/.claude/sandbox/skills ~/.agents/skills \
     -maxdepth 2 -type d -name "plan-review-clc" 2>/dev/null
   ```
   - Variants like `plan-review-cdx/` are fine.
   - If more than one bare `plan-review/` exists, the orchestrator must verify (via byte-equality diff) that they're duplicates. If they are duplicates, proceed (the harness resolves `plan-review` to one of them and behaviour is identical). If they differ, abort with an instruction to rename one or alias the orchestrator's invocation to a canonical path.
   - Known state on author's system (2026-05-23): `~/.claude/skills/plan-review-clc/SKILL.md` and `~/.claude/sandbox/skills/plan-review-clc/SKILL.md` are byte-identical duplicates; this is acceptable.
8. **STATE.md position**: read `.planning/STATE.md` and note the current `Status:` line for resumption logic.

## 5. Modes and stage coverage

- `full <phase>` — stages 1, 2, 4, 5, 6, then terminal handler (7, 8).
- `plan <phase>` — stages 1, 2, then terminal handler. Successful convergence → terminal `done`. Cap-hit → terminal `gate-failed:plan-review`.
- `verify <phase>` — stages 5, 6, then terminal handler. Requires both `START-SHA` and `END-SHA` in `$PHASE_DIR`; abort with a usage message if either is missing.

**Stage 3 is reserved (not used).** An earlier draft included a TDD-enforcement stage; numbering is preserved for stability. Implementers MUST NOT insert a Stage 3.

## 6. Pipeline stages

### Stage 1 — Plan

```bash
git rev-parse HEAD > "$PHASE_DIR/START-SHA"
```
Invoke `Skill(gsd:plan-phase, "<phase>")` with the bare phase name as the single positional argument.

After plan-phase returns, enumerate plan files (bash-3 compatible — macOS default):
```bash
PLAN_FILES=()
while IFS= read -r f; do PLAN_FILES+=("$f"); done < <(ls "$PHASE_DIR"/*-PLAN.md 2>/dev/null | sort)
```

**Empty-set guard**: if `${#PLAN_FILES[@]}` is 0, abort with terminal `error: gsd:plan-phase produced no *-PLAN.md files in $PHASE_DIR; expected multi-plan convention. Check that this phase's roadmap entry yields per-task plans rather than a single phase-plan.md.` This is **not** a silent skip.

Write `$PHASE_DIR/.stage1-complete` containing the list of plan filenames (one per line). Stage 1 does **not** hash contents.

### Stage 2 — Plan-review gate (Claude-only), iterated per plan file

For each `PLAN_FILE` in `${PLAN_FILES[@]}`:

1. Snapshot for review:
   ```bash
   base="$(basename "$PLAN_FILE" .md)"
   review_file="$PHASE_DIR/${base}-REVIEW.md"
   cp "$PLAN_FILE" "$review_file"
   ```

2. Construct the two-token argument list and assert before dispatch:
   ```bash
   args="claude-only $review_file"
   case "$args" in
     "claude-only /"*) : ;;  # ok
     *) abort "PLAN_REVIEW_DISPATCH assertion failed: args=$args" ;;
   esac
   ```
   Invoke as:
   ```
   Skill(plan-review-clc, "claude-only /abs/path/to/01-PLAN-REVIEW.md")
   ```
   plan-review's tokenizer splits on whitespace and matches whole tokens; the leading `claude-only` token routes to the Claude-only fallback (two Claude `Agent` subagents — `plan-reviewer-spec`, `plan-reviewer-exec`).

3. **plan-review may interactively ask the user to extend `max_rounds`** on cap-hit. The orchestrator cannot interpose on that prompt (it's suspended inside the `Skill` call). When running under `/orchestrate-clc`, the user must decline plan-review's extension prompt for the no-Codex/cap-hit invariant to hold cleanly. The orchestrator's cap-hit detection still fires (it counts actual round sections, not `PLAN_REVIEW_MAX_ROUNDS`), so accidental extension does not break detection — it just delays terminal-state transition.

4. **Convergence detection** (file-based, anchored against plan-review's actual append template documented in `~/.claude/skills/plan-review-clc/SKILL.md`):

   plan-review appends `\n\n---\n\n## Spec Review — Round <N>\n` (fallback mode) or `\n\n---\n\n## Claude Review — Round <N>\n` (default mode). Because the orchestrator forces claude-only, only the **Spec Review** form should appear.

   **Delimiter regex** (multi-line, anchored, ERE):
   ```
   ^---$\n^[[:space:]]*$\n^## Spec Review — Round [0-9]+$
   ```
   Locate the **first** match in `$review_file`. Everything from this delimiter to EOF is the review-history region. `Round [0-9]+` (not just `Round 1`) tolerates future plan-review revisions that change the starting round number.

   - **Converged** iff: in the review-history region, every round section contains **zero** `[UNRESOLVED]` markers AND **zero** un-struck-through `[CRITICAL|HIGH|MEDIUM]` items. (Struck-through items appear inside `~~…~~` and are followed by an `**Addressed**:` annotation; ignore them.)
   - **Cap-hit** iff: ≥ 5 round sections (matching `^## (Spec|Execution) Review — Round [0-9]+$`) exist in the review-history region AND ≥ 1 `[UNRESOLVED]` MEDIUM+ marker remains. Counts **actual** sections, so user-extended runs are still detected.
   - **Delimiter absent** in a non-empty post-plan-review file: abort with terminal `error: plan-review delimiter not found in <file>; the plan-review append contract may have changed`.

5. **On cap-hit**:
   - Write `$PHASE_DIR/.stage2-cap-hit` containing the failing plan's basename and the round count (one line: `<basename>:<round-count>`).
   - Transition immediately to terminal `gate-failed:plan-review`. Do not process remaining plans.
   - **Resumption rule**: presence of `.stage2-cap-hit` means re-surface terminal state; do not auto-retry. Forced retry requires the user to delete both `.stage2-cap-hit` AND the failing `<base>-REVIEW.md`.

6. **On convergence**:
   1. **Backup** the GSD-emitted plan (idempotent):
      ```bash
      [ -f "$PLAN_FILE.orig" ] || cp "$PLAN_FILE" "$PLAN_FILE.orig"
      ```
      Preserves the original GSD output against the first successful Stage-1 emission even if Stage 2 is re-run on resume.
   2. Extract the converged plan portion: everything **before** the delimiter's first byte. The capture ends with the last line of plan content; the trailing blank-line + `---` is dropped.
   3. Write the converged portion to `$PLAN_FILE` atomically (temp + `mv`).
   4. Review history remains in `$review_file`.
   5. Record per-plan sentinel:
      ```bash
      printf '%s' "$(eval $SHA256_CMD < "$PLAN_FILE")" > "$PHASE_DIR/.stage2-converged-$base"
      ```

7. After **all** plan files converge (no cap-hit on any), write `$PHASE_DIR/.stage2-complete` as atomic JSON (temp + mv):
   ```bash
   tmp=$(mktemp "$PHASE_DIR/.stage2-complete.XXXXXX")
   # $json is {"01-PLAN.md": "<sha256>", "02-PLAN.md": "<sha256>", ...}
   printf '%s' "$json" > "$tmp"
   mv "$tmp" "$PHASE_DIR/.stage2-complete"
   ```

### Stage 3 — Reserved (not used)

See Section 5. Do not insert a Stage 3.

### Stage 4 — Execute

Invoke `Skill(gsd:execute-phase, "<phase>")` with the bare phase name as the single positional argument.

**Outcome detection (three-step, strict)**:

1. Parse the executor's structured return text for:
   - A literal `## CHECKPOINT REACHED` header at line-start, AND
   - A `type="checkpoint:<subtype>"` attribute on a `<task>` element.

   If both are present → terminal `checkpoint:<subtype>`. Do **not** run handoff/ntfy inline (the terminal handler runs them exactly once).

2. Else read `.planning/STATE.md`; find the line matching anchored regex `^Status: (.+)$`. Match the capture against the documented GSD allow-list:
   - `Phase complete` → **success** → continue to `END-SHA` capture.
   - `In progress` → terminal `error: execute returned with STATE.md Status=In progress and no CHECKPOINT REACHED; possible GSD contract drift`.
   - Any other value → terminal `error: unexpected STATE.md Status: <line>`.

3. **No `^Status:` line found** (corrupted/partial STATE.md) → terminal `error: STATE.md missing Status line; possible corruption`.

Substring matching against `paused` / `checkpoint` in STATE.md is **forbidden** — those tokens do not appear in `Status:` under documented GSD behavior.

On success:
```bash
git rev-parse HEAD > "$PHASE_DIR/END-SHA"
cp "$PHASE_DIR/END-SHA" "$PHASE_DIR/.stage4-complete"
```

### Stage 5 — Verify

Invoke `Skill(gsd:verify-work, "<phase>")` with the bare phase name as the single positional argument. On return (any non-error), write `$PHASE_DIR/.stage5-complete`.

### Stage 6 — Parallel post-execution review (multi-agent dispatch via Claude `Agent` subagents)

Read both SHAs:
```bash
start="$(cat "$PHASE_DIR/START-SHA")"
end="$(cat "$PHASE_DIR/END-SHA")"
diff_range="${start}..${end}"
```

**Dispatch policy**: in a single message, issue two `Agent` tool calls in parallel (one if `!SECURITY_REVIEW_AVAILABLE`, but per Section 4 that flag is unconditionally `true`). Both subagents are Claude (`subagent_type: "general-purpose"`).

#### Subagent prompt — deep-review

```
You are a Claude general-purpose subagent. Invoke the deep-review skill via:

  Skill(deep-review, "Review the changes in this repository between commit
  <start> and commit <end> (git diff <start>..<end>). Write your full review
  findings to <PHASE_DIR>/DEEP-REVIEW.md.")

PROHIBITION (enforceable scope): You MUST NOT use a subagent_type value
starting with "codex:" in any Agent tool YOU directly call. You cannot
introspect into nested skills' own Agent dispatches; that transitive
guarantee is enforced statically by the orchestrator's Verification 13(b)
audit, not by you at runtime. If you find yourself about to dispatch a
"codex:*" subagent_type directly, abort and return:
  STATUS: error:codex-path-detected

Nested subagents inside the deep-review skill's own decomposition are
allowed.

STATUS line contract: somewhere in the LAST 10 lines of your final return
string, emit a line matching exactly one of these forms on its own line:

  STATUS: clean
  STATUS: findings:N        (N integer; report 0 as STATUS: clean for clarity,
                             but findings:0 is also accepted)
  STATUS: error:<reason>    (reason non-empty)

The orchestrator scans the last 10 lines for the first match of
^STATUS: (clean|findings:[0-9]+|error:.+)$ -- additional sign-off text after
the STATUS line is tolerated.

Finding-count rule (for findings:N): N is the count of MEDIUM-or-higher
items in the DEEP-REVIEW.md file you wrote. Count by inspecting the
written file's "### Issues" or "## Issues" section for MEDIUM/HIGH/CRITICAL
severity markers (treat P0-P2 in deep-review's vocabulary as MEDIUM+).
This is a file-anchored count, not a subjective judgment.

Nested subagent text in the conversation transcript is invisible to the
orchestrator unless you surface it ABOVE the STATUS line.
```

Substitute `<start>`, `<end>`, `<PHASE_DIR>` literally when constructing the prompt.

#### Subagent prompt — security-review

Same shape as deep-review, but invoke `Skill(security-review, "<free-form prompt>")` because security-review has no confirmed argument grammar (no on-disk SKILL.md). Pass a prompt describing the diff scope and writing target:

```
You are a Claude general-purpose subagent. Invoke the security-review skill via:

  Skill(security-review, "Perform a security review of the changes in this
  repository between commit <start> and commit <end> (git diff
  <start>..<end>). Write your full findings to
  <PHASE_DIR>/SECURITY-REVIEW.md.")

If the Skill(security-review, ...) invocation fails because the skill is not
registered or returns a 'not found'-class error, emit on its own line in
the last 10 lines of your final return string:

  STATUS: error:security-review-unavailable

The orchestrator maps that specific error to "n/a" (not a pipeline error).

All other rules from the deep-review prompt apply identically (PROHIBITION,
STATUS line contract, finding-count rule).
```

#### `Agent` call shape

```
Agent({
  description: "Deep-review phase <phase>",
  subagent_type: "general-purpose",
  prompt: <prompt_deep>
})
Agent({
  description: "Security-review phase <phase>",
  subagent_type: "general-purpose",
  prompt: <prompt_security>
})
```

Issue both calls in one message for parallel execution.

#### STATUS parsing

For each subagent's return text:
1. Scan the **last 10 non-empty lines** in order.
2. Take the **first** line matching `^STATUS: (clean|findings:[0-9]+|error:.+)$`.
3. Normalize `findings:0` → `clean` before branching.
4. If no line in the last 10 matches, treat as `error: status line malformed`.

#### Branch

- **Security-review unavailable mapping**: if the security subagent returns `error:security-review-unavailable`, the orchestrator maps that specific error to `n/a` and continues with deep-review's status only.
- **Any other `error:<reason>` from any subagent** → terminal `error: Stage 6 subagent error: <agent> reports <reason>`. **No `AskUserQuestion`.**
- **Both `clean`** (after `findings:0`→`clean` normalization and after `n/a` mapping) → continue (no prompt).
- **At least one `findings:N` (N ≥ 1), none errored** → `AskUserQuestion` with three options:
  - **(a) Acknowledge findings and finish** → terminal `done` with `(reviews:findings)` suffix.
  - **(b) Open follow-up issues** → `Skill(to-issues, "Open follow-up issues from the review findings in $PHASE_DIR/DEEP-REVIEW.md and $PHASE_DIR/SECURITY-REVIEW.md")`. Then terminal `done-with-followups`.
  - **(c) Extend with fix-wave** → `Skill(gsd:add-phase, "Add a fix-wave phase 'fix-wave-for-<phase>' addressing findings in $PHASE_DIR/DEEP-REVIEW.md and $PHASE_DIR/SECURITY-REVIEW.md")`. Then terminal `done-extended`.
- **Non-interactive fallback** (SLURM, `/loop`, scheduled runs — `AskUserQuestion` unavailable or times out): default to option **(a)** → terminal `done (reviews:findings, auto-acknowledged)`. Write a sentinel file:
  ```
  $PHASE_DIR/.stage6-default-applied
  ```
  containing the ISO-8601 UTC timestamp and the findings count. The Stage 8 ntfy message at priority 4 explicitly flags this: `Phase <X> complete; <N> findings auto-acknowledged — review $PHASE_DIR/DEEP-REVIEW.md.`
- **`to-issues` completion check** (after option (b)): inspect the `Skill(to-issues, …)` return text for evidence that issues were created (issue URLs, IDs, or a success line). If no such evidence is present (cancelled mid-quiz or errored), downgrade to terminal `done (to-issues-incomplete)` with a priority-4 ntfy noting the cancellation.

Write diagnostic-only `$PHASE_DIR/.stage6-timings.json` with the dispatch and return timestamps of each subagent.

Write `$PHASE_DIR/.stage6-complete` containing one line: `deep:<status>;security:<status|n/a>`.

### Stage 7 — Handoff document (unified terminal handler, runs exactly once)

Run on **every** terminal state — `done`, `done-with-followups`, `done-extended`, `gate-failed:*`, `checkpoint:*`, `error` — to produce a single handoff artifact for the next session.

1. Pre-create the output tempfile portably (BSD/GNU compatible — avoid `mktemp -t` and avoid template suffixes after `XXXXXX`, which BSD `mktemp` does not expand):
   ```bash
   handoff_tmp=$(mktemp "${TMPDIR:-/tmp}/handoff-XXXXXX")
   handoff_out="${handoff_tmp}.md"
   mv "$handoff_tmp" "$handoff_out"
   ```

2. **Snapshot pre-invocation** handoff files for deterministic discovery:
   ```bash
   ls "${TMPDIR:-/tmp}"/handoff-*.md 2>/dev/null | sort > "/tmp/.handoff-before.$$"
   ```

3. Invoke `Skill(handoff, "<context-aware free-form description>; write the handoff document to $handoff_out")`. The description must include:
   - The terminal state (`done`, `gate-failed:plan-review`, etc.).
   - The phase name and `$PHASE_DIR`.
   - For terminal state `error`: the **verbatim** error message, so the next session can recover.
   - For `checkpoint:<subtype>`: the subtype and the executor's reason text.
   - For `gate-failed:plan-review`: the failing plan basename and round count.

4. **Deterministic path resolution** (replaces 60-second mtime windows):
   1. If `$handoff_out` is now non-empty, use it. Done.
   2. Else diff:
      ```bash
      comm -13 "/tmp/.handoff-before.$$" \
        <(ls "${TMPDIR:-/tmp}"/handoff-*.md 2>/dev/null | sort) \
        > "/tmp/.handoff-new.$$"
      ```
      Take the file listed in `/tmp/.handoff-new.$$`.
   3. If zero new files appear: terminal `error: handoff produced no output file`.
   4. If multiple new files appear (extremely unlikely; would mean handoff or another concurrent invocation wrote multiple): take the most recently modified, log the others to stderr.

5. Record the chosen path:
   ```bash
   {
     printf '%s\n' "$handoff_path"
     printf 'mtime=%s\n' "$(stat -f '%m' "$handoff_path" 2>/dev/null || stat -c '%Y' "$handoff_path")"
   } > "$PHASE_DIR/HANDOFF-PATH.txt"
   ```

6. Clean up:
   ```bash
   rm -f "/tmp/.handoff-before.$$" "/tmp/.handoff-new.$$"
   ```

### Stage 8 — Notify (fail-soft, runs exactly once)

Resolve `NTFY_SCRIPT`:
```bash
NTFY_SCRIPT=""
for cand in "${NTFY_SCRIPT_CANDIDATES[@]}"; do
  if [ -x "$cand" ] || [ -f "$cand" ]; then NTFY_SCRIPT="$cand"; break; fi
done
```
If none exist, log `[orchestrate] ntfy script not found; skipping notification` to stderr and **do not** change terminal state.

Otherwise send a single notification (the `${NTFY_DEFAULT_TOPIC:-ab-mac}` form is forward-compatible at zero cost — uses an env-var topic when set, falls back to `ab-mac`):

```bash
bash "$NTFY_SCRIPT" \
  --topic "${NTFY_DEFAULT_TOPIC:-ab-mac}" \
  --title "orchestrate: <phase> <terminal-state>" \
  --priority "<priority>" \
  "<one-line summary>" \
  || echo "[orchestrate] ntfy notification failed; continuing" >&2
```

**Priority guide**:

| Terminal state | Priority |
|---|---|
| `done` (clean reviews) | 3 |
| `done` `(reviews:findings)` / `done-with-followups` / `done-extended` | 4 |
| `done` `(reviews:findings, auto-acknowledged)` / `done (to-issues-incomplete)` | 4 |
| `gate-failed:plan-review` / `gate-failed:sha-drift` | 4 |
| `checkpoint:*` | 4 |
| `error` | 5 |

The one-line summary should include `$PHASE_DIR/HANDOFF-PATH.txt`'s recorded path so the next session can pick it up.

## 7. Gate semantics

- **Pass** = no MEDIUM/HIGH/CRITICAL findings unresolved (Stage 2 convergence detector; Stage 6 STATUS line).
- A failed gate transitions to a terminal state; the pipeline never silently advances past unresolved MEDIUM+ findings.
- The orchestrator **never** edits code in response to findings. Code changes are GSD's job (Stage 4) or a follow-up fix-wave (option (c)).

## 8. Artifact layout

Under `$PHASE_DIR = .planning/phases/<phase>/`:

```
START-SHA, END-SHA
01-PLAN.md, 02-PLAN.md, ...                    (GSD; rewritten by orchestrator on convergence)
01-PLAN.md.orig, 02-PLAN.md.orig, ...          (orchestrator: original GSD output, idempotent)
01-PLAN-REVIEW.md, ...                         (orchestrator: per-plan review history)
XX-SUMMARY.md, XX-VERIFICATION.md              (GSD)
DEEP-REVIEW.md, SECURITY-REVIEW.md             (orchestrator; SECURITY only when available)
HANDOFF-PATH.txt                               (orchestrator: <path>\nmtime=<epoch>)
.stage1-complete                               (list of plan filenames, one per line)
.stage2-converged-<basename>                   (one per converged plan; contains sha256)
.stage2-complete                               (atomic JSON {filename: sha256})
.stage2-cap-hit                                (only on cap-hit; <basename>:<round-count>)
.stage4-complete                               (END-SHA)
.stage5-complete
.stage6-complete                               (deep:<status>;security:<status|n/a>)
.stage6-default-applied                        (only when non-interactive auto-ack)
.stage6-timings.json                           (diagnostic-only)
```

## 9. Terminal state × required sentinels × STATE.md mapping

| Terminal state | Required sentinels in `$PHASE_DIR` | STATE.md `Status:` after exit |
|---|---|---|
| `done` | `.stage1-complete`, `.stage2-converged-*`, `.stage2-complete`, `.stage4-complete`, `.stage5-complete`, `.stage6-complete` | `Phase complete` (written by GSD; **not** modified by orchestrator) |
| `done (reviews:findings)` | same as `done` | same |
| `done (reviews:findings, auto-acknowledged)` | same as `done` + `.stage6-default-applied` | same |
| `done (to-issues-incomplete)` | same as `done` | same |
| `done-with-followups` | same as `done` | same |
| `done-extended` | same as `done` | `Phase complete` for current phase; new phase added by `gsd:add-phase` |
| `gate-failed:plan-review` | `.stage1-complete`, `.stage2-cap-hit` (no `.stage2-complete`, no `.stage4+`) | unchanged by orchestrator |
| `gate-failed:sha-drift` (Stage 6 resumption with stale END-SHA) | `.stage1`, `.stage2`, `.stage4`, `.stage5`, `.stage6` (stale) | unchanged by orchestrator; ntfy priority 4 |
| `checkpoint:<type>` | `.stage1-complete`, `.stage2-complete` (no `.stage4-complete`) | left as GSD wrote it (`In progress` is expected) |
| `error` | whatever sentinels were written before failure | unchanged by orchestrator |

The orchestrator never writes to `STATE.md` directly — only GSD does. The orchestrator's terminal state is recorded by sentinels + ntfy + handoff, not by STATE.md mutation.

## 10. Resumption (sentinel-based)

When `/orchestrate-clc <mode> <phase>` is re-invoked on an in-progress phase:

- **Stage 1**: skip if `.stage1-complete` exists AND its recorded filename list equals current `ls "$PHASE_DIR"/*-PLAN.md | sort`. **Set mismatch → invalidate Stages 1 AND 2** (new plan files appeared or old ones disappeared; per-plan sentinels become stale).
- **Stage 2**:
  - `.stage2-cap-hit` present → re-surface terminal `gate-failed:plan-review` and stop. Forced retry requires user cleanup of `.stage2-cap-hit` AND the failing `*-PLAN-REVIEW.md`.
  - `.stage2-complete` present AND every plan's current sha256 matches its recorded value → skip.
  - Else: per-plan loop — skip plans whose `.stage2-converged-<basename>` sentinel sha256 matches current file sha256; re-run plan-review on plans where the sha256 differs.
- **Stage 4**: skip if `.stage4-complete` exists.
- **Stage 5**: skip if `.stage5-complete` exists.
- **Stage 6**: skip if `.stage6-complete` exists AND `END-SHA` equals current `git rev-parse HEAD`. **On mismatch** (user committed manually between runs): transition to terminal `gate-failed:sha-drift`. The orchestrator does **not** auto-update `END-SHA` — that would silently revalidate reviews against a moved diff. The user must either revert their manual commits or delete `.stage6-complete` and `END-SHA` to acknowledge the drift.
- **Stages 7/8**: never skipped — they run exactly once per invocation, on the current terminal state.

## 11. Multi-agent dispatch summary (all-Claude; no Codex)

- **Stage 2**: parallel internally via plan-review's two Claude `Agent` subagents (`plan-reviewer-spec` + `plan-reviewer-exec`, claude-only fallback). The `claude-only` token guarantees plan-review's default Claude+Codex path is never entered.
- **Stage 4**: parallel internally via GSD's wave-based execution and Claude executor agents.
- **Stage 6**: orchestrator-level parallel `Agent` subagent dispatch — `deep-review` + `security-review` (when available) in one message, both `subagent_type: "general-purpose"` (Claude). Subagents invoke target skills **by name** via `Skill`, not by reading on-disk SKILL.md paths. Subagent prompts contain an active runtime check instructing the subagent to abort with `STATUS: error:codex-path-detected` if any nested `subagent_type: "codex:*"` would be used directly.

<!-- no-codex:prohibition-block-start -->
**Forbidden constructs** anywhere in this skill (use these literals only inside this delimited block; CI audits exclude this region):
- `subagent_type: "codex:codex-rescue"`
- `subagent_type: "codex:*"` (any value starting with `codex:`)
- `command -v codex` (or any equivalent runtime probe)
- Any branch keyed on `"codex` plugin presence
Treat each as a regression if it appears outside this block.
<!-- no-codex:prohibition-block-end -->

## 12. Durable contracts (do NOT remove without an ADR)

Quoted contract specs, not line citations (line numbers drift; specs are normative):

- **`PLAN_REVIEW_MODE` locked to `claude-only`.** No flag exposing the Codex path. Users who want Codex should fork.
- **`Agent` dispatches use `subagent_type: "general-purpose"` only.** No `codex:*` subagent types.
- **plan-review delimiter contract**: plan-review appends review history beginning with the byte sequence `"\n\n---\n\n## Spec Review — Round <N>\n"` where `<N>` is the round number (1 on first append). Sourced descriptively from plan-review SKILL.md's "Merge Reviews" section (the file templates around `## Spec Review — Round <round>`). The orchestrator's regex `^---$\n^[[:space:]]*$\n^## Spec Review — Round [0-9]+$` matches against this contract.
- **GSD executor checkpoint contract**: the executor MUST emit a top-level `## CHECKPOINT REACHED` header followed by a `**Type:** <subtype>` line (and a structured `<task type="checkpoint:<subtype>">` element) in its return text when it pauses for user interaction. Sourced descriptively from gsd/agents/executor/SKILL.md's "Example Return for Auth Gate" and "Checkpoint Protocol" sections.
- **GSD STATE.md `Status:` allow-list**: the executor writes either `Status: In progress` or `Status: Phase complete` after task completion. Sourced descriptively from gsd/agents/executor/SKILL.md's "State Updates" section. Substring matching against `paused`/`checkpoint` is forbidden.
- **Optimistic-dispatch policy for security-review**: assume available; on dispatch failure inside the subagent, return `STATUS: error:security-review-unavailable` and the orchestrator treats it as `n/a`. Does not block the pipeline.
- **No-Codex audit**: must be re-run when any chained skill is updated (see Section 13).

## 13. Pre-share TODOs (sharing-cleanup; safe to remove when sharing)

- `NTFY_TOPIC` currently uses `${NTFY_DEFAULT_TOPIC:-ab-mac}`. The `ab-mac` default is the author's personal topic and is benign on the author's machine. **For future updates / patches**: migrate the topic out of `SKILL.md` entirely into `~/.config/orchestrate-clc/.env` (read at runtime, no hardcoded fallback). Until that migration, anyone forking should either export `NTFY_DEFAULT_TOPIC` in the shell that launches Claude Code or rewrite the default in their fork.
- Replace `NTFY_SCRIPT_CANDIDATES` dual-path probe with a single canonical path or skill arg.
- **Security-review policy**: current default is `available-only` (optimistic dispatch, `n/a` on failure). Pre-share TODO is to add `always` (abort if dispatch fails) and `never` (force-skip) as opt-in flags.
- **User-facing note for plan-review extension prompt**: when running under `/orchestrate-clc`, decline plan-review's "extend max_rounds" prompt on cap-hit. The orchestrator's cap-hit detection still fires (it counts actual round sections), but declining keeps the budget at 5 rounds and avoids extra reviewer cost. There is no machine-readable way for the orchestrator to suppress this prompt from outside plan-review.

## 14. Verification

The following checks validate the skill after install. Run them once before relying on `/orchestrate-clc`.

1. **Static load check** (PyYAML — standard in most envs; does not require `python-frontmatter`):
   ```bash
   python -c "
   import yaml, sys
   t = open(sys.argv[1]).read()
   assert t.startswith('---\n'), 'missing frontmatter open fence'
   end = t.index('\n---\n', 4)
   yaml.safe_load(t[4:end])
   print('frontmatter OK')
   " ~/.claude/skills/orchestrate-clc/SKILL.md
   ```
   Must exit 0. Separately:
   ```bash
   grep -E '^tools:' ~/.claude/skills/orchestrate-clc/SKILL.md | wc -l
   ```
   must equal `0` (this skill intentionally omits the `tools:` field).

2. **Prerequisite-fail dry run**: `/orchestrate-clc full nonexistent-phase` in a directory with no `.planning/`. Must stop at the prerequisite check (Section 4), surface missing `.planning/`, and invoke **no** GSD command.

3. **End-to-end smoke** (scratch git repo): `gsd:new-project`, add a multi-plan phase, run `/orchestrate-clc full <phase>`. Confirm:
   - All artifacts in Section 8 exist.
   - `.stage2-complete` is JSON with each plan's sha256 matching `eval $SHA256_CMD < $PLAN_FILE`.
   - Per-task commits exist between `START-SHA` and `END-SHA`.
   - A single ntfy notification was sent to `ab-mac`.

4. **Parallel dispatch artifact check**: `mtime` of `DEEP-REVIEW.md` and `SECURITY-REVIEW.md` are close. Programmatic alternative: enable `.stage6-timings.json` and assert dispatch overlap.

5. **Resumption check**: interrupt after Stage 2; re-invoke. Confirm Stages 1–2 skipped. Edit one `*-PLAN.md` between runs: only that plan's review re-runs (sha256 mismatch); others' per-plan sentinels still match → skipped. Add a new `*-PLAN.md` to directory: Stages 1 AND 2 both invalidate.

6. **Notification fail-soft**: temporarily rename both `ntfy_send.sh` paths; run `/orchestrate-clc full <phase>`. Must reach `done`, write all sentinels, write `END-SHA`. Stderr contains `[orchestrate] ntfy notification failed; continuing` or `[orchestrate] ntfy script not found; skipping notification`.

7. **Cap-hit detection unit test** (synthetic-input, non-destructive): extract the convergence-detection logic as a bash function or Python snippet. Test it against three inline fixtures:

   **Fixture A (converged)** — `/tmp/test-converged.md`:
   ```
   # Plan content here
   
   ---
   
   ## Spec Review — Round 1
   
   ### Issues
   
   - ~~**[MEDIUM]** Some issue.~~ **Addressed**: fixed.
   
   ## Execution Review — Round 1
   
   - ~~**[HIGH]** Another issue.~~ **Addressed**: fixed.
   ```
   Expected: `converged=true`, `cap_hit=false`.

   **Fixture B (cap-hit)** — `/tmp/test-cap-hit.md` with 5 sections (alternating Spec/Execution Review Round 1 through 5), each containing one `[UNRESOLVED] **[MEDIUM]** Issue text` marker.
   Expected: `converged=false`, `cap_hit=true`.

   **Fixture C (delimiter absent)** — `/tmp/test-no-delim.md` with plan content but no `## Spec Review — Round N` heading.
   Expected: abort with `error: plan-review delimiter not found`.

   This test exercises the regex against the real append template; it does **not** modify any production file under `~/.claude/skills/plan-review-clc/`.

8. **Multi-plan iteration**: phase with two plan files; `/orchestrate-clc plan <phase>`. Both `*-PLAN-REVIEW.md` exist with claude-only fallback-mode sections; `.stage2-complete` JSON has both hashes; both `.stage2-converged-*` sentinels exist.

9. **Stage 4 checkpoint detection**: force GSD to emit a checkpoint (e.g. plan task `type="checkpoint:human-verify"`). Confirm transition to `checkpoint:human-verify`, no `END-SHA`, handoff + ntfy each run exactly once.

10. **Stage 4 fall-through error (code-review check)**: Stage 4 has three branches (CHECKPOINT block found → checkpoint; STATE.md `Status: Phase complete` → success; everything else → error). Runtime verification requires stubbing `gsd:execute-phase`, which mutates a shared skill — **skip runtime test**; replace with a code-review check that the three branches are present in the implemented SKILL.md.

11. **Stage 6 error vs findings**: prompt one subagent (via test harness) to return `STATUS: error:simulated`. Expected: terminal `error` immediately; no `AskUserQuestion`. Then `STATUS: findings:2`: `AskUserQuestion` with three options. Then `STATUS: findings:0`: normalize to `clean`, continue (no prompt). Then `STATUS: clean`: continue. Then `STATUS: error:security-review-unavailable` from the security subagent: map to `n/a`, continue with deep-review's status only.

11b. **Stage 6 non-interactive fallback**: dispatch with `AskUserQuestion` unavailable (e.g., simulate by short-circuiting the prompt). Subagent returns `STATUS: findings:3`. Expected: terminal `done (reviews:findings, auto-acknowledged)`, `.stage6-default-applied` sentinel written, ntfy priority 4 with auto-ack notice.

12. **mktemp portability**: BSD `mktemp` on macOS does **not** expand `XXXXXX` when followed by a suffix (it returns the template literally with `XXXXXX` intact). The Stage-7 portable pattern is:
    ```bash
    handoff_tmp=$(mktemp "${TMPDIR:-/tmp}/handoff-XXXXXX")
    handoff_out="${handoff_tmp}.md"
    mv "$handoff_tmp" "$handoff_out"
    ```
    Confirm on both macOS (BSD mktemp) and Linux (GNU mktemp) that `$handoff_out` ends in `.md` and points to a unique, existing file.

13. **No-Codex audit (CI gate; mechanical)**:

    a. **Self-audit** (orchestrator SKILL.md, excluding the delimited prohibition block):

    The audit must distinguish real violations (actual `subagent_type` assignments to `"codex:*"`, real `command -v codex` probes) from policy-documenting prose (subagent prompts that reference `"codex:*"` to instruct the subagent to abort, durable-contract sections that name the locked-out path, verification commands that match `codex:` as part of their own regex). Real violations only appear inside fenced code blocks. Scan only those, outside the prohibition block, and only for the tight assignment / probe patterns:

    ```bash
    awk '
      /<!-- no-codex:prohibition-block-start -->/{skip=1; next}
      /<!-- no-codex:prohibition-block-end -->/{skip=0; next}
      /^```/{in_code = !in_code; next}
      !skip && in_code
    ' ~/.claude/skills/orchestrate-clc/SKILL.md \
      | grep -nE 'subagent_type[[:space:]]*[:=][[:space:]]*"codex:|command[[:space:]]+-v[[:space:]]+codex' \
      | tee /dev/stderr \
      | (! grep -q .)
    ```
    Expected exit code 0 (no real assignments or probes outside the prohibition block, considering only fenced code blocks).

    A broader **advisory grep** (with manual review of matches) can be run for documentation sanity:
    ```bash
    awk '/<!-- no-codex:prohibition-block-start -->/{skip=1; next} \
         /<!-- no-codex:prohibition-block-end -->/{skip=0; next} \
         !skip' ~/.claude/skills/orchestrate-clc/SKILL.md \
      | grep -nE 'codex:|command -v codex|"codex'
    ```
    Each line of output must be one of: a subagent prompt instructing abort on `codex:*`, a durable-contract sentence naming the locked-out path, or a verification command that includes `codex:` in its own pattern. Any other match is a regression.

    b. **Transitive audit** (chained skills' bodies; matches inside `plan-review` SKILL.md body that describe its default Codex+Claude mode are EXPECTED because the orchestrator forces `claude-only`; matches in any **agent file**, in **deep-review**, **handoff**, **to-issues**, or **GSD executor** are blockers):
    ```bash
    grep -rnE 'codex:|subagent_type.*codex|command -v codex' \
      ~/.claude/skills/plan-review-clc/agents/ \
      ~/.claude/sandbox/skills/gsd/ \
      ~/.claude/sandbox/skills/deep-review/ \
      ~/.agents/skills/handoff/ \
      ~/.agents/skills/to-issues/ \
      2>/dev/null
    ```
    Expected: zero matches across all listed paths. Any match is a blocker.

    c. **Name-collision audit**: probe all three skill roots:
    ```bash
    find ~/.claude/skills ~/.claude/sandbox/skills ~/.agents/skills \
      -maxdepth 2 -type d -name "plan-review-clc" 2>/dev/null
    ```
    Expected: exactly one match at `~/.claude/skills/plan-review-clc`. If more than one bare `plan-review/` directory appears, verify they are byte-identical duplicates (`diff -r`) — if they are, the harness resolves to one deterministically and the collision is benign. If they differ, alias the orchestrator's invocation to the canonical path or rename one.

    d. **Date and reproduce**: each audit is dated in a comment at the top of the orchestrator's SKILL.md when last run. Format: `<!-- no-codex-audit: YYYY-MM-DD -->`. Current value: see line 1.
