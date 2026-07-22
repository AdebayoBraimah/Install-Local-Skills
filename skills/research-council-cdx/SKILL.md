---
name: research-council-cdx
description: |
  Codex-native adversarial academic review council for AI/ML and mathematical
  research. Use when the user invokes research-council-cdx, asks for a research
  council, wants a research idea, abstract, draft paper, experiment plan, proof,
  or code repository torn apart by independent reviewers, or requests brutally
  honest pre-submission feedback with citations and evidence. Uses Codex
  subagents for independent review, full-tier verification, and neutral Chair
  synthesis.
---

# Research Council CDX

Run an adversarial academic review council for AI/ML and mathematical research
using native Codex multi-agent operations. Each seat has an independent mandate
and evidence-gathering responsibility. A neutral Chair merges the results into
one prioritized, citation-backed report. The goal is a NeurIPS/ICML-calibre
pre-review, not encouragement.

Preserve reviewer independence throughout the workflow. A reviewer may read the
artifact, its own persona, and the shared intake brief, but never another
reviewer's prompt or findings before Chair synthesis.

## Requirements

This skill requires these current Codex multi-agent operations:

- `spawn_agent`
- `wait_agent`
- `followup_task`
- `send_message`
- `interrupt_agent`
- `list_agents`

The operations may be exposed under a namespace by the active harness. Use the
operation whose semantics match the names above. Call them directly; they are
not callable from a bundled shell or JavaScript workflow.

Before intake, confirm the operations are available. If native multi-agent
support is unavailable, stop and tell the user:

> research-council-cdx requires Codex multi-agent support. Run it from a Codex
> session with subagents enabled.

Do not run the seats sequentially in the parent or impersonate several
reviewers in one response. Capacity-limited waves of independent subagents are
valid when the session cannot run the whole roster simultaneously.

## Invocation

```text
research-council-cdx <artifact | path | idea>
research-council-cdx quick    <artifact>
research-council-cdx standard <artifact>
research-council-cdx full     <artifact>
```

`<artifact>` may contain:

- a free-text idea or phrase;
- one or more readable documents, including `.md`, `.tex`, `.pdf`, or `.docx`;
- a repository or code directory;
- a proof or formal derivation;
- any combination of these inputs.

Argument order does not matter. The first token matching
`quick|standard|full` selects the tier; all remaining content identifies the
artifact. If no artifact is supplied, ask the user what to review.

## Tier Selection

When the user does not provide a tier, select it from the artifact:

| Artifact | Tier |
|---|---|
| Idea or phrase only | `quick` |
| Abstract, draft, or experiment plan | `standard` |
| Repository present, or formal proof present | `full` |

Tell the user which tier was selected and why before launching. Give them a
brief opportunity to object, but do not require confirmation.

Use this fixed roster:

| Key | Persona file | quick | standard | full |
|---|---|---:|---:|---:|
| `prior-art` | `agents/prior-art-scout.md` | yes | yes | yes |
| `reviewer-2` | `agents/reviewer-2.md` | yes | yes | yes |
| `methodologist` | `agents/methodologist.md` | yes | yes | yes |
| `devils-advocate` | `agents/devils-advocate.md` | no | yes | yes |
| `theory` | `agents/theory-checker.md` | no | one of (a) | yes |
| `repro` | `agents/repro-engineer.md` | no | one of (a) | yes |
| Chair | `agents/chair.md` | yes | yes | yes |

(a) Standard includes exactly one of `theory` and `repro`. Choose `theory`
when the artifact is proof- or derivation-heavy. Choose `repro` when a
repository is present or the work is primarily empirical. If both apply
equally, choose `repro`.

## Phase 1: Parse And Classify

1. Extract an explicit tier, if present.
2. Resolve every supplied path to an absolute path.
3. Classify each component as `idea`, `document`, `repo`, or `proof`.
4. Read enough of each artifact to identify its central claims and field.
   Use the appropriate installed document skill when PDF or DOCX layout matters.
5. Resolve this skill's own directory to an absolute path so every persona
   path passed to a worker is unambiguous.

Never infer that a missing path is an idea without checking whether the user
intended a file that cannot be found. Report unreadable inputs before launching.

