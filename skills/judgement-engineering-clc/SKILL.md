---
name: judgement-engineering-clc
description: Governs problem framing, decision quality, and reversible next steps before engineering planning. Use when goals are fuzzy, unclear, contradictory, high-impact, under-specified, hidden-assumption driven, likely to drift, or when Claude Code must decide what should be built before writing an implementation plan.
---

# Judgement Engineering

Use this skill before implementation planning when confident execution might solve the wrong problem. Planning answers how. Judgement engineering answers whether, why, what, and how much.

## Quick Start

1. Frame the problem before proposing implementation.
2. Classify the uncertainty class as Clear, Complicated, Complex, Chaotic, or Confused.
3. Generate 2-4 viable options, including a minimal reversible option.
4. Convert major assumptions into tests, experiments, or explicit human decision points.
5. Produce a judgement brief with a stop/go recommendation.

## Required Judgement Brief

Use this structure:

```markdown
## Judgement Brief
- Stated goal:
- Inferred goal:
- Underlying problem:
- Non-goals:
- Stakeholders/users:
- Success signal:
- Failure signal:
- Constraints:
- Missing constraints:
- Uncertainty class:
- Candidate interpretations:
- Selected working interpretation:
- Confidence:
- Assumptions:
- Risks:
- Options considered:
- Recommended next step:
- Reversibility rating:
- Fastest useful experiment:
- Human decision points:
- Stop/go recommendation:
- What evidence that would change the decision:
```

Proceed with a provisional working interpretation only when the next step is reversible and the uncertainty is clearly labeled.

## References

- For problem framing and the goal refinement loop, read [problem-framing.md](references/problem-framing.md).
- For Clear/Complicated/Complex/Chaotic/Confused classification, read [uncertainty-classification.md](references/uncertainty-classification.md).
- For comparing directions before committing, read [decision-options-register.md](references/decision-options-register.md).
- For reversibility and assumption-to-test conversion, read [reversibility-and-assumptions.md](references/reversibility-and-assumptions.md).
- For premortems, value-of-information checks, escalation, and judgement review, read [judgement-review.md](references/judgement-review.md).
