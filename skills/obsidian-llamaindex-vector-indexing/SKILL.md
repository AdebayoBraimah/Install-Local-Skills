---
name: obsidian-llamaindex-vector-indexing
description: Use the local LlamaIndex vector RAG tooling for an Obsidian vault. Trigger whenever the user asks to set up, validate, rebuild, update, search, query, refresh, troubleshoot, inspect, or install the local vector index; scaffold `.vault-llamaindex-rag/` if missing, then run the appropriate shell wrapper instead of only describing the command.
---

# Obsidian LlamaIndex Vector Indexing

Use this skill when the user asks to build, update, validate, search, or troubleshoot the local LlamaIndex vector index for the vault.

## Agent Behavior

When this skill triggers, prefer doing the action for the user by running the appropriate shell wrapper from the vault root. Do not merely tell the user which command to run unless they explicitly ask for instructions only.

Before running any wrapper, check whether `.vault-llamaindex-rag/` exists in the current vault/repo root. If it is missing, scaffold it first:

```bash
~/.agents/skills/obsidian-llamaindex-vector-indexing/scripts/install_scaffold.sh "$PWD"
```

The scaffold installer copies the bundled template into the target vault. It does not copy Chroma vectors, manifests, caches, or logs, and it does not overwrite an existing `.vault-llamaindex-rag/` directory.

Default mappings:

- Setup or dependency check: run `./.vault-llamaindex-rag/setup_llama-index.sh`
- Validate the workflow: run `./.vault-llamaindex-rag/validate_llama-index.sh`
- Refresh after note changes: run `./.vault-llamaindex-rag/update_llama-index.sh`
- Preview refresh impact: run `./.vault-llamaindex-rag/update_llama-index.sh --dry-run`
- Search/query the vault: run `./.vault-llamaindex-rag/search_llama-index.sh "query" --top-k 5`
- Rebuild from scratch: run `./.vault-llamaindex-rag/rebuild_llama-index.sh --force` only when the user asks for a rebuild/reset or approves it.

If the requested action is ambiguous, choose the least destructive useful command: `update` for refresh/index requests, `validate` for health checks, and `search` for retrieval questions.

## How It Runs

The skill is guidance; the shell wrappers do the work. The wrappers invoke the shared conda environment `obsidian-rag` with `conda run`, so manual activation is not normally needed.

Chroma is file-backed, not a persistent server. Index/update commands run once and persist vectors to `.vault-llamaindex-rag/chroma_db/`; later searches reopen that local database.

In a new vault, scaffold first, then run setup:

```bash
~/.agents/skills/obsidian-llamaindex-vector-indexing/scripts/install_scaffold.sh "$PWD"
./.vault-llamaindex-rag/setup_llama-index.sh
```

## Watch Mode Note

Do not start `watch_llama-index.sh` unless the user explicitly asks for continuous watching/background updates. Watch mode is long-running and should be treated separately from normal one-shot update/search/validate commands.

## Commands

Run commands from the vault root:

```bash
./.vault-llamaindex-rag/setup_llama-index.sh
./.vault-llamaindex-rag/rebuild_llama-index.sh --force
./.vault-llamaindex-rag/update_llama-index.sh
./.vault-llamaindex-rag/update_llama-index.sh --dry-run
./.vault-llamaindex-rag/validate_llama-index.sh
./.vault-llamaindex-rag/search_llama-index.sh "query" --top-k 5
./.vault-llamaindex-rag/watch_llama-index.sh --debounce 2
```

## Safety

- Do not modify vault notes during indexing.
- Keep Chroma, manifest, cache, validation, and log paths inside `.vault-llamaindex-rag/`.
- Rebuild requires `--force` unless `allow_rebuild_delete: true` is set in config.
- Search is retriever-only and must not require OpenAI credentials.

## Implementation Notes

- Config paths are resolved relative to the directory containing `config.yaml`.
- The Chroma collection is `obsidian_llamaindex_vault`.
- The shared conda environment is `obsidian-rag`.
- Incremental updates delete Chroma rows by `source_path` and re-add changed files.
