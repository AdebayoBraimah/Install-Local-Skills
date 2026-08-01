---
name: gr-verify-cdx
description: |
  Codex-native Gr/TREX-style runtime validation of code-review findings. Use
  when the user wants to empirically confirm that a reported bug reproduces,
  asks to prove or disprove a gr-review-cdx finding, supplies a findings report,
  or wants a minimal regression test with observed output. Runs repository tests
  only inside a unique detached worktree and returns REPRODUCED,
  NOT-REPRODUCED, or INCONCLUSIVE without modifying the user's checkout.
---

# GR Verify CDX — Runtime Validation Of Findings

Empirically validate reasoned code-review findings. Write a minimal test that
asserts correct behavior, run it against the reviewed code in an isolated
worktree, and report what actually happened. A predicted assertion failure
confirms the bug; a pass or unrelated failure does not.

This skill runs the repository's own test tooling. It never writes generated
tests into the user's checkout and never commits unless the user separately asks.

## Invocation

```text
gr-verify-cdx --from-report <path>
gr-verify-cdx "<claimed bug, location, and failure scenario>"
gr-verify-cdx --keep-tests <finding source>
```

- `--from-report <path>` reads findings from a `gr-review-cdx` report or a
  findings JSON file.
- An ad-hoc description must identify enough code and behavior to derive a test.
- `--keep-tests` authorizes retaining confirmed regression tests after teardown.

If no finding source is supplied, ask what to verify and stop.

Parse whole tokens: `--keep-tests` sets retention; `--from-report` consumes the
next token as its path and is invalid when that operand is missing; all remaining
text is one ad-hoc finding description. Reject conflicting or extra report paths.

For JSON input, accept either a top-level findings array or an object whose
`findings` field is an array. For Markdown, extract only structured GR Review
entries with a `path:line`, title, severity section, body, and suggestion; do not
turn arbitrary prose into findings. JSON findings retain their exact severity.
The Markdown report groups CRITICAL with HIGH and MEDIUM with LOW, so preserve
that combined bucket without guessing an exact value. Normalize to:

```json
{
  "file": "repository/relative/path",
  "line": 42,
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
  "severity_bucket": "CRITICAL_OR_HIGH|MEDIUM_OR_LOW|null",
  "title": "claimed defect",
  "body": "concrete failure scenario",
  "suggestion": "expected corrective behavior"
}
```

For JSON, require an exact supported `severity` and set `severity_bucket` to null.
For Markdown, set `severity` to null and retain the report heading as
`severity_bucket`; use the bucket only for processing order. Reject malformed
JSON, an empty report, paths escaping the repository, nonpositive lines, and
unsupported severities/buckets. If an otherwise valid finding lacks enough
behavioral detail to derive an observable correct-behavior assertion, report that
finding INCONCLUSIVE rather than inventing a test.

## Step 0: Preflight

Resolve the repository root and record its state without changing it:

```bash
repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 1
git -C "$repo_root" status --porcelain=v1 -z
```

If the current directory is not in a Git repository, stop. Resolve each input
path and ensure it is readable before creating a sandbox.

Detect the stack and narrowest valid test command by inspecting repository files:

| Signal | Runner |
|---|---|
| `pytest.ini`, pytest configuration/dependency in `pyproject.toml`, or a documented pytest wrapper | repository-configured `pytest` |
| `tox.ini` | the tox environment and command defined by the repository |
| `package.json` | `scripts.test`, otherwise configured Jest/Vitest/Node test |
| `go.mod` | `go test` for the target package |
| `Cargo.toml` | `cargo test` for the target test |
| `pom.xml` | Maven target test |
| `build.gradle` or `build.gradle.kts` | Gradle target test |

The presence of `pyproject.toml` alone does not prove pytest, and tox may invoke
unittest or arbitrary commands. Require evidence from runner configuration,
declared dependencies, repository scripts/wrappers, CI, or documentation. Do not
guess when several runners are plausible; ask for the command or return setup-
INCONCLUSIVE. If no runnable harness exists, offer static re-derivation and explain
that empirical verification cannot proceed.

## Step 1: Create Owned Isolation

Generate a run token from a timestamp plus lowercase hexadecimal entropy. Resolve
an absolute run root outside the reviewed checkout, preferably beneath a `.codex`
directory in the checkout's parent:

```text
<repo-parent>/.codex/gr-verify/<repo-slug>-<run-token>/
```

Validate that the run root and sandbox are neither the repository root nor an
ancestor of it. Stop if an exact safe path cannot be established.

Create this manifest before the worktree:

