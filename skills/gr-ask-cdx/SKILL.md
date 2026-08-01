---
name: gr-ask-cdx
description: |
  Codex-native, read-only codebase Q&A with grounded path:line citations. Use
  whenever the user asks where repository code lives, how a symbol works, what
  calls or depends on it, how data or control flows through the code, how an
  area is structured, why behavior occurs, or when relevant code changed. Uses
  current GitNexus retrieval when its index is available and degrades honestly
  to ripgrep and direct source reading when it is not.
---

# GR Ask CDX — Codebase Q&A

Answer a natural-language question about the current repository from real code
evidence. Every substantive claim carries a validated `path:line` citation so
the user can inspect it. This skill reads and explains; it never edits code.

## Invocation

```text
gr-ask-cdx <question>
gr-ask-cdx --deep <question>
```

Use `--deep` for architecture overviews, cross-cutting behavior, and multi-hop
flows. If the invocation contains no question, ask what the user wants to know
and stop.

## Step 0 — Establish a read-only repository context

Run only non-mutating preflight checks:

```bash
git rev-parse --show-toplevel
command -v rg || command -v git
```

If the working directory is not inside a Git repository, explain that this
skill answers questions about a repository and stop. Resolve the repository
root and use it as the working directory for every local read.

Discover indexed repositories with GitNexus `list_repos`, following its
pagination until the current repository is found or all pages are exhausted.
Canonicalize the current repository root and every returned repository path,
match by canonical path, and retain the matched repository's exact GitNexus
identifier. Pass that identifier explicitly as `repo` to every later GitNexus
operation; this is required when several repositories are indexed. When the
repository is indexed, read its context resource to check index freshness:

- a present, current index enables **graph mode**;
- an absent or stale index enables **degraded mode** using `rg`, read-only Git
  history commands, and direct file reads.

Missing GitNexus tools, connection failures, malformed responses, or unreadable
context resources also enable degraded mode. Distinguish the reason—unavailable,
absent, or stale—in the answer's confidence note.

In degraded mode, tell the user that textual retrieval can miss dynamic
dispatch, reflection, generated code, and indirect dependencies. Suggest the
`gitnexus-cli` skill for indexing or refreshing, but do not modify the index as
part of this read-only question-answering run.

## Step 1 — Classify and route the question

A question may require more than one route:

| Intent | Typical signal | Graph-mode retrieval | Degraded retrieval |
|---|---|---|---|
| Locate / discover | “where is”, “which file” | `query` | `rg -n` plus source reads |
| Explain a symbol | “how does X work”, “what does X do” | `query`, then `context` | locate definition and read callers/callees |
| Callers / dependents | “what calls X”, “who uses X”, “what breaks” | `impact` or `api_impact` | search references and inspect each call site |
| Flow / trace | “how does A reach B”, “what happens when” | `trace` | follow definitions and references hop by hop |
| Architecture | “how is X structured”, “overview of” | `route_map`, `tool_map`, or schema-aware `cypher` | inspect entry points, directories, imports, and call sites |
| Statement control/data | “what guards this”, “where does this variable flow” | `pdg_query` when its layer is available | read the containing function and trace locally |
| Security taint | “is input reaching this sink”, persisted taint evidence | `explain` | inspect source-to-sink flow directly and qualify limits |
| Why / history | “why does X”, “when did X change” | relevant routes and source, plus `git log -S` and `git blame` | source plus `git log -S` and `git blame` |

GitNexus `explain` is exclusively a persisted taint-finding surface. Never use
it to explain an ordinary symbol; use `context` for that. Treat an empty
`explain` result as absence of a recorded finding, not proof of safety.
`pdg_query` is intra-procedural and may be unavailable when the repository was
indexed without PDG layers; disclose that limitation instead of treating an
empty result as definitive.

## Step 2 — Retrieve evidence

Gather evidence before drafting the answer. Do not answer from prior knowledge
or assumptions.

In graph mode:

1. Pass the retained exact `repo` identifier to every operation, then use
   `query` to discover relevant processes and symbols.
