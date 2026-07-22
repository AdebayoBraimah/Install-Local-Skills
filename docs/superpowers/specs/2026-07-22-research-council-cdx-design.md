# Research Council CDX Design

## Goal

Add `research-council-cdx`, a Codex-native adaptation of
`research-council-clc` that preserves its quick, standard, and full review
tiers, seven reviewer personas, verification round, Chair synthesis, report
format, and cleanup behavior.

## Architecture

The skill will orchestrate Codex subagents directly from `SKILL.md`. It will
use `spawn_agent` to launch independent reviewers, `wait_agent` to collect
results, and `close_agent` after each phase. It will not copy the Claude
Workflow JavaScript because scripts cannot invoke Codex's native subagent
tools.

Persona instructions will remain separate files under `agents/`. Each reviewer
will receive only its persona path, the intake brief path, and an output path.
This preserves reviewer independence and keeps prompts compact.

## Workflow

1. Parse and classify ideas, documents, repositories, and proofs using the
   existing tier-selection rules.
2. Write a concise intake brief in a workspace-local scratch directory.
3. Spawn the selected reviewer roster concurrently. The standard tier selects
   either the theory or reproducibility seat using the existing rules.
4. Collect each review in a separate Markdown file. Continue when an individual
   reviewer fails, but stop if all reviewers fail.
5. For the full tier, extract CRITICAL and MAJOR findings into a verification
   brief and dispatch independent verification subagents. Verification results
   must confirm, weaken, or reject each targeted finding with evidence.
6. Spawn a Chair subagent with the intake brief, reviewer outputs, and any
   verification outputs. The Chair produces the final prioritized,
   citation-backed report.
7. Write `council-review-<slug>.md` in the current working directory, using a
   numeric suffix when needed.
8. Clean council scratch files and close every spawned agent. Preserve the
   final report and any evidence scripts explicitly cited by it.

When the reproducibility seat receives a Git repository, it will work in an
isolated Codex worktree when the harness supports agent isolation. If isolation
is unavailable, it must avoid destructive commands and modifications to the
user's checkout, report the limitation, and restrict itself to safe inspection
and commands.

## Behavioral Parity

The adaptation will retain the original invocation forms, automatic tier
selection, reviewer roster, adversarial mandates, missing-reviewer disclosure,
evidence requirements, aggregate verdict, and concise chat handoff. Claude-only
requirements, Workflow calls, and Artifact-page publishing will be replaced by
Codex-native orchestration and the Markdown report deliverable.

## Repository Integration

Create `skills/research-council-cdx/` with `SKILL.md` and the seven adapted
persona files. Add it to `AGENTS_COPY_SKILLS` so it is always installed in
`~/.agents/skills/`. Add the corresponding Codex literature/research entry and
source-of-truth note to `README.md`.

No standalone orchestration script or extra user-facing documentation will be
added.

## Failure Handling

- If subagent tools are unavailable, stop with a Codex capability message.
- If one or more reviewers fail, continue and require the Chair to identify the
  missing perspectives.
- If all reviewers fail, stop without fabricating a report.
- If verification fails, retain the challenged findings but mark them
  unverified in the Chair input and final report.
- If report writing fails, return the Chair output in chat and report the file
  error.

## Validation

- Run the skill validator against `skills/research-council-cdx/`.
- Check that every persona and path referenced by `SKILL.md` exists.
- Run `bash -n install-skills.sh` and verify the fixed-stride registry remains
  valid.
- Search for stale Claude Workflow and Artifact references in the CDX skill.
- Forward-test a representative idea review using Codex subagents if the test
  can run without external side effects.