```json
{
  "repo_root": "/absolute/repository",
  "run_root": "/absolute/owned/run-root",
  "sandbox": "/absolute/owned/run-root/worktree",
  "created_by_run": true
}
```

Save the exact NUL-delimited pre-run status as `status-before.bin`. Record
`git rev-parse HEAD` as the base commit. Immediately capture
`git diff --binary HEAD` as `reviewed-state.patch`, compute and record its SHA-256
digest, and do not regenerate it later in the run. Then create a detached worktree:

```bash
git -C "<repo-root>" worktree add --detach "<sandbox>" "<recorded-base-commit>"
```

If `reviewed-state.patch` is non-empty, run `git apply --check` inside the sandbox
before applying that exact frozen patch. Apply it only after the check succeeds,
then verify the sandbox diff hashes to the recorded reviewed state. If the base
commit changed, the check/application fails, or the reconstructed diff does not
match, return INCONCLUSIVE and tear down rather than testing different code. Do
not include or silently invent untracked files. If an untracked file is necessary
to reproduce the finding, ask the user for explicit handling or return
INCONCLUSIVE.

Keep virtual environments, dependency caches, generated tests, and build output
inside the sandbox or run root. Never install globally. Prefer already declared
and locked repository dependencies; ask before a substantial network download.

## Step 2: Verify Each Finding

Process findings from highest to lowest severity.

1. Identify the exact file, symbol, expected correct behavior, and predicted
   failure scenario.
2. Read the relevant code, callers, existing tests, and repository conventions.
   Use the installed `tdd` guidance for idiomatic test construction or
   `diagnose` when reproduction is non-obvious.
3. Write the smallest test in the sandbox that asserts correct behavior. A test
   engineered merely to crash or to assert the buggy output is invalid.
4. Run only that test or test file. Use a broader integration command only when
   the claim itself crosses components and explain why it is necessary.
5. Capture the exact command, exit code, stdout, and stderr beneath the run root.

Classify the observation:

- **REPRODUCED** — the test reaches the claimed code and fails for the predicted
  behavioral reason.
- **NOT-REPRODUCED** — the correct-behavior assertion passes, the claimed input
  cannot reach the code, or the observed failure is unrelated to the finding.
- **INCONCLUSIVE** — the test cannot build or run, dependencies/services are
  unavailable, the reviewed state cannot be recreated, or the behavior is not
  observable with the repository harness.

Retry at most three times only when the generated test itself fails to compile,
collect, or load. A predicted assertion failure is evidence, not a retry trigger.
Never upgrade a reasoned suspicion over contradictory runtime evidence.

## Step 3: Report

Use this format:

```markdown
## GR Verify — <source>

| Finding | Verdict | Evidence |
|---|---|---|
| `file:line` — <title> | ✅ REPRODUCED | test failed: <observed behavior> |
| `file:line` — <title> | ❌ NOT-REPRODUCED | test passed or assumption failed: <reason> |
| `file:line` — <title> | ⚠️ INCONCLUSIVE | <specific blocker> |

### Confirmed bugs (regression tests available)
- `file:line` — <title>
  ```text
  <minimal failing test and relevant observed output>
  ```
```

For every row, report the command and enough output to distinguish an assertion
failure from an environment or test-construction failure.

When `--keep-tests` is active, copy only confirmed regression tests to a unique
`<repo-root>/.gr-verify/<run-token>/` directory before teardown. Check whether
that destination is ignored by Git and disclose when it is not. Without
`--keep-tests`, preserve test text in the report but keep no generated files in
the repository.

## Step 4: Teardown Always

Teardown runs after success, partial failure, and error.

1. Read the manifest and re-resolve every path.
2. Confirm the sandbox is the exact recorded worktree and remains outside the
   repository root.
3. Remove it through `git -C <repo-root> worktree remove --force <sandbox>`.
4. Run `git -C <repo-root> worktree prune`.
5. Remove remaining run-owned files only beneath the exact recorded run root.
6. Capture `git status --porcelain=v1 -z` as `status-after.bin` before deleting
   the final run metadata and compare it byte-for-byte with the pre-run snapshot,
   excluding an explicitly retained `.gr-verify/<run-token>/` directory.

If cleanup or status comparison fails, preserve uncertain paths, report them,
and never broaden a deletion target. Do not remove another worktree or branch.

## Scope Guardrails

- Run only repository-owned test tooling and dependencies.
- Install nothing globally.
- Never generate or run tests in the user's checkout.
- Never commit unless the user separately requests it.
- Report observed behavior exactly; empirical evidence overrides speculation.
- Keep retries bounded to test-construction defects.