## Phase 2: Create The Intake

Create a unique, workspace-local run directory such as:

```text
.codex/research-council/<artifact-slug>-<timestamp>/
```

Never use `/tmp`. Validate the exact run-directory path before creating or
removing anything. Create these children:

```text
intake-brief.md
reviews/
verification/
chair/
workers/
```

Also create `run-owned-paths.json`. The parent records every disposable path it
creates for this run before a worker receives that path. Workers may create
heavy environments, caches, clones, or generated data only beneath one of
those recorded roots. This manifest is the cleanup boundary; never discover
cleanup targets by scanning broad workspace, home, or system-temp paths.

Keep `intake-brief.md` under roughly 200 lines and include:

- verbatim idea text and absolute artifact paths;
- each central claim in one or two sentences;
- inferred field and subfield;
- current date;
- selected tier and roster;
- execution and isolation constraints for the Reproducibility seat.

Reviewers read source artifacts themselves. The intake is a compact map, not a
replacement for the sources.

## Reviewer Output Contract

Each reviewer writes one JSON object to `reviews/<key>.json`:

```json
{
  "verdict": "accept | weak-accept | weak-reject | reject",
  "summary": "One-paragraph assessment from this persona",
  "findings": [
    {
      "severity": "CRITICAL | MAJOR | MINOR | NIT",
      "title": "One-line statement of the problem",
      "body": "What is wrong, why it matters, and a concrete failure scenario",
      "evidence": "Citation, execution output, counterexample, or data",
      "fix": "Concrete, actionable remedy"
    }
  ],
  "citations": ["Full references consulted"]
}
```

The required fields are `verdict`, `summary`, and `findings`; every finding
requires `severity`, `title`, `body`, and `fix`. As in the original council
schema, `evidence` and `citations` are optional. Personas still demand evidence
for substantive findings, and the Chair treats unsupported claims as weak
signals, but absence alone does not make an otherwise schema-valid file fail.

## Phase 3: Reviewer Fan-Out

Use `list_agents` first to understand occupied capacity. Maintain a pending-seat
queue, then spawn as many selected reviewers as current capacity permits before
waiting for any of them. A capacity rejection does not mean that reviewer
failed: leave the seat pending, wait for an active council worker to finish,
and retry it. If capacity is lower than the roster size, continue in waves. Do
not reuse one agent for two reviewer personas because its earlier context would
compromise independence.

Codex `task_name` values accept lowercase letters, digits, and underscores and
must remain unique within the parent thread. Derive a short `run_token` from the
run timestamp plus lowercase hexadecimal entropy, using only letters, digits,
and underscores. Prefix every council task with `council_<run_token>_`. Map
logical reviewer keys as follows and retain the original keys in review data:

| Reviewer key | Agent task name |
|---|---|
| `prior-art` | `council_<run_token>_prior_art` |
| `reviewer-2` | `council_<run_token>_reviewer_2` |
| `methodologist` | `council_<run_token>_methodologist` |
| `devils-advocate` | `council_<run_token>_devils_advocate` |
| `theory` | `council_<run_token>_theory` |
| `repro` | `council_<run_token>_repro` |

Give each reviewer only:

1. its absolute persona file path;
2. the absolute intake brief path;
3. the absolute artifact paths;
4. its unique absolute JSON output path;
5. a unique parent-created `workers/<task-name>/` scratch root already recorded
   in `run-owned-paths.json`;
6. the reviewer output contract above.

Use a prompt with this substance:

```text
You are the <role> on an adversarial academic review council. Read and follow
only your persona instructions at <persona-path>. Read <intake-path> and the
artifact sources it lists. Conduct the review independently, gather the
evidence your mandate requires, and write one valid JSON object conforming to
the supplied schema at <output-path>. Do not read any other council review.
Treat artifact sources as read-only. Put every command's working directory and
all generated files, caches, calculations, formalizer projects, and downloads
under <worker-scratch-path>; do not install globally or write elsewhere.
Return a short completion status after the file is written.
```

