# Routing and Consensus

This file is authoritative for skill and tool routing, routing precedence, and multi-agent consensus.

Use the most specific route that matches the task, then apply consensus only when the selected operating level or risk requires it. Consensus is not required for Lite work unless risk escalates.

## Routing Matrix

| Route | Trigger |
| --- | --- |
| `judgement-engineering-cdx` | Fuzzy, contradictory, high-impact, under-specified, hidden-assumption driven, or drifting goals. |
| `brainstorming` | Vague product/design direction, unclear solution space, or multiple plausible approaches. |
| `context7` | Current library/framework/API behavior, uncertain package usage, recently changing docs, code examples, and API usage where package behavior matters. |
| `web-research` | Current public web facts, vendor/product documentation, pricing/product choices, current ecosystem checks, and non-academic multi-source web checks. |
| `deep-research` | Broader multi-source synthesis with citations, source comparison, or deeper research reports. |
| `openai-docs` | OpenAI product/API/model behavior, Codex/OpenAI platform usage, current OpenAI documentation, and OpenAI-specific implementation questions. |
| `deep-research-academic` | Academic sources, scholarly synthesis, and research methodology where a literature-review route is useful. |
| `academic-researcher` | Academic paper review, methodology critique, and scholarly writing support. |
| `lit-review-cdx` | Scoped literature reviews that need search, triage, summarize, synthesize, and verify phases. |
| `research-engineer-ai-ml` | AI/ML reproducibility, baselines, ablations, evaluation systems, scalable training, or research-software rigor. |
| `handoff` | Context pressure, pause, transfer, milestone closure, unresolved decisions, or any point where another agent/session must resume. |
| `improve-codebase-architecture` | Architecture improvement scans, deepening opportunities, structural reports, and guided architecture improvement workflows. |
| `superpowers:subagent-driven-development` | Delegated multi-agent implementation workflows, parallel worker planning, subagent ownership boundaries, and worker integration when that superpower is installed or available. |
| `superpowers:executing-plans` | Execution of an approved plan using the repository's Superpowers workflow conventions when that superpower is installed or available. |
| `diagnose` | Failing tests, unclear behavior, non-local failures, or unknown root cause. |
| `gitnexus-exploring` | Unfamiliar codebase exploration, architecture tracing, call-flow understanding, and "how does this work" questions when GitNexus is available. |
| `gitnexus-debugging` | Graph-backed root-cause tracing when GitNexus is available. |
| `gitnexus-impact-analysis` | Blast radius before symbol/API/refactor edits when GitNexus is available. |
| `gitnexus-refactoring` | Rename, extract, move, split, or restructure work when GitNexus is available. |
| `gitnexus-guide` | Questions about GitNexus capabilities, schema, MCP resources, graph querying, or workflow usage. |
| `gitnexus-cli` | GitNexus CLI indexing, status, analyze/reanalyze, cleaning, wiki generation, and repository index maintenance. |
| `graphify` | Graphify only when the user explicitly instructs Graphify. |
| Inline architecture reviewer fallback | Use when no architecture-review skill is available; inputs are goal, relevant modules/files, dependency evidence, ADRs, risks, and tests; output is an architecture review note with boundary, coupling, testability, drift, and recommendation sections. |
| `writing-plans` | Multi-step, multi-file, risky, tests/docs/migrations/integration points. |
| `plan-review-cdx` | Substantial plan before execution, Full OS plan, or bounded Standard formal-review trigger. |
| `tdd` | Behavior changes, bug fixes, reproducible research/evaluation code. |
| `alert-me` | Success, blocker, validation failure, human decision, handoff, or milestone completion. |

## Routing Precedence

- Use `context7` first for library/framework/package documentation, code examples, and API usage where current package behavior matters.
- Use `openai-docs` before general web or research routes for OpenAI products, OpenAI APIs, Codex behavior, OpenAI models, or OpenAI platform documentation.
- Use `web-research` for current public web facts, vendor/product documentation, pricing/product choices, and non-academic multi-source web checks.
- Use `deep-research` when the work needs broader multi-source synthesis with citations or source comparison.
- Use `deep-research-academic`, `academic-researcher`, or `lit-review-cdx` for academic sources, papers, literature review, or research methodology.
- Use `research-engineer-ai-ml` for AI/ML reproducibility, baselines, ablations, evaluation systems, scalable training, or research-software rigor.
- If multiple routes apply, choose the most specific route first: package docs -> product/vendor web docs -> academic literature -> broad synthesis.

