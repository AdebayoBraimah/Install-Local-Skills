# Engineering Governance

Do not create every artifact blindly. Create or update only those justified by task size, selected operating level, triggered gates, and repository conventions.

## Lite/Standard/Full OS Governance-Gate Matrix

| Operating level | Governance posture | Required gates |
| --- | --- | --- |
| Lite | Lite skips governance gates, including Knowledge Gap, Architecture Fitness, and Success Metrics Gates, unless a risk-escalation boundary is crossed. Risk-escalation includes public API impact, data-loss risk, security/accessibility impact, irreversible action, unclear acceptance criteria, or shared architecture change. | None by default; apply only the triggered gate if risk escalates. |
| Standard | Standard applies only triggered governance gates for the selected work, such as bounded ADR, knowledge gap, risk, rollback, architecture fitness, or measurable-outcome checks for clear API, dependency, shared-behavior, or milestone changes. | Triggered ADR Gate, Assumption/Knowledge Gap Gate, Risk Gate, Rollback Gate, Invariant/Architecture Fitness Gate, or Success Metrics Gate. |
| Full OS | Full OS applies the full governance gate set relevant to the milestone, and triggered knowledge gaps, fitness checks, and success metrics must be closed before milestone close. | ADR Gate, Assumption Gate, Knowledge Gap Gate, Risk Gate, Complexity Budget Gate, Invariant Gate, Architecture Fitness Gate, Drift Gate, Rollback Gate, Success Metrics Gate, and Telemetry Gate as applicable. |

## Governance Gates

### ADR Gate

Required for public APIs, architecture changes, dependency changes, migrations, data semantics, and irreversible decisions. Exit when the ADR is written or a documented decision says the repository convention stores the decision elsewhere.

### Assumption Gate

Major assumptions must be validated, explicitly accepted, or converted into experiments before planning closes. Exit when each major assumption has confidence, validation method, owner/agent, status, and next review trigger.

### Knowledge Gap Gate

Augments the Assumption Gate; it does not replace assumption tracking. Trigger when planning or design depends on missing docs, benchmarks, papers, examples, API behavior, performance numbers, or unclear facts. Use a Knowledge Gap Tracker when multiple gaps affect the plan. Exit when each important gap is resolved with evidence, explicitly accepted with risk, or converted into an experiment with owner/status.

### Risk Gate

High-impact risks must have mitigation, owner, status, and validation path. Exit when high/critical risks are mitigated, accepted by the user, or blocking.

### Complexity Budget Gate

Define limits for maximum new packages, files modified, new abstractions, breaking changes, or migration scope. Exceeding budget triggers replanning and plan review.

### Invariant Gate

Required invariants must be checked before milestone close. Examples include no circular imports, public APIs have tests, schema version matches migrations, every task has acceptance criteria, architecture boundaries hold, and configured coverage thresholds are respected.

### Architecture Fitness Gate

Augments the Invariant Gate for architecture-sensitive work. Trigger for architecture-sensitive work, public API changes, dependency changes, migrations, boundary changes, major refactors, or Full OS milestones where structure matters. Define Architecture Fitness Functions as automated checks where practical or manual checks where automation is not available. Exit when applicable checks are defined, their pass/fail action is known, and failed checks are resolved, accepted, blocked, or converted into follow-up based on severity.

### Drift Gate

Detect unexpected dependencies, dead modules, duplicate implementations, unused abstractions, architecture boundary violations, and divergence from ADRs/specs/plans. Severe drift blocks closeout; minor drift becomes linked follow-up.

### Rollback Gate

Non-trivial changes must define revert path, affected files/configs/migrations, data-loss risk, and rollback validation.

### Telemetry Gate

Substantial milestones record planning/coding/testing/research time, rework, failures, replans, and failure causes when practical.

### Success Metrics Gate

Augments Living Project Specification and Telemetry guidance. Trigger for Standard milestones with measurable outcomes and all Full OS milestones. Exit when Success Metrics include the metric, target or expected direction, measurement method, and closeout evidence location.

## Artifact Defaults

