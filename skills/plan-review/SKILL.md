---
name: plan-review
description: |
  Two-reviewer plan quality assurance loop. Use when the user invokes /plan-review,
  asks for a plan review, wants independent review of a plan, or wants to validate
  a plan before execution. Default mode dispatches one Claude reviewer and one Codex
  reviewer in parallel; falls back to a Claude-only spec + execution split when
  Codex is unavailable, or when the user passes the `claude-only` keyword (useful on
  HPC SLURM nodes without Codex). Iteratively corrects the plan until all MEDIUM+
  issues are resolved.
version: 1.1.0
---

# Plan Review

Automated two-reviewer plan QA loop. Dispatches independent reviewers in parallel (or sequentially), then corrects the plan iteratively until all MEDIUM+ issues are resolved or the iteration cap is reached.

## Invocation

- `/plan-review` — review the active plan in the default mode (parallel)
- `/plan-review path/to/plan.md` — review the given file in default mode (parallel)
- `/plan-review sequential` — sequential dispatch (first reviewer completes before the second starts)
- `/plan-review claude-only` — force fallback mode (two Claude Agents, spec + exec split)
- `/plan-review claude-only sequential` — fallback mode, sequential
- `/plan-review claude-only path/to/plan.md` — fallback mode on a file path
- `/plan-review path/to/plan.md sequential claude-only` — argument order does not matter

### Argument tokenizer

Every command-line argument is exactly one of:

- the literal token `sequential` → sets sequential mode (default is parallel)
- the literal token `claude-only` → forces fallback mode
- any other token → treated as a plan file path

Matching is whole-token equality, not substring. A path argument like `claude-only-fixes.md` does **not** trigger fallback mode — only an argument that is exactly the string `claude-only` does.

## Mode Selection (pre-flight, before Step 0)

1. If `claude-only` was passed as an argument, set `mode=fallback` and skip the auto-detection check.
2. Otherwise, run this Bash pre-flight (returns 0 → `default`, non-zero → `fallback`):

   ```bash
   command -v codex >/dev/null 2>&1 \
     && [ -f "${HOME}/.claude/plugins/installed_plugins.json" ] \
     && grep -q '"codex' "${HOME}/.claude/plugins/installed_plugins.json"
   ```

   On non-zero, announce: `Codex unavailable; running in claude-only mode.`
3. Once `mode` is set, it stays fixed for the entire `/plan-review` invocation. There is no mid-run mode-switch.

Notes on the probe:

- The Claude plugin layout has a single top-level manifest at `~/.claude/plugins/installed_plugins.json` plus `marketplaces/` and `cache/` subdirectories. There is no `~/.claude/plugins/*/plugin.json` glob to match.
- The grep pattern `'"codex'` matches any plugin id starting with `"codex` (e.g., `"codex@openai-codex"`). Tighten to `'"codex@'` if a future non-codex plugin starts with that substring.
- If `installed_plugins.json` schema or the codex plugin id changes, this probe will need to be updated.

### Mode summary

- **`mode=default`** (Claude+Codex): one Claude Agent (general checklist via `agents/claude-reviewer.md`) + one Codex Agent (general checklist via `agents/codex-reviewer.md`).
- **`mode=fallback`** (claude-only): two Claude Agents — one with `agents/plan-reviewer-spec.md` (spec-alignment checklist), one with `agents/plan-reviewer-exec.md` (execution-quality checklist). Used on systems without Codex (e.g., HPC SLURM) or whenever the user passes `claude-only`.

### Path expansion at dispatch time

The Agent spawn-prompt path strings below contain literal `${HOME}/...`. The receiving subagent's Read tool does **not** expand `${HOME}` or `~`. Resolve `${HOME}` to an absolute path **before** composing the Agent prompt:

```bash
# Run this in Bash before constructing each Agent prompt
agent_dir="${HOME}/.claude/skills/plan-review/agents"
echo "$agent_dir"   # use the resolved absolute path in the prompt
```

Pass the resolved string into the Agent prompt — do **not** pass the unresolved literal `${HOME}` text.

## Step 0: Locate the Plan

Determine the plan source in this order:

1. **Active plan mode**: If the session is in plan mode, the active plan is available in context. Write this content to a working file.
2. **File path argument**: If a path argument was provided (per the tokenizer above), read that file.
3. **Both present**: Prefer the active plan; ignore the argument.
4. **Neither present**: Print usage instructions and stop:
   > Usage: `/plan-review [path/to/plan.md] [sequential] [claude-only]`
   > Either be in plan mode or provide a path to a plan file.

Store the resolved plan content and its source path. This is the **original plan file** that will accumulate review feedback across rounds.

## Step 1: Review Loop

Set `round = 1` and `max_rounds = 5`.

### For each round:

#### 1a. Snapshot

Branch the temp filenames by `mode`:

```bash
if [ "$mode" = "default" ]; then
  cp "<original_plan_path>" "/tmp/plan-review-claude-r<round>.md"
  cp "<original_plan_path>" "/tmp/plan-review-codex-r<round>.md"
else
  cp "<original_plan_path>" "/tmp/plan-review-spec-r<round>.md"
  cp "<original_plan_path>" "/tmp/plan-review-exec-r<round>.md"
fi
```

Pre-resolve the agent directory once per round for use in spawn prompts:

```bash
agent_dir="${HOME}/.claude/skills/plan-review/agents"
```

#### 1b. Dispatch Reviews

