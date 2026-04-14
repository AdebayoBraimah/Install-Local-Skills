---
name: plan-review
description: |
  Two-reviewer plan quality assurance loop. Use when the user invokes /plan-review,
  asks for a plan review, wants independent review of a plan, or wants to validate
  a plan before execution. Routes the plan through parallel Claude Code and Codex
  reviewers, then iteratively corrects until all MEDIUM+ issues are resolved.
version: 1.0.0
---

# Plan Review

Automated two-reviewer plan QA loop. Runs independent Claude Code and Codex reviews in parallel, then corrects the plan iteratively until all MEDIUM+ issues are resolved or the iteration cap is reached.

## Invocation

- `/plan-review` — reviews the active plan (must be in plan mode)
- `/plan-review path/to/plan.md` — reviews the plan at the given file path

## Step 0: Locate the Plan

Determine the plan source in this order:

1. **Active plan mode**: If the session is in plan mode, the active plan is available in context. Write this content to a working file.
2. **File path argument**: If an argument was provided (e.g., `/plan-review docs/my-plan.md`), read that file.
3. **Both present**: Prefer the active plan; ignore the argument.
4. **Neither present**: Print usage instructions and stop:
   > Usage: `/plan-review [path/to/plan.md]`
   > Either be in plan mode or provide a path to a plan file.

Store the resolved plan content and its source path (the original plan file path, or a working file if from plan mode). This is the **original plan file** that will accumulate review feedback across rounds.

## Step 1: Review Loop

Set `round = 1` and `max_rounds = 5`.

### For each round:

#### 1a. Snapshot

Copy the current original plan file to two temporary files:
- `/tmp/plan-review-claude-r<round>.md`
- `/tmp/plan-review-codex-r<round>.md`

Use Bash:
```bash
cp "<original_plan_path>" "/tmp/plan-review-claude-r<round>.md"
cp "<original_plan_path>" "/tmp/plan-review-codex-r<round>.md"
```

#### 1b. Parallel Review

Spawn BOTH reviewers simultaneously in a single message (two Agent tool calls):

**Claude Code sub-agent:**
```
Agent({
  description: "Claude plan review round <round>",
  prompt: "You are a plan reviewer. Read the instructions in agents/claude-reviewer.md (located at ~/.claude/skills/plan-review/agents/claude-reviewer.md), then review the plan at /tmp/plan-review-claude-r<round>.md following those instructions exactly. Append your review to the end of that file.",
  mode: "auto"
})
```

**Codex reviewer:**
```
Agent({
  description: "Codex plan review round <round>",
  subagent_type: "codex:codex-rescue",
  prompt: "You are a plan reviewer. Read the instructions in agents/codex-reviewer.md (located at ~/.claude/skills/plan-review/agents/codex-reviewer.md), then review the plan at /tmp/plan-review-codex-r<round>.md following those instructions exactly. Append your review to the end of that file."
})
```

IMPORTANT: Both agents MUST be spawned in the same message to run in parallel.

#### 1c. Merge Reviews

After both reviewers complete:

1. Read `/tmp/plan-review-claude-r<round>.md` — extract everything after the original plan content (the appended review section).
2. Read `/tmp/plan-review-codex-r<round>.md` — extract everything after the original plan content (the appended review section).
3. Append both reviews to the **original plan file** with delimited headers:

```markdown

---

## Claude Review — Round <round>

<extracted claude feedback>

## Codex Review — Round <round>

<extracted codex feedback>
```

Use the Edit tool to append to the original plan file.

#### 1d. Correct the Plan

Now act as the corrector. Read the original plan file (which now has the review feedback appended at the bottom).

Address the issues following these rules:

- **Thirdparty review of the plan was performed. The assessment of the plan is located at the bottom of the plan. Address the concerns/issues, and make the corresponding edits to the plan as advised.**
- **Contradiction resolution:**
  - If both reviewers raise the same issue: fix it.
  - If reviewers contradict on a CRITICAL or HIGH issue: escalate to the user. Present both positions using AskUserQuestion and let the user decide.
  - If reviewers contradict on a MEDIUM or LOW issue: defer to the Codex recommendation. Add a note: `[Deferred to Codex over Claude: <brief reason>]`.
- After addressing each issue, strike it through or remove it from the review sections.
- If an issue cannot be fully resolved (e.g., requires architectural change outside plan scope), annotate it as `[UNRESOLVED]` and leave it in place.

#### 1e. Convergence Check

After corrections are complete, check the review sections for any remaining `[UNRESOLVED]` issues at MEDIUM severity or above.

- **No `[UNRESOLVED]` MEDIUM+ issues remain**: The plan is clean. Proceed to Step 2 (Cleanup).
- **`[UNRESOLVED]` MEDIUM+ issues remain AND round < max_rounds**: Increment `round` and go back to Step 1a.
- **`[UNRESOLVED]` MEDIUM+ issues remain AND round == max_rounds**: Proceed to Step 2 (Cap Hit).

## Step 2: Exit and Cleanup

### If plan is clean (converged):

Report to the user:
> Plan review complete. All MEDIUM+ issues resolved after **<round>** round(s).

### If cap was hit:

Present remaining unresolved issues to the user:
> Plan review reached the iteration cap (**<max_rounds>** rounds). The following MEDIUM+ issues remain unresolved:
> - <list of unresolved issues>
>
> Would you like to extend the review for more rounds?

If the user chooses to extend, reset `max_rounds += 5` and continue from Step 1a.

### Cleanup (always):

Delete all temporary files:
```bash
rm -f /tmp/plan-review-claude-r*.md /tmp/plan-review-codex-r*.md
```

## Scope Guardrails

- This skill does NOT execute the plan. It only reviews and corrects it.
- Code review by the reviewers is permissible if and only if it is also necessary for the plan review.
- No persistent state across separate invocations. Each `/plan-review` call is self-contained.
