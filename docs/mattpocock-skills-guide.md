# Engineering Skills Guide: Matt Pocock's `mattpocock/skills`

The 13 skills installed by `./install-skills.sh --eng` are a curated subset of [`mattpocock/skills`](https://github.com/mattpocock/skills), Matt Pocock's "anti-failure toolkit" for coding agents. They target four recurring failure modes: **misalignment** (the agent builds the wrong thing), **verbosity** (rambling code or comments), **non-functional code** (passes locally, breaks elsewhere), and **architectural decay** (small additions that erode structure over time).

## Per-project bootstrap

**Before first use in any new project, run `setup-matt-pocock-skills` once.** It provisions the `## Agent skills` block in `AGENTS.md`/`CLAUDE.md` and the `docs/agents/` layout that **11 of the other 12 skills depend on** for issue-tracker context, triage labels, and domain documentation. Without it, those 11 will silently degrade — they invoke against missing files rather than failing loudly. This is a per-project step, not a per-skill step: once per repo and you are done.

## TL;DR

- **Misalignment** → `grill-me` (or `grill-with-docs`) before planning; `to-prd` before tickets.
- **Non-functional code** → `tdd` during implementation; `diagnose` on regressions.
- **Architectural decay** → `improve-codebase-architecture` for refactors; `zoom-out` before edits to unfamiliar code; `triage` for issue state.

## The 13 skills

### `setup-matt-pocock-skills`

Per-project bootstrap. Writes the `## Agent skills` block into `AGENTS.md`/`CLAUDE.md` and sets up `docs/agents/`. Run once when adopting these skills in a new repo. Skip-this-and-you'll-hit-it signal: the other skills reference files under `docs/agents/` that do not exist yet.

### `tdd`

Enforces a strict red-green-refactor loop: failing test first, minimum code to pass, refactor with the test as a safety net. Targets **non-functional code**. Invoke when starting a new feature or fix where correctness boundaries are clear enough to express as tests up front.

### `diagnose`

Structured debugging for bugs and performance regressions. Builds a hypothesis tree and prunes by observation rather than guessing. Targets **non-functional code**. Invoke on any "it used to work" or "intermittent" symptom — anywhere the cheap fix is to read three more lines and the costly fix is to patch a symptom.

### `grill-me`

Adversarial questioning before planning or coding. The agent challenges the user's framing — "why this approach over X?", "what happens at boundary Y?" — until requirements are pinned down. Targets **misalignment**. Invoke at the very start of any non-trivial task, before writing code or a plan.

### `grill-with-docs`

Same loop as `grill-me`, but the agent also writes/updates the project's `CONTEXT.md` as it goes. Targets **misalignment** with a paper trail. Invoke when the grilling output is worth keeping — onboarding a new collaborator, capturing why a non-obvious decision was made, or seeding a long-running project's context file.

### `improve-codebase-architecture`

Surveys a section of the codebase and proposes structural improvements: extract this, collapse that, move this boundary. Targets **architectural decay**. Invoke when a module has grown organically and is getting hard to reason about, or before adding a substantial new feature.

### `triage`

Treats issue management as a state machine — new, accepted, in-progress, blocked, done — and forces explicit transitions. Targets **misalignment** at the project-management layer. Invoke when an issue tracker has drifted into a fog of "open" tickets with no clear next action.

### `zoom-out`

Adds system-wide context to a code section: who calls it, what it depends on, what invariants surrounding code assumes. Targets **architectural decay** and **non-functional code** at the edit boundary. Invoke before editing unfamiliar code, especially in a monorepo or a module with non-local callers.

### `to-prd`

Converts a conversation into a Product Requirements Document. Targets **misalignment** at the planning-to-PRD handoff. Pairs with `to-issues` for the PRD-to-tickets follow-up. Invoke when a free-form conversation has produced enough alignment to be worth pinning into a written spec.

### `to-issues`

Converts the PRD produced by `to-prd` into a set of GitHub issues. Targets **misalignment** at the PRD-to-execution boundary. Invoke after `to-prd` when the plan is ready to be tracked as discrete tickets.

### `caveman`

Ultra-compressed communication mode. Cuts agent token usage by ~75 % by dropping filler while preserving technical accuracy. Invoke when context budget is tight or when an agent is about to produce a long-running summary.

### `handoff`

Compacts the current conversation into a handoff document so a separate agent (or future you) can pick up the work without re-deriving state. Invoke at natural breakpoints in long sessions.

### `write-a-skill`

Scaffolds a new skill with proper structure, progressive disclosure, and bundled resources. Invoke when extracting a repeated workflow into a reusable skill.

## Suggested workflow

1. **Once per project:** `setup-matt-pocock-skills`.
2. **Before planning:** `grill-me` (or `grill-with-docs` if you want the output persisted).
3. **Before editing unfamiliar code:** `zoom-out`.
4. **During implementation:** `tdd`.
5. **On regressions or weird behavior:** `diagnose`.
6. **Before substantial new work or after sustained organic growth:** `improve-codebase-architecture`.
7. **At the planning-to-PRD handoff:** `to-prd`.
7a. **After PRD, before issue tracking:** `to-issues`.
8. **For ongoing issue hygiene:** `triage`.

The skills compose: `grill-me` → `to-prd` → `to-issues` → `triage` is a planning pipeline; `zoom-out` → `tdd` → `diagnose` is an editing pipeline; `improve-codebase-architecture` is the periodic structural pass.

## Skills we did not include

We omitted upstream skills that fall outside the "discipline" theme of this bundle:

> **Now included (policy reversal):** `to-issues` was previously excluded "to keep the bundle scoped to discipline rather than issue tracking." That rationale has been reversed — the PRD → GitHub-issues handoff is now considered part of the discipline bundle, completing the `grill-me → to-prd → to-issues → triage` planning pipeline. Bundled with `--eng`.

- **`prototype`, `git-guardrails-claude-code`, `migrate-to-shoehorn`, `scaffold-exercises`, `setup-pre-commit`** — out of scope for this bundle (experimental, niche, or orthogonal to the discipline theme).

## A note on `CONTEXT.md`

`CONTEXT.md` is written and updated by `grill-with-docs` and consumed by `zoom-out`. It is **not** auto-created by `setup-matt-pocock-skills` — it appears organically the first time you run `grill-with-docs`. Treat it as a pattern, not a prerequisite: users do not need to pre-create it.

## Bottom line

Run `setup-matt-pocock-skills` once per repo. Reach for `grill-me` and `tdd` first — most of the value lives there. The other 10 are situational tools you invoke when their failure mode actually shows up.
