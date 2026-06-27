# Context Orchestration

Treat context as an engineered artifact. This file covers the Context Orchestrator, context ranking, conflict detection, prompt assembly, and SQLite overview. It delegates repository memory search/writeback, role-specific windows, compression, snapshots, and diffs to [context-memory-and-compression.md](context-memory-and-compression.md).

Graphify only when the user explicitly instructs Graphify. Do not run Graphify merely because a repository graph would be useful.

## Context Orchestrator

For each role and phase:

1. determine the agent role and current objective
2. retrieve relevant context
3. rank context
4. detect stale, missing, contradictory, or deprecated context
5. assemble a role-specific context package
6. record what context was supplied
7. update working memory after meaningful changes

## Context Layers

- Persistent knowledge: repository memory tools when available, GitNexus, Graphify only when requested, SQLite, Markdown docs, ADRs, specs, plans, tests, and research notes.
- Working memory: current goal, milestone, slice, files touched, blocker, hypothesis, assumption, next action, active plan, active handoff, validation status.
- Episodic memory: goal, what happened, mistakes, lessons, final decision, related files, ADRs, future advice.
- Semantic memory: concepts and relationships, such as subsystem depends on module or test covers behavior.
- Intent memory: why a milestone, abstraction, API, or algorithm exists.

## Context Ranking

Prioritize:

1. current milestone
2. current slice
3. working memory
4. relevant ADRs
5. repository intelligence output
6. recent handoffs
7. tests
8. documentation
9. research
10. archived episodes

## Validation and Conflict Detection

Before planning or implementation, check whether context is stale, contradictory, incomplete, deprecated, missing, or unsupported by evidence.

Raise conflicts such as:

- ADR says one architecture, docs say another.
- Plan assumes a module exists, code says otherwise.
- Tests encode behavior that contradicts the spec.
- Old handoff conflicts with current repository state.

## Context Dependency Graph

Link: Goal -> Milestone -> ADR -> Assumption -> Risk -> Plan -> Code -> Tests -> Docs -> Handoff.

## SQLite Optional Memory

SQLite is an optional repo-local memory cache when no better project memory exists. Markdown docs, ADRs, plans, and the repository's established memory convention remain source of truth.

Default DB path: `.agent-memory/looped-engineering-cdx.sqlite`.

Suggested tables:

- `facts`
- `working_memory`
- `episodes`
- `relations`
- `assumptions`
- `risks`

Every important fact should include source, date discovered, date verified, confidence, owner/agent, and validity status.

### SQLite Installation

Prefer Conda:

```bash
conda install -y sqlite
```

macOS fallback if Conda is unavailable:

```bash
command -v conda >/dev/null 2>&1 || command -v sqlite3 >/dev/null 2>&1 || brew install sqlite
```

Debian/Ubuntu fallback if Conda is unavailable:

```bash
command -v conda >/dev/null 2>&1 || { sudo apt-get update && sudo apt-get install -y sqlite3 libsqlite3-dev; }
```

Common verification:

```bash
sqlite3 --version
python3 - <<'PY'
import sqlite3
print(sqlite3.sqlite_version)
PY
```

Python `sqlite3` is standard-library backed. Do not install a PyPI package named `sqlite3`; install a Python build with SQLite support if the module is missing.

## Prompt Assembly

When invoking subagents or helper skills, assemble prompts from current goal, working memory, relevant ADRs, repository intelligence, tests, architecture constraints, research/docs, assumptions, risks, and acceptance criteria. Apply context budgeting; do not dump everything into every prompt.