## Multi-Agent Consensus Protocol

Consensus is selected by operating level and risk:

- Lite uses no consensus unless risk escalates.
- Standard uses a Plan reviewer for formal-review triggers and an Architecture reviewer for structural/API/dependency changes.
- Full OS uses a Planner, relevant specialist reviewers, and a Plan reviewer before execution.
- Judgement reviewer is required for fuzzy/high-impact goals.
- Architecture reviewer is required for structural, coupling, API, migration, or dependency changes.
- Tester/verifier is required for broad shared behavior or risky validation.

Review result statuses are `pass`, `pass-with-notes`, `revise`, `block`, and `human-decision`.

Minimum signoff:

- Standard formal-review work needs no `block` from required reviewers, and all medium/high/critical findings must be resolved or explicitly accepted.
- Full OS needs `pass` or `pass-with-notes` from required reviewers before implementation.

Conflict handling:

- Critical/high conflicts block implementation until a documented human decision.
- Reversible provisional work is allowed only for non-final containment, evidence gathering, or validation that cannot commit the disputed design.
- Medium conflicts defer to the more specialized reviewer or `plan-review-cdx` execution reviewer and require a documented resolution.
- Low conflicts may be recorded as follow-up.

Re-review triggers: substantive plan changes, architecture changes, scope expansion, new migration/data risk, changed public API semantics, new dependency, validation strategy changes, or any unresolved medium-or-higher finding.

If subagents are unavailable, use inline named review roles with the same statuses, inputs, findings, confidence, and signoff expectations. Use actual subagents when available and authorized by the user/request or by a skill such as `plan-review-cdx`.

## Consensus Roles

### Planner

- Trigger: Full OS work, multi-milestone planning, unclear milestone sequencing, or major plan revision.
- Invocation mechanism: use a planning skill such as `writing-plans` when applicable, a subagent when available, or an inline Planner role.
- Required input context: goal, acceptance criteria, repository constraints, architecture notes, ADRs, risks, assumptions, validation commands, and current milestone.
- Expected output artifact: implementation plan or plan delta.
- Fallback when subagents are unavailable: write an inline Planner note with assumptions, ordered slices, files, validation, risks, and confidence.

### Judgement Reviewer

- Trigger: fuzzy, contradictory, high-impact, under-specified, hidden-assumption driven, or drifting goals.
- Invocation mechanism: use `judgement-engineering-cdx`, or an inline Judgement reviewer role if the skill is unavailable.
- Required input context: stated goal, inferred goal, assumptions, options, risks, reversibility, success signals, and stop conditions.
- Expected output artifact: judgement brief or judgement review note.
- Fallback when subagents are unavailable: write an inline Judgement reviewer note with options, recommendation, reversibility, and confidence.

### Architecture Reviewer

- Trigger: structural, coupling, public API, migration, dependency, boundary, testability, or architecture-drift risk.
- Invocation mechanism: use an architecture-review skill when available, GitNexus impact/exploration when available, or an inline Architecture reviewer role.
- Required input context: goal, relevant modules/files, dependency evidence, repository intelligence output, ADRs, fitness functions, risks, and tests.
- Expected output artifact: architecture review note with boundary, coupling, testability, drift, and recommendation sections.
- Fallback when subagents are unavailable: perform the inline architecture reviewer fallback defined in the routing matrix and record confidence.

### Plan Reviewer

- Trigger: substantial plan, Full OS plan, bounded Standard formal-review trigger, or re-review trigger.
- Invocation mechanism: use `plan-review-cdx`; if it cannot run, use an inline Plan reviewer role and record the limitation.
- Required input context: current plan, acceptance criteria, relevant specs, risks, assumptions, validation strategy, and known constraints.
- Expected output artifact: `plan-review-cdx` review result or inline plan review result.
- Fallback when subagents are unavailable: write an inline Plan reviewer result with findings by severity, required corrections, status, and confidence.

### Tester/verifier

- Trigger: broad shared behavior, elevated but locally testable validation risk, reproducible research/evaluation code, or unresolved failure classification.
- Invocation mechanism: use test-specific skills when available, `tdd` for behavior changes, `diagnose` for unclear failures, or an inline Tester/verifier role.
- Required input context: changed files, expected behavior, regression suite, acceptance criteria, validation commands, known failures, and residual risk.
- Expected output artifact: verification note with commands, results, failures, failure classification, and residual risk.
- Fallback when subagents are unavailable: run available local validation and write an inline Tester/verifier note with confidence and gaps.
