---
name: manuscript-review-clc
description: |
  ICLR-calibre peer review for written manuscripts. Use when the user invokes
  /manuscript-review-clc, asks for a paper or manuscript review, a mock or
  simulated ICLR/NeurIPS/ICML review, predicted reviews, likely reviewer
  reactions, or an accept/reject leaning for a draft paper. Fans out
  independent reviewer personas — calibrated on real ICLR 2026 reviews and
  outcomes — in parallel via the Workflow tool, optionally verifies major
  weaknesses against the manuscript, then an Area Chair writes a meta-review
  with a decision leaning and a priority revision plan. Claude Code only.
version: 1.0.0
---

# Manuscript Review

A simulated top-venue review panel for draft papers. Each reviewer persona
writes a complete, standalone ICLR-format review with a distinct emphasis
(novelty/positioning, experiments/statistics, claims/correctness,
clarity/reproducibility); the full tier adversarially checks major weaknesses
against the manuscript to kill hallucinated criticisms; an Area Chair merges
everything into a meta-review with a decision leaning, rebuttal forecast, and
prioritized revision plan. Scores and severity judgments are calibrated on
real ICLR 2026 submissions with known outcomes (`references/calibration.md`).

The goal is to predict what real reviewers will say — and hand the authors
the highest-leverage fixes — before a real venue does.

## Requirements — Claude Code only

This skill orchestrates reviewers with the **Workflow** tool. If the Workflow
tool is not available in the current harness, stop immediately and tell the
user:

> manuscript-review-clc requires Claude Code with the Workflow tool. Run it
> from a Claude Code session.

Do not attempt a sequential fallback.

## Invocation

```
/manuscript-review-clc <manuscript-path> [context...]
/manuscript-review-clc quick    <manuscript-path>   # 2 reviewers + AC
/manuscript-review-clc standard <manuscript-path>   # 4 reviewers + AC (default)
/manuscript-review-clc full     <manuscript-path>   # 4 reviewers + verification + AC
```

- `<manuscript-path>` — a draft paper: `.pdf`, `.tex`, `.md`, `.docx`, or a
  directory containing the paper source (find the main file).
- `[context...]` — optional free text: target venue, deadline, what the
  authors are most worried about, links to the accompanying repo.

Argument order does not matter; the first token matching
`quick|standard|full` is the tier, the first existing path is the manuscript,
everything else is context. If no manuscript path was given, ask the user for
one — do not review an idea from free text (that is `research-council-clc`'s
job; suggest it instead).

## Step 1 — Parse arguments and select the tier

Default tier is **standard**. Auto-upgrade to **full** when the manuscript is
theory-heavy (theorem statements / formal proofs present) or the user asks for
a decision prediction, thorough review, or pre-submission check. Tell the
user which tier was selected and why before launching; give them a beat to
object, but do not block on confirmation.

| Tier | Roster | Verification |
|---|---|---|
| quick | A (novelty) + B (empirical) | no |
| standard | A + B + C (theory/claims) + D (clarity) | no |
| full | A + B + C + D | yes |

## Step 2 — Write the intake brief

Skim the manuscript's first pages (title, abstract, intro) — enough to write
the brief, not a full read; reviewers read the manuscript themselves.
Materialize the brief at `<scratchpad>/manuscript-review/intake-brief.md`
(never `/tmp`) containing:

- Absolute path to the manuscript (and repo/supplement paths if given)
- Title and the paper's claimed contributions, restated in one line each
- Field/subfield (e.g. "LLM multi-agent systems; empirical") — infer it
- Target venue if the user named one (default: ICLR-style top ML venue)
- Any user-supplied context (worries, deadline)
- Today's date (reviewers need it for prior-art searches)
- Tier and roster

Keep the brief under ~100 lines.

## Step 3 — Launch the Workflow

Call the **Workflow** tool with:

- `scriptPath`: `<skill base dir>/scripts/review-workflow.js`
- `args` (a real JSON object, kept small — the harness truncates large args
  payloads in transit; prompts are templated inside the script):

```json
{
  "verify": false,
  "briefPath": "<abs path to intake-brief.md>",
  "skillDir": "<abs path to this skill's base directory>",
  "roster": [
    {"key": "novelty",   "role": "Reviewer A (Novelty & Positioning)",           "file": "reviewer-novelty.md"},
    {"key": "empirical", "role": "Reviewer B (Experiments & Statistical Rigor)", "file": "reviewer-empirical.md"},
    {"key": "theory",    "role": "Reviewer C (Claims & Technical Correctness)",  "file": "reviewer-theory.md"},
    {"key": "clarity",   "role": "Reviewer D (Clarity & Reproducibility)",       "file": "reviewer-clarity.md"}
  ]
}
```

- Include only the roster rows for the selected tier (quick = `novelty` +
  `empirical`).
- Set `"verify": true` **only** for the full tier.

The workflow fans reviewers out in parallel, optionally verifies
CRITICAL/MAJOR weaknesses against the manuscript, and finishes with the Area
Chair. If a reviewer returns `null` (skipped/failed), continue; the AC notes
the missing seat.

## Step 4 — Deliver the report

The workflow returns `{ reviews, verified, report }` where `report` is the
Area Chair's meta-review markdown.

1. Compose the full deliverable: the AC report first, then an appendix with
   each reviewer's complete review rendered in the ICLR form
   (`references/review-format.md` field order; render each weakness as its
   numbered title + body + evidence + fix, and include the sub-scores,
   rating, and confidence). Mark verification-refuted weaknesses inline with
   `[refuted in verification]` rather than deleting them.
2. Write it to `manuscript-review-<slug>.md` in the current working
   directory (`<slug>` = short kebab-case name from the paper title; suffix
   `-2`, `-3`, … if taken).
3. Load the `artifact-design` skill, then publish the report as an Artifact
   page (favicon `📝`, stable across redeploys of the same review).
4. In chat, give only: the decision leaning, the rating spread, the 3–5
   load-bearing weaknesses (one line each, tagged FATAL/PATCHABLE), the top
   revision priority, the report path, and the Artifact link.

Do not soften the panel's findings when summarizing. If the panel was
uniformly positive, verify its praise cites actual evidence — an
evidence-free positive review is a failed review; say so.

## Failure handling

- Workflow tool denied/unavailable → the Claude-Code-only message above.
- Manuscript unreadable (corrupt PDF, missing path) → report it and stop;
  never review from the title alone.
- All reviewers failed → report the failure; do not fabricate a review.
- Artifact publish fails → the markdown report is the deliverable; mention
  the failure and move on.
