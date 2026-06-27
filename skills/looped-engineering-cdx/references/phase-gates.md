# Phase Gates

Use gates to prevent confident work on the wrong target. This file summarizes gate purpose and exit criteria; it delegates operating-level selection and state transitions to [operating-levels-and-state-machine.md](operating-levels-and-state-machine.md) and delegates helper-skill routing decisions to [routing-and-consensus.md](routing-and-consensus.md).

## Intake Gate

Exit when the task type, likely blast radius, and lightest sufficient operating level are known.

## Orient Gate

Read repository instructions first: `AGENTS.md`, `CLAUDE.md`, contribution docs, style guides, existing plans, specs, tests, architecture docs, and current repository state.

Exit when relevant files/modules are identified, constraints are known, validation commands are known or confirmed absent, and repository-specific rules are understood.

## Judgement Gate

Use `judgement-engineering-cdx` when goals are fuzzy, incomplete, contradictory, high-impact, poorly specified, hidden-assumption driven, or likely to drift. Exit with a judgement brief or a clearly labeled reversible provisional interpretation.

## Research and Brainstorming Gate

Use when the task is vague, solution space is unclear, multiple approaches are plausible, product/design direction is uncertain, or current documentation matters. Route the specific helper through `routing-and-consensus.md`.

## Architecture Gate

Use before implementation planning when structure, coupling, adapters, testability, maintainability, refactoring, shallow modules, public APIs, migrations, or deepening opportunities are central.

For architecture-sensitive work, define Architecture Fitness Functions where practical, including the check method and what happens on pass/fail.

## Planning Gate

Use a concise plan, plan delta, or formal plan according to the selected operating level and risk. Multi-step work, multiple files, non-trivial risk, tests, docs, migrations, or integration points usually require at least a plan delta.

When the Knowledge Gap Gate is triggered, unresolved knowledge gaps must be resolved, explicitly accepted, or converted into experiments before planning closes.

## Plan Review Gate

Use `plan-review-cdx` when the selected operating level or Standard formal-review triggers require it. Correct all medium/high/critical findings before implementation unless the risk is explicitly accepted and documented.

## Execution and Verification Gates

Execute task-by-task. Verify with targeted tests, broader tests when appropriate, lint/typecheck/build, repository-specific commands, graph/index updates when required, and unexpected-change detection.

When triggered, execute applicable architecture fitness checks and measure Success Metrics with closeout evidence.

## Reflection and Closeout Gate

Reflect on architecture depth, coupling, mocking, repeated concepts, interface complexity, follow-up refactors, docs, handoff, and alerting before closing a milestone. Apply the closeout depth from the selected operating level.

When triggered, include Knowledge Gap Gate outcomes, Architecture Fitness Gate checks, and Success Metrics Gate measurements as closeout evidence.
