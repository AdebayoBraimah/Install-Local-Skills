# Plan Review and Execution

This file owns planning, `writing-plans`, `plan-review-clc`, TDD, and execution-loop mechanics. It delegates skill/tool routing and consensus role selection to [routing-and-consensus.md](routing-and-consensus.md).

## Planning

Use `writing-plans` when work is multi-step, touches multiple files, has non-trivial risk, or includes tests, docs, migrations, or integration points and the selected operating level requires a formal plan. For ordinary Standard work, a concise plan or plan delta is enough unless risk escalates.

Plans should include goal, exact files to create or modify, ordered tasks, tests per task, commands, expected outcomes, risks, assumptions, open questions, and commit checkpoints where useful.

Default plan path: `docs-superpowers/superpowers/plans/YYYY-MM-DD-<feature-or-milestone>.md`.

## Standard-Plan and Standard-Plan-Review Trigger Table

| Work type | Planning requirement | `plan-review-clc` requirement | Notes |
| --- | --- | --- | --- |
| Ordinary clear multi-file feature or normal refactor | Concise plan or plan delta required. | Not required unless risk escalates. | Use targeted validation and broaden only when shared behavior changes. |
| Clear public API addition with stable semantics | Formal plan required. | Required. | Include tests for the public API contract. |
| Clear dependency change | Formal plan required. | Required. | Include dependency rationale, rollback path, and validation. |
| Clear cross-module shared behavior | Formal plan required. | Required. | Include integration or regression checks for affected modules. |
| Elevated but locally testable validation risk | Formal plan required. | Required. | Include failure classification and recovery path. |
| Mandatory Full OS escalation: migration/data semantics changes, irreversible actions, security/data-loss/accessibility impact, unclear acceptance criteria, fuzzy or contradictory goals, high-impact work, architecture-changing work, long-running milestones, handoff-heavy work, AI/ML or research systems, or multi-milestone tasks | Full OS formal plan required. | Required before implementation. | Full OS takes precedence over Standard triggers. |

## Plan Review

Use `plan-review-clc` when Full OS, a bounded Standard formal-review trigger, a substantial plan, or risk escalation requires it. Run independent plan review, then correct all medium, high, or critical issues before implementation unless the risk is explicitly accepted and documented.

Do not execute a plan that requires formal review until the plan review gate converges.

## Execution Loop

Execute task-by-task:

1. write or update a behavior-focused test when behavior changes
2. make the smallest scoped edit
3. run targeted validation
4. fix failures
5. update plan status

Use TDD vertical slices for non-trivial behavior. Do not write all tests first and all implementation later.

Before editing functions, classes, methods, APIs, or symbols, use available repository intelligence such as GitNexus impact analysis if present.

## Simplicity Governor

Use a YAGNI/simplicity governor:

- ask whether the thing needs to exist
- prefer standard library or native platform features
- prefer existing dependencies
- avoid new abstractions with only one implementation
- avoid new dependencies unless justified
- keep the smallest working diff

Do not use simplicity as an excuse to skip tests, security, validation, data-loss handling, accessibility, research provenance, reproducibility, architecture gates, or handoff notes.

## Progress

Keep the active plan updated. For long work, maintain working memory with current goal, slice, changed files, validation status, blocker, and next action.