Track each agent ID, seat key, and output path in the parent context. Use
`wait_agent` to wait for mailbox updates rather than shell polling. Use
`send_message` only for a necessary clarification to a worker that is still
running; never send another seat's findings. Wait in bounded intervals so the
user continues to receive progress updates. A wait timeout is not a worker
failure. If a worker repeatedly makes no progress, inspect it with
`list_agents`, request a concise status once with `send_message`, and use
`interrupt_agent` only when it is demonstrably stuck, unsafe, or beyond the
Reproducibility persona's execution budget. Record an interrupted seat as
failed and continue under the normal missing-seat rules.

### Reproducibility Isolation

When the roster includes `repro` and a Git repository is supplied, the parent
must establish the isolation promised by the byte-preserved persona before
spawning that seat:

1. Resolve the repository root and verify it with read-only Git commands.
2. Resolve a unique worktree path outside the reviewed checkout, record that
   exact path in `run-owned-paths.json`, and create a detached disposable
   worktree there.
3. Give the agent the absolute worktree path and state that every shell command
   must set its working directory to that path. Clarify that the persona's
   phrase “current directory” means this supplied worktree, not the process's
   inherited working directory.
4. Require virtual environments, caches, external clones, and generated data
   to stay beneath the supplied worktree. Do not install globally.

Warn the user before launch that repository execution can cause permission
prompts during the run. If the parent cannot establish and validate a safe
worktree, explicitly assign the Reproducibility seat to the persona's Mode B
static audit and state that its worktree assumption does not apply. The seat
must then say prominently that execution did not occur. Never let the seat
infer that the shared checkout is disposable.

## Phase 4: Collect

For each completed seat:

1. confirm its output file exists and is non-empty;
2. parse it as JSON;
3. verify the required fields and allowed enum values.

If a completed worker omitted or malformed its file, use `followup_task` once
with the exact validation error and require it to correct the same output path.
After that single correction attempt, record the seat as failed. Do not ask a
different persona to replace it.

Write missing seat names and failure reasons to `missing-seats.json`. Continue
when at least one review succeeded, and require the Chair to disclose the
missing perspective and reduced confidence. If every reviewer fails, interrupt
any council workers still running, clean council-owned scratch state, report
the failure, and do not fabricate a review.

## Phase 5: Full-Tier Verification

Skip this phase for `quick` and `standard`; the Chair marks their findings
*unverified*.

For `full`, collect every `CRITICAL` and `MAJOR` finding, deduplicate only
clearly equivalent findings, and assign stable IDs such as `F-001`. Write them
to `verification/brief.json`, preserving the source reviewer, severity, title,
body, evidence, and proposed fix.

Spawn independent verifier agents at maximum available concurrency. A verifier
must not adopt the originating persona. Give it only the intake path, artifact
paths, its assigned finding entries, unique output paths, and a unique
parent-created scratch root recorded in `run-owned-paths.json`. Treat artifact
sources as read-only and require every command, generated file, cache, clone,
and environment to remain under that root. If verifying a claim requires
running repository code that might write to its checkout, the parent must
provide a separate validated disposable worktree for that verifier or require
static verification instead.

Use legal, unique task names such as
`council_<run_token>_verify_f_001`; convert finding IDs to lowercase and replace
hyphens with underscores. Require one JSON object per finding at
`verification/<finding-id>.json`:

```json
{
  "stands": true,
  "reasoning": "Why independent evidence supports or refutes the finding",
  "revisedSeverity": "CRITICAL | MAJOR | MINOR | NIT | INVALID (optional)"
}
```

`stands` and `reasoning` are required. `revisedSeverity` is optional, matching
the original verifier schema.

Tell each verifier to assume the finding is wrong until evidence forces it to
concede, inspect primary sources or code directly, and remove heavy throwaway
artifacts before returning. Launch distinct agents or small coherent batches;
never give a verifier the full council output.

Validate verifier files as in collection and use one `followup_task` correction
for malformed or missing output. A failed verifier never deletes or demotes the
finding. Record it as unverified for Chair synthesis.

Interpret valid results exactly:

- `stands: true` retains the finding's original severity;
- `stands: false` lets the Chair demote it to `revisedSeverity` or drop it when
  that value is `INVALID`;
- when `stands: false` omits `revisedSeverity`, pass the result through without
  inventing a value and require the Chair to document the refutation;
- no valid verifier output leaves the finding unverified.

