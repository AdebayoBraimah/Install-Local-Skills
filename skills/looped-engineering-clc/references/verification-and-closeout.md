# Verification and Closeout

Run validation and closeout according to the selected operating level and observed risk. Lite work must not require unconditional plan review, Full OS artifacts, ADRs, or consensus unless risk escalates.

## Verification

Run validation appropriate to risk:

- targeted tests
- broader tests when shared behavior changed
- lint/typecheck/build commands when available
- repo-specific graph/index freshness checks when required
- architecture fitness checks if available
- Success Metrics measurement when triggered
- change-scope detection if available

For repositories with graph/index tools, update indexes only when repository rules or user instructions require it. Do not run Graphify unless explicitly instructed.

Before commit, detect unexpected changes. Do not stage forbidden agent instruction files such as `AGENTS.md` or `CLAUDE.md` unless explicitly instructed. Do not push unless explicitly instructed.

## Closeout Checklist by Operating Level

Use evidence lines in the final note, handoff, or milestone report. Each line should include command/artifact, result, and residual risk when relevant.

### Lite

- Tests: targeted test or manual verification relevant to the change.
- Lint/typecheck/build: run only when repository convention or touched file requires it.
- Graph/index freshness: not required unless repository rules require it; Do not run Graphify unless explicitly instructed.
- Changed files: list touched files.
- Unexpected changes: check if committing or if the workspace has unrelated changes.
- Docs: update only if behavior or usage changed.
- ADRs: not required unless risk escalates.
- Risks: note only new meaningful risk.
- Assumptions: note only assumptions that affect correctness.
- Knowledge Gap Gate / Architecture Fitness Gate / Success Metrics Gate: not required unless Lite risk escalates; if triggered, record status and evidence in the final note.
- Handoff: optional unless pausing or context pressure requires it.
- Alert: record alert outcome when this workflow was explicitly invoked or long-running.

### Standard

- Tests: targeted tests for each slice and broader tests when shared behavior changed.
- Lint/typecheck/build: run available relevant checks or explain why unavailable.
- Graph/index freshness: update or check only when repository rules require it; Do not run Graphify unless explicitly instructed.
- Changed files: record expected changed files and actual changed files.
- Unexpected changes: inspect and separate unrelated changes before commit.
- Docs: update when user-facing behavior, public API, operations, or workflow changed.
- ADRs: required only for triggered public API, dependency, architecture, migration, data semantics, or irreversible decisions.
- Risks: review triggered risks and record mitigation or accepted residual risk.
- Assumptions: record major assumptions that shaped the plan.
- Knowledge Gap Gate: when triggered, record gaps as resolved, accepted, experiment, blocked, or follow-up.
- Architecture Fitness Gate: when triggered, record checks run or manual checks performed, pass/fail result, and action.
- Success Metrics Gate: when triggered, record metric, target or expected direction, measurement method, and closeout evidence.
- Handoff: required for pause, transfer, unresolved decision, or context-heavy continuation.
- Alert: record alert outcome.

### Full OS

- Tests: targeted, integration/regression, reproducibility, or benchmark checks appropriate to the milestone.
- Lint/typecheck/build: run all relevant repository checks or classify unavailable checks.
- Graph/index freshness: update or check only when repository rules require it; Do not run Graphify unless explicitly instructed.
- Changed files: compare actual changes to plan and manifest.
- Unexpected changes: explain, isolate, or stop for user decision.
- Docs: update specs, operations docs, or design notes as triggered.
- ADRs: satisfy the ADR Gate for architecture, public API, dependency, migration, data semantics, or irreversible decisions.
- Risks: update risk register or milestone report with owner, status, mitigation, and validation path.
- Assumptions: validate, accept, or convert major assumptions into experiments.
- Knowledge Gap Gate: record triggered gaps as passed/resolved, accepted, blocked, or follow-up.
- Architecture Fitness Gate: record triggered fitness checks as passed, accepted, blocked, or follow-up.
- Success Metrics Gate: record triggered Success Metrics as measured/passed, accepted, blocked, or follow-up.
- Handoff: required at milestone close, pause, transfer, context pressure, or unresolved decision.
- Alert: record alert outcome.

## Failure Classification

- resolved locally: failure was reproduced, fixed, and validation passed.
- acceptable known failure: failure is unrelated or pre-existing, with evidence and risk noted.
- blocker: failure prevents safe closeout without external change.
- human decision required: failure requires product, policy, destructive, secret, or high/critical risk acceptance.
- follow-up task: failure is low-risk or out of scope, with owner/status and trigger.

## Reflection

Ask:

- Did this make the architecture deeper or shallower?
- Did new coupling appear?
- Did implementation expose follow-up refactors?
- Did tests require excessive mocking?
- Did the same concept appear in multiple modules?
- Did interface complexity grow?
- Should a follow-up plan be created?

## Commit

If committing:

- stage only intended files
- follow repository commit format
- avoid forbidden files
- summarize validation

## Handoff Quality Gate

If pausing or transferring, write a handoff that lets another agent resume without raw chat history. Include:

- current goal
- active plan/spec path
- completed tasks
- changed files
- validation status
- blockers
- unresolved decisions
- assumptions and risks
- rollback information when relevant
- recommended next skill
- next action

Use OS temp directory unless the repository has an established temporary coordination location.

## Milestone Exit Criteria

Do not close a milestone until the operating-level checklist is satisfied and:

- plan complete when a plan was required
- plan review complete when formal plan review was required
- architecture reviewed when relevant
- tests pass or failures are classified
- docs updated if needed
- graph/index freshness handled if required
- ADR written if the ADR Gate was triggered
- risks reviewed when risk changed
- assumptions reviewed when major assumptions shaped the work
- triggered Knowledge Gap Gate items, Architecture Fitness Gate checks, and Success Metrics Gate measurements recorded as passed, accepted, blocked, or follow-up for Full OS closeout
- handoff written when required
- alert sent via `alert-me` or alert failure recorded
