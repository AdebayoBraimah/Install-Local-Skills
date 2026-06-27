# Problem Framing

Use the Problem-Framing Gate before writing an implementation plan for unclear, high-impact, or evolving work.

## Gate

Capture:

- stated goal: the user's literal request
- inferred goal: what the user likely needs
- underlying problem: the failure, opportunity, or decision behind the request
- stakeholders/users: who benefits or is affected
- success signal: observable evidence the work helped
- failure signal: observable evidence the work is wrong or harmful
- constraints: known technical, time, policy, safety, budget, or compatibility limits
- non-goals: what should not be solved now
- missing constraints: decisions that cannot be discovered from the repo or environment

## Goal Refinement Loop

Run this loop until the next step is coherent:

1. Restate the goal in concrete terms.
2. Identify missing constraints.
3. Generate candidate interpretations.
4. Score interpretations by alignment, risk, reversibility, and time to feedback.
5. Choose a working interpretation.
6. Prototype, inspect, test, research, or ask to learn.
7. Refine the goal.

The working interpretation may be provisional. Label it provisional when important constraints are still unknown.

## Escalation

Ask the user when the judgement depends on preference, priority, risk tolerance, public API semantics, data policy, security posture, destructive action, credentials, cost, or business tradeoff.
