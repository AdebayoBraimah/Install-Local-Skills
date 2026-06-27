# Judgement Review

Use this review when the decision is high-impact, low-confidence, or likely to drift.

## Premortem Gate

Ask: Imagine this failed badly in two weeks. Why did it fail?

Consider:

- wrong problem
- scope creep
- hidden user preference
- stale context
- unowned decision
- unclear acceptance criteria
- no feedback loop
- overbuilt architecture
- missing tests
- architecture drift
- poor handoff

## Value-of-Information Gate

Ask: Would more information change the decision?

- If yes, research, inspect, benchmark, prototype, or ask.
- If no, execute the smallest safe next step.

## Human Decision Gate

Escalate when the decision depends on user preference, project priority, risk tolerance, cost tolerance, public API semantics, security posture, data retention policy, destructive action, irreversible migration, credential access, or product tradeoff.

If the agent cannot ask immediately, it may proceed only with a clearly labeled reversible provisional decision.

## Judgement Reviewer Checklist

Check:

- Are we solving the right problem?
- Is the goal coherent?
- Are hidden assumptions driving the design?
- Is the solution overbuilt?
- What simpler version would teach us faster?
- What would a skeptical senior engineer reject?
- Is the next step reversible enough?
- Are human decisions being guessed?

## Judgement Review Output

Statuses:

- pass: proceed with the recommended next step.
- revise: revise framing, options, assumptions, or reversibility before planning.
- block: do not proceed until the blocking issue is resolved.
- human-decision: use when the existing Human Decision Gate applies; this status inherits that gate and must not narrow its escalation criteria.

Use this output template:

```markdown
## Judgement Review Output
- Status: pass / revise / block / human-decision
- Findings: <none, or concise findings>
- Required changes: <none, or changes required before planning>
- Human decision needed: <none, or the exact decision required>
- Confidence: high / medium / low / unknown
- Recommended next action: <one concrete next step>
```
