---
name: research-council-cdx
description: |
  Codex-native adversarial academic review council for AI/ML and mathematical
  research. Use when the user invokes research-council-cdx, asks for a research
  council, wants an idea, paper, experiment plan, proof, or repository attacked
  by independent reviewers, or requests blunt pre-submission feedback with
  citations and evidence. Orchestrates parallel Codex subagents, optional
  full-tier verification, and neutral Chair synthesis.
---

# Research Council CDX

Run an adversarial academic review council using native Codex multi-agent
tools. Preserve reviewer independence: each seat has a fixed mandate, writes a
separate review, and does not see the other reviewers before Chair synthesis.

The required phase order is:

```text
parse -> intake -> reviewer fan-out -> collect -> full-tier verification -> chair -> report -> cleanup
```

## Requirements

Before starting, discover and confirm access to `spawn_agent`, `wait_agent`,
`send_input`, and `close_agent`. Tool names may be namespaced by the harness.
If native multi-agent tools are unavailable, stop and explain that
`research-council-cdx` requires Codex multi-agent support. Do not silently run
the seats sequentially or impersonate multiple reviewers in the parent.

Track every spawned agent ID. Close every agent after its output has been
collected or its failure has been recorded, including reviewers, verifiers,
and the Chair. Use `send_input` only to resolve a blocked agent or request a
missing output; never use it to coordinate reviewers or expose another seat's
work.

## Invocation And Tiers

```text
research-council-cdx <artifact | path | idea>
research-council-cdx quick    <artifact>
research-council-cdx standard <artifact>
research-council-cdx full     <artifact>
```

The first token matching `quick|standard|full` selects the tier; everything
else is the artifact, regardless of argument order. An artifact may be free
text, one or more readable document paths, a repository path, a proof, or a
combination. If no artifact is supplied, ask what to review.

When no tier is explicit, use:

| Artifact | Tier |
|---|---|
| Idea or phrase only | `quick` |
| Abstract, draft, or experiment plan | `standard` |
| Repository or formal proof present | `full` |

State the selected tier and reason before launching, allowing the user a brief
chance to object without requiring confirmation.

## 1. Parse

Classify each component as an `idea`, `document`, `repo`, or `proof`. Resolve
all source paths to absolute paths. Read enough of each source to identify its
central claims and field. Use appropriate document-reading tools for formats
such as PDF or DOCX.

Select reviewers from this fixed roster:

| Key | Persona | quick | standard | full |
|---|---|---:|---:|---:|
| `prior-art` | `agents/prior-art-scout.md` | yes | yes | yes |
| `reviewer-2` | `agents/reviewer-2.md` | yes | yes | yes |
| `methodologist` | `agents/methodologist.md` | yes | yes | yes |
| `devils-advocate` | `agents/devils-advocate.md` | no | yes | yes |
| `theory` | `agents/theory-checker.md` | no | one of (a) | yes |
| `repro` | `agents/repro-engineer.md` | no | one of (a) | yes |
| Chair | `agents/chair.md` | yes | yes | yes |

(a) Standard includes exactly one of `theory` and `repro`. Choose `theory`
for proof/derivation-heavy work and `repro` for a repository or primarily
empirical work. If both apply equally, choose `repro`.

## 2. Intake

Create a workspace-local scratch directory, never `/tmp`, such as
`.codex/research-council/<unique-run-id>/`. Keep it outside the reviewed repo
when the current workspace permits. Write `intake-brief.md` under 200 lines:

- verbatim idea text and absolute source paths;
- one or two sentences for each central claim;
- inferred field/subfield;
- current date;
- selected tier and roster;
- execution/isolation constraints relevant to the reproducibility seat.

Create `reviews/`, `verification/`, and `chair/` beneath the run directory.

All council outputs use Markdown. Each reviewer must produce:

```markdown
# <Seat> Review
## Verdict
<accept | weak-accept | weak-reject | reject>
## Summary
<concise assessment>
## Findings
### <CRITICAL | MAJOR | MINOR>: <title>
- Claim: <specific claim or location>
- Evidence: <citation, calculation, command output, or counterexample>
- Fix: <concrete corrective action>
- Confidence: <high | medium | low>
## Citations
<full references or "None">
```

