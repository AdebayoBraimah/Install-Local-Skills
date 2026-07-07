---
name: research-council-clc
description: |
  Adversarial academic review council for AI/ML and mathematical research. Use when
  the user invokes /research-council-clc, asks for a "research council", wants a
  research idea, abstract, draft paper, experiment plan, proof, or code repository
  torn apart by independent reviewers, or wants brutally honest pre-submission
  feedback with citations and receipts. Fans out persona reviewers in parallel via
  the Workflow tool (Prior-Art Scout, Reviewer #2, Methodologist, Devil's Advocate,
  Theory/Proof Checker, Reproducibility Engineer), then a Chair synthesizes one
  prioritized, citation-backed report. Claude Code only.
version: 1.0.0
---

# Research Council

An adversarial review council for academic research artifacts, specialized for
AI/ML and mathematics. Each council member has a fixed persona, a mandate to
disagree, and tools to pull real evidence (literature search, code execution,
proof checking). A neutral Chair merges everything into one prioritized,
citation-backed report. The goal is a NeurIPS/ICML-calibre pre-review — not
encouragement.

## Requirements — Claude Code only

This skill orchestrates reviewers with the **Workflow** tool. If the Workflow
tool is not available in the current harness (Codex, Gemini CLI, Antigravity,
or a restricted Claude environment), stop immediately and tell the user:

> research-council-clc requires Claude Code with the Workflow tool. Run it from
> a Claude Code session.

Do not attempt a sequential fallback.

## Invocation

```
/research-council-clc <artifact | path | idea>
/research-council-clc quick    <artifact>   # 3 reviewers + chair
/research-council-clc standard <artifact>   # 5 reviewers + chair
/research-council-clc full     <artifact>   # 7 reviewers + chair + verification round
```

`<artifact>` is any of:
- a free-text **idea or phrase** ("contrastive pretraining for EEG artifact removal")
- a **file path** — abstract, draft paper (`.md`, `.tex`, `.pdf`, `.docx`), experiment plan, proof
- a **directory / repo path** — code accompanying a claim
- any **combination** ("review draft.tex against ./experiments")

Argument order does not matter; the first token matching `quick|standard|full`
is the tier, everything else is the artifact.

## Step 1 — Parse arguments and classify the artifact

1. Extract the tier keyword if present. Remaining text is the artifact spec.
2. Classify each artifact component:
   - **idea** — free text, no existing path
   - **document** — path to a readable file (read it; for PDFs use the Read tool)
   - **repo** — path to a directory containing code
   - **proof** — document containing formal mathematics (theorem statements,
     derivations, LaTeX math, Lean)
3. If no artifact was given at all, ask the user what to review — do not guess.

**Auto tier selection** (only when no tier keyword given):

| Artifact | Tier | Council |
|---|---|---|
| idea/phrase only | quick | 3 reviewers |
| document (abstract/draft/plan) | standard | 5 reviewers |
| repo present, or proof present | full | 7 reviewers + verification |

Tell the user which tier was selected and why before launching; give them a
beat to object, but do not block on confirmation.

## Step 2 — Write the intake brief

Materialize everything the reviewers need into one file in the scratchpad
directory (never `/tmp`): `<scratchpad>/council/intake-brief.md` containing:

- The artifact verbatim (idea text) and/or absolute paths to documents/repos
- The central claim(s) as you understand them, stated in one or two sentences each
- Field/subfield (e.g., "RL, offline; theory-heavy") — infer from the artifact
- Today's date (reviewers need it for "is this already published?" searches)
- Tier and roster

Keep the brief under ~200 lines; reviewers read source documents themselves.

## Step 3 — Compose the roster and launch the Workflow

Persona instructions live in `agents/` under this skill's base directory:

| Key | Persona file | quick | standard | full |
|---|---|---|---|---|
| `prior-art` | `agents/prior-art-scout.md` | x | x | x |
| `reviewer-2` | `agents/reviewer-2.md` | x | x | x |
| `methodologist` | `agents/methodologist.md` | x | x | x |
| `devils-advocate` | `agents/devils-advocate.md` | | x | x |
| `theory` | `agents/theory-checker.md` | | (a) | x |
| `repro` | `agents/repro-engineer.md` | | (a) | x |
| Chair (always runs) | `agents/chair.md` | x | x | x |

(a) standard tier includes exactly one of `theory`/`repro`: pick `theory` when
the artifact is proof/derivation-heavy, `repro` when a repo is present or the
work is primarily empirical. If both apply equally, pick `repro`.

The workflow builds every reviewer and chair prompt itself from a template —
you only supply a compact **roster**. Do **not** pass full prompt strings:
the harness truncates large `args` payloads in transit, which silently corrupts
the JSON. Keep `args` small (a few hundred bytes).

Call the **Workflow** tool with:

- `scriptPath`: `<skill base dir>/scripts/council-workflow.js`
- `args` (a real JSON object, kept small):

```json
{
  "verify": false,
  "briefPath": "<abs path to intake-brief.md>",
  "agentsDir": "<skill base dir>/agents",
  "chairFile": "chair.md",
  "roster": [
    {"key": "prior-art",     "role": "Prior-Art Scout",              "file": "prior-art-scout.md"},
    {"key": "reviewer-2",    "role": "Reviewer #2",                  "file": "reviewer-2.md"},
    {"key": "methodologist", "role": "Methodologist / Stats Critic", "file": "methodologist.md"}
  ]
}
```

- `key` — short id for labels/dedup; `role` — human role name inserted into the
  prompt; `file` — persona filename inside `agentsDir`.
- Include only the roster rows for the selected tier (see the table above).
  For standard/full, add the extra rows: `{"key":"devils-advocate","role":"Devil's Advocate","file":"devils-advocate.md"}`,
  `{"key":"theory","role":"Theory / Proof Checker","file":"theory-checker.md"}`,
  `{"key":"repro","role":"Reproducibility Engineer","file":"repro-engineer.md"}`.
- Set `"verify": true` **only** for the full tier.

The workflow fans the roster out in parallel, optionally runs an adversarial
verification round on CRITICAL/MAJOR findings (full tier), and finishes with the
Chair. Everything a reviewer needs beyond its persona and role must live in the
**intake brief** (Step 2), since that path is all the prompt carries.

Notes:
- The Reproducibility Engineer **executes code** when a repo is given (isolated
  env under the scratchpad). Warn the user that permission prompts may appear
  mid-run depending on their permission mode.
- If a reviewer returns `null` (skipped/failed), continue; the Chair must note
  the missing perspective in the report.

## Step 4 — Deliver the report

The workflow returns `{ reviews, verified, report }` where `report` is the
Chair's consolidated markdown.

1. Write it to `council-review-<slug>.md` in the current working directory,
   where `<slug>` is a short kebab-case name derived from the artifact
   (e.g. `council-review-eeg-contrastive.md`). If the file exists, suffix `-2`,
   `-3`, ….
2. Load the `artifact-design` skill, then publish the same report as an
   Artifact page (favicon `🏛️`, stable across redeploys of the same review).
3. In chat, give only: the aggregate verdict, the 3–5 highest-priority
   findings (one line each), the report path, and the Artifact link.

Do not soften the council's findings when summarizing. If every reviewer was
positive, say so plainly — but check first that the reviewers actually cited
evidence; an evidence-free positive review is a failed review and should be
called out as such.

## Failure handling

- Workflow tool denied/unavailable → the Claude-Code-only message above.
- All reviewers failed → report the failure; do not fabricate a review.
- Artifact publish fails → the markdown report is the deliverable; mention the
  Artifact failure and move on.
