# Workflow State Machine

This file is the lifecycle overview. It delegates operating levels, the transition table, upgrade/downgrade rules, and per-state artifacts to [operating-levels-and-state-machine.md](operating-levels-and-state-machine.md).

The workflow is both a lifecycle and a set of loops. Use the detailed state machine when deciding whether Lite, Standard, or Full OS gates apply.

## Lifecycle

Intake -> Orient -> Judgement -> Research -> Architecture -> Plan -> Plan Review -> Execute -> Verify -> Drift/Health/Invariant -> Reflect -> Commit/Handoff -> Alert -> Continue/Stop.

## Embedded Loops

- Planning loop: draft -> review -> revise -> review again when the selected operating level or risk requires it.
- Execution loop: edit -> test -> inspect -> fix.
- Architecture loop: observe friction -> propose candidate -> evaluate -> plan.
- Continuation loop: handoff -> resume -> orient -> continue.

## Intake Classification

Classify work as:

- answer-only
- small edit
- bug fix
- feature
- refactor
- architecture review
- plan execution
- handoff or continuation

Choose the lightest loop that satisfies the task and repository rules. Do not run Full OS for a trivial answer unless risk escalates.

## Stop Conditions

Stop only for a real human decision, high/critical risk acceptance, missing secret, destructive action, unresolved local validation failure, public API/data policy decision, or explicit user pause. When stopping, write a concise state note or handoff and alert.
