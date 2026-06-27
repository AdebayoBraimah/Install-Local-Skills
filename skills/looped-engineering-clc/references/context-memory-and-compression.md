# Context Memory and Compression

This file is authoritative for repository memory search, role-specific context windows, conversation compression, context snapshots, context diffs, and repository memory writeback.

Use this layer for substantial coding, Standard work that touches multiple files, Full OS milestones, handoffs, resumes, or any task where prior lessons may prevent repeated mistakes. If a memory tool is unavailable, record that fact in working memory or the handoff instead of blocking.

## Repository Memory Search

Search before substantial coding for prior lessons learned, common pitfalls, historical bugs, previous failed attempts, successful patterns, ADRs, handoffs, risks, and assumptions.

Use this exact repository memory search order:

1. `codebase-memory-mcp`, if installed and relevant.
2. GitNexus, if available for the repository.
3. Graphify only when the user explicitly instructs Graphify.
4. Local Markdown/repository search using `rg` across ADRs, plans, specs, handoffs, docs, tests, and known engineering ledgers.

Record search scope, unavailable tools, evidence found, evidence not found, and confidence. For Lite work, local search is optional unless the request explicitly references prior context or repository rules require it.

## Role-Specific Context Windows

| Role | Include | Exclude by default |
| --- | --- | --- |
| Planner | Vision, roadmap, architecture, ADRs, constraints, current milestone, acceptance criteria, known risks, active assumptions. | Full file dumps unrelated to the current milestone. |
| Implementer | Relevant files, acceptance criteria, current slice, tests, commands, changed-files expectations, local conventions. | Broad research history unless it changes implementation. |
| Tester | Changed files, expected behavior, regression suite, acceptance criteria, failure classifications, validation commands. | Design alternatives already rejected unless they explain expected behavior. |
| Architecture reviewer | Dependency graph, repository intelligence output, fitness functions, ADRs, drift reports, public API boundaries, coupling evidence. | Low-level implementation details not tied to boundaries or risk. |
| Judgement reviewer | Stated goal, inferred goal, assumptions, options, risks, reversibility, success signals, stop conditions. | Implementation minutiae before the goal is clarified. |

## Conversation Compression

Use this format when context pressure grows, a milestone spans sessions, or a handoff must preserve the work without raw chat history:

- Project summary: repository or skill, current objective, and operating level.
- Current state: active branch or filesystem location, current slice, changed files, and current blocker if any.
- Completed work: decisions made, files changed, tests run, artifacts written.
- Remaining work: next concrete actions, open tasks, and validation still required.
- Validation status: commands, results, known failures, residual risk, and unavailable validators.
- Lessons learned: pitfalls, successful patterns, unexpected constraints, and stale assumptions corrected.
- Open questions: decisions needed, owner, impact, and deadline or trigger.
- Next action: one executable step for the next agent/session.

## Context Snapshot Template

Create context snapshots at Full OS milestone boundaries, handoff-heavy pauses, or when a long-running Standard milestone needs durable resume context.

- Date:
- Owner/agent:
- Operating level:
- Architecture state:
- Working memory:
- Relevant ADRs:
- Active assumptions and risks:
- Outstanding work:
- Validation status:
- Rollback information:
- Memory searched:
- Memory writeback completed:
- Next review trigger:

## Context Diff Template

Use context diffs after meaningful replans, architecture shifts, or milestone completion:

- Added assumptions:
- Removed assumptions:
- New risks:
- Resolved risks:
- New modules:
- Changed architecture:
- New dependencies:
- Changed invariants:
- Validation strategy changes:
- Follow-up writeback targets:

## Repository Memory Writeback Rules

Write back after Full OS milestones, meaningful handoffs, architecture decisions, resolved high-impact risks, repeated pitfalls, or durable lessons that future agents should find. Prefer existing repository conventions. Create `docs/engineering/*` only for Full OS or milestone work, or when accepted by repository/user convention; otherwise record the writeback in the OS temp handoff and note the skipped durable target.

Writeback targets:

- ADRs for durable architectural decisions.
- `docs/engineering/assumptions.md` for assumption changes.
- `docs/engineering/risks.md` for risk changes.
- `docs/engineering/technical-debt.md` for postponed debt.
- `docs/engineering/health.md` for milestone health.
- Context snapshots under `docs/engineering/context-snapshots/`.
- OS temp handoff files unless the repository has a handoff convention.

Every writeback entry should include date, source/evidence, confidence, owner/agent, status, and next review trigger when applicable.

## Working Memory Minimums

- Lite: current task, files touched, validation result, and stop condition if any.
- Standard: current goal, current slice, assumptions, risks, files touched, validation status, next action, and unavailable memory tools.
- Full OS: Standard memory plus repository memory search results, context snapshot/diff when triggered, governance gate status, consensus status, rollback information, telemetry when practical, and repository memory writeback status.