## 3. Reviewer Fan-Out

Spawn every selected reviewer before waiting for any reviewer. Each reviewer
prompt may contain only:

1. its persona file path under this skill's `agents/` directory;
2. the absolute `intake-brief.md` path;
3. the absolute source paths from the intake;
4. its unique output path, `reviews/<key>.md`;
5. the common reviewer output schema above.

Tell each agent to read those files, follow only its persona mandate, conduct
the evidence gathering that mandate requires, write its review atomically to
the output path, and return a short completion status. Do not include another
reviewer's prompt, findings, or output path. For `repro`, request isolated
worktree execution when the harness supports it.

## 4. Collect

Wait for all reviewer agents, in batches if the tool requires it. A reviewer
succeeds only when its output file exists, is non-empty, follows the schema,
and contains evidence for substantive findings. Use `send_input` once when a
successful agent omitted or malformed its file; otherwise record the failure.
Close each reviewer after collecting or recording its result.

Continue when some seats fail. Record their names and failure reasons in
`missing-seats.md`, and require the Chair to disclose the missing perspectives
and reduced confidence. If every reviewer fails, close all agents, clean the
scratch directory, report the failure, and do not fabricate a council report.

## 5. Full-Tier Verification

Skip this phase for `quick` and `standard`. Their findings remain explicitly
`UNVERIFIED` in Chair synthesis.

For `full`, extract every `CRITICAL` and `MAJOR` finding into
`verification/brief.md`, assigning stable IDs such as `F-001`. Preserve the
original claim, evidence, severity, source reviewer, and proposed fix.

Spawn independent verification agents before waiting. Partition findings into
small coherent batches. Verifiers must not adopt the originating persona and
must independently inspect primary sources, calculations, code, or proof
steps. Give each verifier only the intake path, source paths, verification
brief entries assigned to it, and a unique output path. Require one result per
finding:

```markdown
### F-001: <CONFIRMED | WEAKENED | REJECTED | UNVERIFIED>
- Revised severity: <CRITICAL | MAJOR | MINOR | INVALID>
- Evidence: <independent evidence and source paths/citations>
- Rationale: <why the original finding does or does not stand>
```

`CONFIRMED` means independent evidence supports the finding; `WEAKENED` means
it stands at lower severity or narrower scope; `REJECTED` means evidence
refutes it; `UNVERIFIED` means the verifier could not reach a defensible
classification. Wait for all verifiers, retry a missing output once with
`send_input`, then close every verifier. Failed verification never deletes a
finding: mark it `UNVERIFIED` for the Chair.

## 6. Chair

After reviewer collection and full-tier verification are complete, spawn one
Chair agent. Give it only:

- `agents/chair.md`;
- the intake brief path;
- all successful reviewer output paths;
- verification output paths, when present;
- `missing-seats.md`, when present;
- the required final output path `chair/report.md`.

Require the Chair to apply verification verdicts, deduplicate findings,
resolve conflicts by evidence, disclose failed seats, and write a complete
self-contained report. Wait for it, use `send_input` once if the output file is
missing or malformed, collect its output, and close it. If the Chair fails,
report that failure without inventing synthesis; preserve reviewer outputs
long enough to summarize the failure.

## 7. Report

Copy the Chair report to `council-review-<slug>.md` in the current working
directory. Derive a short kebab-case slug from the artifact. Never overwrite:
use `-2`, `-3`, and so on when the name already exists.

If file writing fails, return the complete Chair output in chat and state the
file error. Otherwise chat contains only the aggregate verdict, the three to
five highest-priority findings (one line each), the report path, and any
missing-seat or verification limitations. Do not soften the report.

## 8. Cleanup

Cleanup runs on success, partial failure, and error:

1. ensure every tracked agent is closed;
2. remove council scratch files and throwaway environments, clones, caches,
   and disposable worktrees created by the council;
3. never remove or modify user-owned source files or the final report;
4. preserve only evidence scripts explicitly cited by the final report, move
   them beside the report in a collision-safe evidence directory, and state
   their paths;
5. disclose cleanup failures.

The reproducibility agent must clean its own heavy artifacts first; parent
cleanup is the final safety check. Never run destructive cleanup against an
unverified path.