2. Use the route selected above to establish definitions, callers, dependency
   paths, or execution flow.
3. Use `cypher` only after reading the repository schema resource and only for
   questions the higher-level tools do not cover.
4. For history questions, run read-only `git log -S` and `git blame` against the
   relevant source even when graph mode is active; the graph cannot establish
   when or why a change entered history.
5. Open the actual source around every returned location. Graph facts guide
   retrieval; source text establishes the final citation.

In degraded mode:

1. Locate symbols or phrases with `rg -n`. If `rg` is unavailable, use
   `git grep -n` for tracked content or recursive `grep -n` with explicit
   repository-local paths. If none is available, stop with a clear prerequisite
   message instead of pretending degraded retrieval succeeded.
2. Read complete surrounding functions or blocks.
3. Follow referenced names with the available search command selected in step 1.
4. For history questions, use read-only commands such as `git log -S <term> --
   <path>` and `git blame -L <start>,<end> -- <path>`.

For each relevant fact, retain the repository-relative path, exact line number,
symbol, and supporting snippet. If retrieval finds nothing, say so without
inventing an implementation.

### Deep retrieval

For `--deep`, prefer one fresh Codex retrieval subagent so broad evidence
collection is separated from synthesis. Confirm native collaboration operations
are available and inspect current agent capacity. Derive a `run_token` from the
current timestamp plus lowercase hexadecimal entropy, using only lowercase
letters, digits, and underscores. Spawn the agent with the unique legal task
name:

```text
gr_ask_<run_token>_retrieval
```

Give it the absolute repository root, the exact question, the graph/degraded
mode, the retained exact GitNexus `repo` identifier when graph mode is active,
the retrieval routes above, and this evidence contract. Require it to:

- remain read-only and create no files;
- inspect source for every graph-derived location;
- return concise findings with repository-relative `path:line` citations and
  supporting snippets;
- distinguish graph facts, source facts, and inferences;
- pass the supplied `repo` identifier to every GitNexus operation;
- avoid answering beyond the evidence it collected.

Wait for that fresh agent and synthesize its findings; do not delegate the final
answer. If subagents are unavailable or capacity prevents spawning one, perform
the same deep retrieval inline and disclose reduced parallelism. Never reuse an
agent carrying context from an unrelated task.

## Step 3 — Validate citations

Before answering, validate every proposed `path:line` citation:

1. resolve the path beneath the repository root and reject paths that escape it;
2. confirm the file exists and is readable;
3. confirm the cited line number is a positive integer within the file;
4. reread a small surrounding range and verify it supports the associated
   claim;
5. use repository-relative paths in the response.

Correct stale graph line numbers from the source when possible. If a claim has
no valid supporting location, drop it or label it explicitly as an inference;
never fabricate or retain an invalid citation. A citation to a definition does
not by itself prove runtime behavior—cite the call path or controlling logic as
well when that distinction matters.

## Step 4 — Answer

Use this structure:

```markdown
**<direct answer in 1–3 sentences>**

<explanation that walks through the mechanism, each claim tied to a citation>

### Evidence
- `path/to/file.py:42` — <what this line or block establishes>
- `path/to/other.go:88` — <what this line or block establishes>

### If you want to go deeper
- <optional follow-up question or related area, only when genuinely useful>
```

Every factual claim about the repository maps to at least one validated
citation. General programming knowledge may be uncited but should be rare.
Prefer showing the concrete code path over asserting a conclusion. Distinguish
graph-backed relationships from conclusions inferred through textual search.

State confidence honestly. If the question is ambiguous, answer the most likely
reading and note the alternative; ask a clarifying question only when the
readings would materially change the answer.

## Read-only guardrails

- Do not edit, create, delete, format, stage, commit, stash, or push files.
- Do not run tests, builds, generators, package installation, indexing, or any
  command that may write caches or generated output.
- Do not use mutating Git or GitNexus operations.
- Do not create persistent state between invocations.
- Do not expose secrets encountered while reading; cite the relevant code
  structure without reproducing secret values.
- Never claim that absence from a graph or text search proves absence at
  runtime.
