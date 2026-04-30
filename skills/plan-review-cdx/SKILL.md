---
name: plan-review-cdx
description: |
  Two-reviewer Codex plan quality assurance loop. Use when the user asks to
  review, validate, QA, or correct an implementation plan with independent
  reviewers before execution. Dispatches two independent Codex reviewers, then
  iteratively corrects the plan until all MEDIUM+ issues are resolved.
version: 1.0.0
---

# Plan Review CDX

Automated two-reviewer plan QA loop for Codex. Runs two independent Codex
reviewers, merges their feedback, corrects the plan, and repeats until all
MEDIUM+ issues are resolved or the iteration cap is reached.

This skill is a review-and-correction workflow only. It never executes the plan
being reviewed.

## Invocation

- `plan-review-cdx` - review the active plan in context.
- `plan-review-cdx path/to/plan.md` - review the plan at the given path.
- `plan-review-cdx sequential` - review the active plan sequentially.
- `plan-review-cdx sequential path/to/plan.md` - review the given plan sequentially.
- `plan-review-cdx path/to/plan.md sequential` - same; argument order does not matter.

Parallel mode is the default. Both reviewers run at the same time and do not see
each other's feedback.

Sequential mode runs the spec reviewer first, then the execution reviewer. Each
reviewer still receives a fresh snapshot of the same current plan, so the second
reviewer does not see the first review.

## Step 0: Locate the Plan

Determine the plan source in this order:

1. Active plan context: if the user has provided a plan in the conversation,
   write that content to a working file such as `/tmp/plan-review-cdx-active.md`.
2. File path argument: if an argument names a readable file, read that file.
3. Both present: prefer the active plan in context and ignore the path argument.
4. Neither present: print usage and stop:

```text
Usage: plan-review-cdx [path/to/plan.md] [sequential]
Either provide a plan in context or provide a path to a plan file.
```

The resolved file is the original plan file. It accumulates review feedback and
corrections across rounds.

## Step 1: Review Loop

Set:

```text
round = 1
max_rounds = 5
```

### For Each Round

#### 1a. Snapshot

Copy the current original plan file into two independent snapshot files:

```bash
cp "<original_plan_path>" "/tmp/plan-review-cdx-spec-r<round>.md"
cp "<original_plan_path>" "/tmp/plan-review-cdx-exec-r<round>.md"
```

#### 1b. Dispatch Reviews

This skill explicitly requires two independent reviewer subagents. When invoked,
the user request authorizes exactly these two reviewer subagents.

Use two Codex subagents:

- Spec reviewer: uses
  `${HOME}/.agents/skills/plan-review-cdx/agents/plan-reviewer-spec.md`
- Execution reviewer: uses
  `${HOME}/.agents/skills/plan-review-cdx/agents/plan-reviewer-exec.md`

When using Codex's agent tools, spawn both reviewers with `spawn_agent` before
calling `wait_agent` on either reviewer. Use fresh independent prompts for both
reviewers. Do not send either reviewer the other reviewer's output.

##### Parallel Mode

Dispatch both reviewers in parallel by spawning both agents first, then waiting
for both results. Give each reviewer only its own snapshot path and its own
reviewer instructions.

Spec reviewer prompt:

```text
You are a plan reviewer. Read the instructions in
${HOME}/.agents/skills/plan-review-cdx/agents/plan-reviewer-spec.md,
then review the plan at /tmp/plan-review-cdx-spec-r<round>.md following those
instructions exactly. Append your review to the end of that file if your file
edits are visible to the parent session. In all cases, return the exact review
section in your final response.
```

Execution reviewer prompt:

```text
You are a plan reviewer. Read the instructions in
${HOME}/.agents/skills/plan-review-cdx/agents/plan-reviewer-exec.md,
then review the plan at /tmp/plan-review-cdx-exec-r<round>.md following those
instructions exactly. Append your review to the end of that file if your file
edits are visible to the parent session. In all cases, return the exact review
section in your final response.
```

##### Sequential Mode

Run the spec reviewer first and wait for completion. Then run the execution
reviewer against its own fresh snapshot. The execution reviewer must not receive
the spec review output.

#### 1c. Merge Reviews

After both reviewers complete:

1. Read `/tmp/plan-review-cdx-spec-r<round>.md` and extract the appended review
   after the original snapshot content.
2. Read `/tmp/plan-review-cdx-exec-r<round>.md` and extract the appended review
   after the original snapshot content.
3. If a snapshot does not contain an appended review, use that reviewer
   subagent's final response as the review payload.
4. Append both reviews to the original plan file with delimited headers:

```markdown

---

## Spec Review - Round <round>

<spec reviewer feedback>

## Execution Review - Round <round>

<execution reviewer feedback>
```

#### 1d. Correct the Plan

Act as the corrector. Read the plan and the review feedback appended at the
bottom. Edit the original plan to address reviewer concerns.

Correction rules:

- Fix every duplicated issue raised by both reviewers.
- Fix every non-contradictory MEDIUM, HIGH, and CRITICAL issue.
- LOW issues are advisory unless they can be fixed without expanding scope.
- If reviewers contradict on a CRITICAL or HIGH issue, stop and ask the user to
  choose between the two positions.
- If reviewers contradict on a MEDIUM or LOW issue, defer to the execution
  reviewer and add a note in the review section:
  `[Deferred to execution reviewer: <brief reason>]`.
- After addressing an issue, strike it through or annotate it as resolved in the
  review section.
- If an issue cannot be fully resolved because it requires a decision outside
  the plan scope, annotate it as `[UNRESOLVED]` and leave it visible.

Do not execute the plan while correcting it. Only edit the plan document.

#### 1e. Convergence Check

Inspect review sections for unresolved MEDIUM+ issues.

- If no `[UNRESOLVED]` MEDIUM+ issues remain, proceed to cleanup and report
  success.
- If unresolved MEDIUM+ issues remain and `round < max_rounds`, increment
  `round` and repeat from Step 1a.
- If unresolved MEDIUM+ issues remain and `round == max_rounds`, report the
  remaining issues and ask the user whether to extend the cap by five rounds.

## Step 2: Exit and Cleanup

If converged, report:

```text
Plan review complete. All MEDIUM+ issues resolved after <round> round(s).
```

If the cap was hit, report:

```text
Plan review reached the iteration cap (<max_rounds> rounds). The following
MEDIUM+ issues remain unresolved:
- <issue>
```

Always clean up temp files:

```bash
rm -f /tmp/plan-review-cdx-spec-r*.md /tmp/plan-review-cdx-exec-r*.md
```

## Scope Guardrails

- Review and correct the plan only; never execute it.
- Code inspection is allowed only when needed to verify a plan assumption.
- Do not expand into general code review.
- Each invocation is self-contained. Do not preserve state across invocations.
- Keep the two reviewer outputs independent. Do not show either reviewer the
  other review before both have finished.