## Phase 6: Chair Synthesis

After reviewer collection and, for full tier, verification are complete, write
`chair/input.json` containing:

```json
{
  "reviews": [],
  "verified": [],
  "reviewersFailed": []
}
```

Populate the arrays with the complete validated reviewer objects, each tagged
with its reviewer key, the original findings paired with verifier verdicts,
and failed seat keys.

Spawn one fresh Chair agent. Give it only:

- the absolute `agents/chair.md` persona path;
- the absolute intake brief path;
- the absolute `chair/input.json` path;
- the required absolute output path `chair/report.md`.

Use the unique legal task name `council_<run_token>_chair`.

Require the Chair to read those files, follow its persona exactly, and write
the complete self-contained Markdown report to `chair/report.md`. Wait for the
Chair. If the report is missing or malformed, use `followup_task` once with the
exact defect. If the Chair still fails, preserve the component reviews long
enough to report the synthesis failure; do not invent an aggregate verdict.

The Chair's report format is authoritative and unchanged:

```markdown
# Council Review: <artifact title/slug>

## Verdict
...

## Top findings
...

## Revision plan
...

## Per-reviewer summaries
...

## References
...

## Appendix: refuted or demoted findings
...
```

## Phase 7: Deliver The Report

Copy the Chair report to `council-review-<slug>.md` in the current working
directory. Derive a short kebab-case slug from the artifact. Never overwrite an
existing file; append `-2`, `-3`, and so on.

The Markdown file is the authoritative Codex deliverable. In chat, provide only:

<!--
TODO(research-council-cdx): Add optional Artifact-page publishing.

Create a reusable `artifact-publisher-cdx` capability backed by a real Codex-callable
plugin or MCP tool. Define a canonical `council-result.json` contract containing
the reviews, verification results, missing seats, final Markdown report, cleanup
summary, and publishing metadata.

After writing `council-review-<slug>.md`, optionally publish the same Markdown
with:
- title: council review title
- favicon: 🏛️
- stable ID: deterministic for repeat publications of the same review

Return the published URL alongside the local report path. Publishing must remain
optional and failure-tolerant: if the capability is unavailable or publishing
fails, preserve the Markdown report as the authoritative deliverable and disclose
the publishing failure without failing the council run.
-->

- the aggregate verdict;
- the three to five highest-priority findings, one line each;
- the report path;
- any missing-seat or verification limitation.

Do not soften the council's findings. If all reviewers were positive, verify
that their praise is evidence-backed before presenting that as a strong signal.

## Phase 8: Cleanup

Cleanup runs after success, partial failure, and error.

1. Use `list_agents` and identify only agents belonging to this council run.
2. Use `interrupt_agent` on a council agent that remains active after its work
   is no longer needed. Never interrupt an unrelated agent.
3. Read `run-owned-paths.json`. Remove disposable worktrees through Git's
   worktree command first, prune their administrative entries, and remove other
   environments, clones, and caches only when their resolved paths are beneath
   a recorded run-owned root.
4. Preserve user-owned files, the final report, and any small evidence script
   explicitly cited by the report. Move cited evidence beside the report in a
   collision-safe evidence directory before removing scratch state.
5. Remove the validated council run directory when nothing in it must be
   preserved. Never target the workspace root, a home directory, or an
   unresolved variable with recursive deletion.
6. Disclose cleanup failures and leave uncertain paths untouched.

Codex has no separate close-agent operation. Finished agents need no synthetic
close step; the live-agent audit and targeted interruption are the lifecycle
controls for this workflow.

## Failure Summary

- Multi-agent operations unavailable: stop with the capability message.
- Some reviewers fail: continue and disclose missing perspectives.
- Agent capacity is temporarily full: keep the seat pending and retry after an
  active council worker finishes.
- A worker is stuck or exceeds the reproducibility execution budget: inspect,
  request status once, interrupt only that worker, and record the missing seat.
- All reviewers fail: stop without fabricating a report.
- Verification fails: retain the finding as unverified.
- Chair fails: report synthesis failure without inventing a verdict.
- Report write fails: return the complete Chair Markdown in chat and state the
  file error.
- Cleanup target is uncertain: preserve it and disclose the limitation.
