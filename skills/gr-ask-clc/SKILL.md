---
name: gr-ask-clc
description: |
  Gr-style natural-language codebase Q&A with citations. Use when the user
  invokes /gr-ask-clc, asks "how does X work", "where is X", "what calls X", "why
  does X happen", or any question that needs a grounded answer about *this*
  codebase rather than general knowledge. Classifies the question, retrieves
  evidence from the gitnexus knowledge graph (degrading to ripgrep when the graph
  is unavailable), and answers with every claim backed by a `file:line` citation.
version: 0.1.0
---

# GR Ask — Codebase Q&A

Answer a natural-language question about the current repository, grounded in real
code. Every substantive claim carries a `path:line` citation so the user can verify
it. This is the local analogue of Gr's codebase chat.

This skill reads and explains. It never edits code.

## Invocation

- `/gr-ask-clc <question>` — answer the question about this repo.
- `/gr-ask-clc --deep <question>` — dispatch a retrieval subagent for broad or
  multi-hop questions (architecture overviews, cross-cutting flows).
- If invoked with no question, ask the user what they want to know and stop.

## Step 0 — Preflight

```bash
git rev-parse --show-toplevel >/dev/null 2>&1 && echo "REPO_OK" || echo "NOT_A_GIT_REPO"
command -v rg >/dev/null 2>&1 && echo "RG_OK" || echo "RG_MISSING"  # ripgrep fallback
```

- `NOT_A_GIT_REPO`: this skill answers questions about a repository — tell the user
  to run it inside one, and stop.
- Check the graph: call `mcp__gitnexus__list_repos`. If this repo is indexed →
  **graph mode**. If absent/stale → **degraded mode** (retrieval via `rg`/`grep` +
  reading files); tell the user answers will be lower-confidence and suggest indexing
  via the `gitnexus-cli` skill.

## Step 1 — Classify the question

Route the question to a retrieval strategy (a question may hit several):

| Intent | Signal | Primary retrieval |
|---|---|---|
| **Locate** | "where is", "which file" | `mcp__gitnexus__query` / `search_code`; `rg` in degraded mode |
| **Explain** | "how does X work", "what does X do" | `mcp__gitnexus__explain` + `context` on the symbol |
| **Callers** | "what calls X", "who uses X" | `mcp__gitnexus__impact` / `api_impact` |
| **Flow / trace** | "how does data get from A to B", "what happens when" | `mcp__gitnexus__trace` |
| **Architecture** | "how is X structured", "overview of" | `mcp__gitnexus__route_map` / `tool_map` / `cypher` graph queries |
| **Why / history** | "why does X", "when did X change" | code + `git log -S`/`git blame` on the relevant lines |

## Step 2 — Retrieve evidence

Gather concrete evidence before writing a word of the answer. Do not answer from
prior knowledge or assumption — if you can't cite it, you don't claim it.

- **Graph mode:** call the tools from the routing table. Prefer graph facts
  (callers, dependents, definitions) over guesses. Use `mcp__gitnexus__cypher` /
  `query` for anything the higher-level tools don't cover.
- **Degraded mode:** `rg -n <symbol>` to locate; read the surrounding functions;
  follow references by grepping their names. Trace flows by reading, not guessing.
- **`--deep`:** dispatch an `Explore` (or `general-purpose`) Agent to fan out the
  retrieval across the codebase and return cited excerpts; synthesize from its
  findings. Use this when the question spans many files or needs multi-hop tracing.

Collect, for each relevant location: `path:line`, the symbol, and the snippet that
supports the answer. If retrieval turns up nothing, say so — do not fabricate.

## Step 3 — Answer

Structure the reply:

```markdown
**<direct answer in 1–3 sentences>**

<explanation that walks through the mechanism, each claim tied to a citation>

### Evidence
- `path/to/file.py:42` — <what this line/block establishes>
- `path/to/other.go:88` — <…>

### If you want to go deeper
- <optional follow-up question or related area, only if genuinely useful>
```

Rules:
- Every factual claim about the code maps to at least one citation. Uncited claims
  are only allowed for general programming knowledge, and should be rare.
- State confidence honestly. In degraded mode, or when the graph is stale, say the
  answer is based on textual search and may miss dynamic dispatch / reflection.
- Prefer showing the reader the exact code path over asserting a conclusion.
- If the question is ambiguous, answer the most likely reading and note the
  alternative — do not stall on a clarifying question unless the readings diverge
  materially.

## Scope guardrails

- Read-only. Never edits code or repo state.
- No persistent state between invocations.
- Distinguishes graph-backed facts from text-search inferences in the answer.
- Never fabricates a citation — if a claim can't be grounded, it is dropped or
  flagged as an assumption.
