# Uncertainty Classification

Classify the task before planning.

## Classes

- Clear: requirements and acceptance criteria are known. Plan and execute normally.
- Complicated: the goal is coherent, but expert knowledge, current documentation, or careful design review is needed before planning.
- Complex: cause and effect are uncertain. Prefer prototypes, experiments, benchmarks, or small reversible probes.
- Chaotic: the system is broken or unstable. Stabilize, reproduce, or contain the failure before planning new work.
- Confused: the goal is ambiguous or contradictory. Decompose, restate, and ask only for decisions that cannot be discovered.

## Required Action

- Clear: proceed to planning.
- Complicated: research, inspect, or request expert review first.
- Complex: define the fastest useful experiment before committing to a design.
- Chaotic: stop feature work and stabilize the system.
- Confused: run the Problem-Framing Gate and Goal Refinement Loop.

Low confidence should trigger research, prototyping, or judgement review rather than irreversible implementation.