- Plans: `docs-superpowers/superpowers/plans/YYYY-MM-DD-<feature-or-milestone>.md`
- Specs: `docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md`
- ADRs: `docs/adr/ADR-YYYY-MM-DD-<slug>.md`
- Assumption register: `docs/engineering/assumptions.md`
- Risk register: `docs/engineering/risks.md`
- Technical debt ledger: `docs/engineering/technical-debt.md`
- Health dashboard: `docs/engineering/health.md`
- Context snapshots: `docs/engineering/context-snapshots/YYYY-MM-DD-<slug>.md`
- Handoffs: OS temp directory unless repository conventions say otherwise.

## Living Project Specification

Consult or maintain project vision, goals, non-goals, architecture, constraints, coding standards, milestones, Success Metrics, and roadmap when the selected operating level or repository convention requires it. When the Success Metrics Gate triggers, record the measurement method and closeout evidence location with the milestone.

## Evidence-Based Planning

Major planning decisions should cite evidence from repository files, tests, Graphify only when explicitly instructed, GitNexus or similar impact analysis, Context7/current docs, benchmarks, research, ADRs, and specs.

## Compact Templates

### ADR Template

- Title:
- Date:
- Status:
- Context:
- Decision:
- Alternatives considered:
- Tradeoffs:
- Consequences:
- Evidence/source:
- Confidence:
- Links to plans/specs/code:
- Next review trigger:

### Assumption Entry Template

- Assumption:
- Date:
- Source/evidence:
- Confidence:
- Validation method:
- Owner/agent:
- Status:
- Next review trigger:

### Knowledge Gap Entry Template

- Gap:
- Date:
- Why it matters:
- Missing source/evidence:
- Resolution path:
- Owner/agent:
- Status: resolved / accepted / experiment / blocked
- Closeout evidence:
- Next review trigger:

### Risk Entry Template

- Risk:
- Date:
- Source/evidence:
- Likelihood:
- Impact:
- Mitigation:
- Owner:
- Status:
- Validation path:
- Next review trigger:

### Debt Entry Template

- Description:
- Date:
- Source/evidence:
- Priority:
- Estimated effort:
- Reason postponed:
- Linked milestone:
- Owner/status:
- Next review trigger:

### Health Summary Template

- Date:
- Milestone:
- Architecture health:
- Dependency graph status:
- Complexity:
- Coverage:
- Documentation coverage:
- Open task markers:
- Technical debt:
- Tests/build status:
- Graph/index freshness:
- Repository intelligence warnings:
- Next review trigger:

### Drift Report Template

- Date:
- Drift observed:
- Source/evidence:
- Severity:
- Affected boundary:
- Impact:
- Resolution or follow-up:
- Owner/status:
- Next review trigger:

### Architecture Fitness Function Template

- Fitness function:
- Boundary or invariant protected:
- Check type: automated / manual
- Command or method:
- Pass condition:
- Fail action:
- Owner/agent:
- Status:
- Closeout evidence:
- Next review trigger:

### Rollback Plan Template

- Date:
- Change summary:
- Revert path:
- Affected files/configs/migrations:
- Data-loss risk:
- Rollback validation:
- Owner/agent:
- Status:
- Next review trigger:

### Success Metric Template

- Metric:
- Milestone/outcome:
- Target or expected direction:
- Baseline/source:
- Measurement method:
- Closeout evidence location:
- Owner/agent:
- Status: measured / accepted / blocked / follow-up
- Next review trigger:

### Milestone Exit Report Template

- Date:
- Milestone:
- Operating level:
- Completed scope:
- Validation evidence:
- Governance gates satisfied:
- Known failures:
- Risks/assumptions/debt updated:
- Handoff or snapshot path:
- Alert outcome:
- Next action:

### Retrospective Template

- Date:
- Milestone:
- What went well:
- What failed:
- Surprises:
- Missing context:
- Bad assumptions:
- Useful context:
- Planning time:
- Coding time:
- Testing time:
- Research time:
- Rework:
- Failures:
- Replans:
- Failure causes:
- Follow-up:
