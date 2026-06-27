---
name: looped-engineering-cdx
description: Adaptive Lite/Standard/Full OS engineering loop for coding work that needs orientation, planning, execution, verification, reflection, handoff, or alerting. Use when tasks involve multi-file implementation, refactors, architecture improvement, repository maintenance, research software, AI/ML systems, unclear or evolving goals, handoffs, substantial plans, or context-heavy coding work needing minimal user intervention.
---

# Looped Engineering

Use this as an adaptive Engineering OS for substantial engineering work. Lite mode applies when `looped-engineering-cdx` is explicitly invoked for a small task or when a larger workflow downgrades after orientation. Choose Lite, Standard, or Full OS according to blast radius and risk, then keep moving autonomously through the gates required by that selected operating level unless a real human decision is required.

## Control Loop

The control loop is adaptive to the selected operating level. Keep this 14-step sequence as lifecycle vocabulary, but apply gates and artifacts according to Lite, Standard, or Full OS rather than treating every step as mandatory for every task.

1. Intake
2. Context Orchestration
3. Judgement Gate, if needed
4. Research/Brainstorming Gate, if needed
5. Architecture Gate, if needed
6. Planning Gate
7. Plan Review Gate using `plan-review-cdx`
8. Execution Loop using TDD when behavior changes
9. Verification Gate
10. Drift/Health/Invariant Gate
11. Reflection/Retrospective
12. Commit or Handoff
13. Alert using `alert-me`
14. Continue or Stop

Invoke `judgement-engineering-cdx` when the goal is fuzzy, incomplete, contradictory, high-impact, poorly specified, hidden-assumption driven, or likely to drift. It may be used multiple times during a long task.

Lite work may skip formal planning and `plan-review-cdx` when requirements are clear, blast radius is low, and repository rules do not require a plan. `plan-review-cdx`, consensus roles, ADR/risk/assumption gates, and other Full OS artifacts are required only for substantial Standard work, Full OS work, or Lite work that escalates in risk.

## Autonomous Defaults

Proceed without user intervention through context gathering, judgement brief, formal planning when required by the selected operating level, `plan-review-cdx` when required by the selected operating level or risk escalation, plan revision, implementation, testing, verification, handoff, and alerting.

Ask the user only for irreversible decisions, destructive operations, credentials/secrets, explicit product priorities, unclear preferences that materially affect outcome, high/critical risk acceptance, public API or data policy decisions, or validation failures that cannot be resolved locally.

Use reversible provisional decisions when possible, and label them.

## Reference Routing

- For operating levels, lifecycle state transitions, transition rules, upgrade/downgrade rules, and per-state artifacts, read [operating-levels-and-state-machine.md](references/operating-levels-and-state-machine.md). For the lifecycle overview, read [workflow-state-machine.md](references/workflow-state-machine.md).
- For phase entry and exit gate summaries, read [phase-gates.md](references/phase-gates.md).
- For the Context Orchestrator and SQLite overview, read [context-orchestration.md](references/context-orchestration.md). For repository memory search/writeback, role-specific windows, compression, snapshots, and diffs, read [context-memory-and-compression.md](references/context-memory-and-compression.md).
- For skill/tool routing, routing precedence, and multi-agent consensus, read [routing-and-consensus.md](references/routing-and-consensus.md). It covers helper-skill routing for `web-research`, `deep-research`, `openai-docs`, `handoff`, `improve-codebase-architecture`, `tdd`, `diagnose`, `gitnexus-exploring`, `gitnexus-impact-analysis`, `gitnexus-debugging`, `gitnexus-refactoring`, `gitnexus-guide`, `gitnexus-cli`, `superpowers:subagent-driven-development`, `superpowers:executing-plans`, and `graphify`. Graphify only when the user explicitly instructs Graphify.
- For `writing-plans`, `plan-review-cdx`, TDD, and execution rules, read [plan-review-and-execution.md](references/plan-review-and-execution.md).
- For ADRs, registers, health, drift, invariants, Knowledge Gap Tracker, Architecture Fitness Functions, Success Metrics, and governance gates/templates, read [engineering-governance.md](references/engineering-governance.md).
- For validation, reflection, commit, and handoff, read [verification-and-closeout.md](references/verification-and-closeout.md).
- For terminal notifications, read [alert-policy.md](references/alert-policy.md).
