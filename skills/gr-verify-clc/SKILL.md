---
name: gr-verify-clc
description: |
  Gr/TREX-style runtime validation of code-review findings. Use when the user
  invokes /gr-verify-clc, wants to empirically confirm a bug is real (not just
  argued), asks to "prove this finding reproduces", or wants to promote gr-review-clc
  findings from reasoned to tested. Takes a finding (or a gr-review findings file),
  writes a minimal test that should fail if the bug is real, runs it in an isolated
  git worktree, and returns a reproduced / not-reproduced / inconclusive verdict with
  the observed output.
version: 0.1.0
---

# GR Verify — Runtime Validation of Findings

Reasoned code review produces plausible bugs; some are false positives. This skill
does what Gr's TREX does: it **empirically confirms** a finding by writing a
test that should fail if the bug is real, running it in a sandbox, and reporting what
actually happened. A reproduced failure is a confirmed bug (with a ready-made
regression test); a passing test is strong evidence of a false positive.

This skill runs the repo's own test tooling. It writes tests into an **isolated git
worktree**, never the user's working tree, and does not commit anything unless asked.

## Invocation

- `/gr-verify-clc --from-report <path>` — verify the findings in a `gr-review-clc`
  report or `/tmp/gr-findings-*.json`.
- `/gr-verify-clc "<description of the claimed bug + location>"` — verify one ad-hoc
  finding.
- `/gr-verify-clc --keep-tests` — leave confirmed failing tests in the worktree /
  copy them out for the user to keep, instead of cleaning up.

If invoked with no finding source, ask what to verify and stop.

## Step 0 — Preflight: repo, language, test runner

```bash
repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "NOT_A_GIT_REPO"; exit 0; }
git -C "$repo_root" diff --quiet && git -C "$repo_root" diff --cached --quiet \
  && echo "TREE_CLEAN" || echo "TREE_DIRTY"
```

Detect the stack and its test command by inspecting the repo (do not assume):
- `pyproject.toml`/`pytest.ini`/`tox.ini` → `pytest`
- `package.json` → the `scripts.test`, else `jest`/`vitest`/`node --test`
- `go.mod` → `go test ./...`
- `Cargo.toml` → `cargo test`
- `pom.xml`/`build.gradle` → `mvn test`/`gradle test`
- else: ask the user for the test command.

If no runnable test harness exists, tell the user; verification cannot proceed
without one (offer to instead do a stronger *static* re-derivation, which is what
`gr-review-clc`'s verifier already does).

## Step 1 — Create an isolated sandbox worktree

Never write or run generated tests in the user's working tree. Use a detached
worktree so the sandbox can't corrupt their state:

```bash
sandbox="$(git -C "$repo_root" rev-parse --show-toplevel)/../gr-verify-sandbox"
git -C "$repo_root" worktree add --detach "$sandbox" HEAD
```

Install/prepare deps in the sandbox as the repo requires (reuse existing
`venv`/`node_modules` by preference; only install if the harness needs it). If the
findings pertain to uncommitted changes, apply that diff into the sandbox first
(`git -C "$repo_root" diff HEAD | git -C "$sandbox" apply`) so you test the code as
reviewed.

## Step 2 — For each finding: red test → run → verdict

Process findings highest-severity first. For each:

1. **Understand the claim:** the file, the symbol, and the concrete failure scenario
   (input → wrong output/crash). If the finding lacks a concrete scenario, derive the
   smallest one that would exercise the claimed defect.
2. **Write a minimal failing test** that asserts the *correct* behavior, so it
   **fails iff the bug is real**. Route to the `tdd` skill for idiomatic test
   construction, or `diagnose` when reproduction is non-obvious. Place the test in the
   sandbox's test tree, following the repo's conventions.
3. **Run just that test** with the detected runner (target the single test/file; do
   not run the whole suite unless the bug is a cross-cutting integration issue).
   Capture stdout/stderr and exit code.
4. **Verdict:**
   - **REPRODUCED** — the test fails exactly as the finding predicts (right error,
     right place). The bug is real; keep the failing test as a regression test.
   - **NOT-REPRODUCED** — the test passes, or fails for an unrelated reason. Strong
     evidence the finding is a false positive; say why (an existing guard, the input
     can't reach it, the assumption was wrong).
   - **INCONCLUSIVE** — couldn't build/run, missing deps, needs external services, or
     the behavior isn't observable via a unit test. Report the blocker; do not guess.

Iterate a bounded number of times (≤3) if a test fails to *build* (vs. fails the
assertion) — a compile error in the test is a test bug, not a verdict.

## Step 3 — Report

```markdown
## GR Verify — <source>

| Finding | Verdict | Evidence |
|---|---|---|
| `file:line` — <title> | ✅ REPRODUCED | test failed: <1-line observed error> |
| `file:line` — <title> | ❌ NOT-REPRODUCED | test passed; <why the finding doesn't hold> |
| `file:line` — <title> | ⚠️ INCONCLUSIVE | <blocker> |

### Confirmed bugs (regression tests available)
- `file:line` — <title>
  ```
  <the failing test + observed output>
  ```
```

Reproduced findings are the ones worth fixing first. If `--keep-tests`, copy the
confirmed failing tests to `<repo_root>/.gr-verify/` (git-ignored) or report their
sandbox paths so the user can move them next to the fix.

## Step 4 — Teardown (always)

```bash
git -C "$repo_root" worktree remove --force "$sandbox" 2>/dev/null
git -C "$repo_root" worktree prune
```
Confirm the user's working tree is untouched (`git -C "$repo_root" status` unchanged
from the pre-run snapshot). Never leave a dangling worktree.

## Scope guardrails

- Runs only the repository's **own** test tooling; installs nothing global.
- All generated tests live in a throwaway worktree — the user's tree is never
  modified, and nothing is committed unless the user asks.
- Reports what was actually observed; never upgrades a NOT-REPRODUCED to a bug on
  reasoning alone. Empirical verdicts override reasoned ones.
- Bounded retries on test *build* errors; a real assertion failure is a verdict, not
  a retry trigger.