Dispatch differs by `mode`. Within each mode, parallel vs sequential is selected by whether the `sequential` keyword was passed.

### Default mode (Claude + Codex)

##### Parallel (default within default mode)

Spawn BOTH reviewers simultaneously in a single message (two Agent tool calls). Substitute `<agent_dir>` with the resolved Bash variable (e.g., `/Users/<user>/.claude/skills/plan-review/agents`).

**Claude Code sub-agent:**
```
Agent({
  description: "Claude plan review round <round>",
  prompt: "You are a plan reviewer. Read the instructions in <agent_dir>/claude-reviewer.md, then review the plan at /tmp/plan-review-claude-r<round>.md following those instructions exactly. Append your review to the end of that file.",
  mode: "auto"
})
```

**Codex reviewer:**
```
Agent({
  description: "Codex plan review round <round>",
  subagent_type: "codex:codex-rescue",
  prompt: "You are a plan reviewer. Read the instructions in <agent_dir>/codex-reviewer.md, then review the plan at /tmp/plan-review-codex-r<round>.md following those instructions exactly. Append your review to the end of that file."
})
```

IMPORTANT: Both agents MUST be spawned in the same message to run in parallel.

##### Sequential

Spawn the Claude reviewer first; wait for completion; then spawn the Codex reviewer. Each reviewer works on its own snapshot. The Codex reviewer does **not** see Claude's output.

### Fallback mode (`claude-only`)

##### Parallel (default within fallback mode)

Spawn BOTH reviewers simultaneously in a single message (two Claude Agent tool calls).

**Spec reviewer:**
```
Agent({
  description: "Spec plan review round <round>",
  prompt: "You are a plan reviewer. Read the instructions in <agent_dir>/plan-reviewer-spec.md, then review the plan at /tmp/plan-review-spec-r<round>.md following those instructions exactly. Append your review to the end of that file.",
  mode: "auto"
})
```

**Execution reviewer:**
```
Agent({
  description: "Execution plan review round <round>",
  prompt: "You are a plan reviewer. Read the instructions in <agent_dir>/plan-reviewer-exec.md, then review the plan at /tmp/plan-review-exec-r<round>.md following those instructions exactly. Append your review to the end of that file.",
  mode: "auto"
})
```

IMPORTANT: Both agents MUST be spawned in the same message to run in parallel.

##### Sequential

Spawn the spec reviewer first; wait for completion; then spawn the exec reviewer. Each reviewer works on its own snapshot. The exec reviewer does **not** see the spec reviewer's output.

#### 1c. Merge Reviews

After both reviewers complete, read each snapshot, extract the appended review section (everything after the original plan content), and append both to the **original plan file** with delimited headers. Branch the headers by `mode`:

**Default mode:**
```markdown

---

## Claude Review — Round <round>

<extracted Claude feedback>

## Codex Review — Round <round>

<extracted Codex feedback>
```

**Fallback mode:**
```markdown

---

## Spec Review — Round <round>

<extracted spec feedback>

## Execution Review — Round <round>

<extracted exec feedback>
```

Use the Edit tool to append.

#### 1d. Correct the Plan

Act as the corrector. Read the original plan file (which now has the review feedback appended at the bottom). Address the issues following these rules:

- **Third-party review of the plan was performed. The assessment is at the bottom of the plan. Address the concerns/issues and make the corresponding edits as advised.**
- **Contradiction resolution (branches by mode):**
  - If both reviewers raise the same issue: fix it.
  - If reviewers contradict on a CRITICAL or HIGH issue: escalate to the user via AskUserQuestion and let the user decide.
  - If reviewers contradict on a MEDIUM or LOW issue:
    - **Default mode**: defer to the Codex recommendation. Add a note: `[Deferred to Codex over Claude: <brief reason>]`.
    - **Fallback mode**: defer to the execution reviewer. Add a note: `[Deferred to execution reviewer: <brief reason>]`.
- After addressing each issue, strike it through or remove it from the review sections.
- If an issue cannot be fully resolved (requires an architectural change outside plan scope), annotate as `[UNRESOLVED]` and leave it in place.

#### 1e. Convergence Check

Inspect review sections for remaining `[UNRESOLVED]` MEDIUM+ issues.

- **None remain**: proceed to Step 2 (Cleanup).
- **Remain AND `round < max_rounds`**: increment `round` and go back to Step 1a.
- **Remain AND `round == max_rounds`**: proceed to Step 2 (Cap Hit).

## Step 2: Exit and Cleanup

### If plan is clean (converged):

Report:
> Plan review complete. All MEDIUM+ issues resolved after **<round>** round(s).

### If cap was hit:

Present remaining unresolved issues:
> Plan review reached the iteration cap (**<max_rounds>** rounds). The following MEDIUM+ issues remain unresolved:
> - <list>
>
> Would you like to extend the review for more rounds?

If the user extends, reset `max_rounds += 5` and continue from Step 1a.

### Cleanup (always)

Delete temp files for both glob sets unconditionally so leftover files from prior runs are also cleared:

```bash
rm -f /tmp/plan-review-claude-r*.md /tmp/plan-review-codex-r*.md \
      /tmp/plan-review-spec-r*.md /tmp/plan-review-exec-r*.md
```

## Scope Guardrails

- This skill does NOT execute the plan. It only reviews and corrects it.
- Code review by the reviewers is permissible if and only if it is also necessary for the plan review.
- No persistent state across separate invocations. Each `/plan-review` call is self-contained.
- Mode is fixed at pre-flight; no mid-run switching.
