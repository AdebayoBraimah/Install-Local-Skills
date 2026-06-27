---
name: obsidian-graphrag-index
description: Use for setting up, preparing, validating, indexing, querying, updating, or troubleshooting the vault-local Microsoft GraphRAG workflow under .vault-graphrag. Use this whenever the user asks to build the GraphRAG graph, refresh/rebuild the index, query GraphRAG, inspect GraphRAG status, or asks whether GraphRAG indexing/querying has been run.
---

# Obsidian GraphRAG Index

Use this skill for the vault-local Microsoft GraphRAG workflow in `.vault-graphrag/`.

Assume commands run from the Obsidian vault root. If the current directory does not contain `.vault-graphrag/`, first locate and `cd` to the vault root. If the user wants to install GraphRAG into a new vault, use the bootstrap command below.

## Rules

- Run the wrapper scripts for the user instead of only describing commands.
- Do not run paid index/query operations unless the user explicitly asks for them.
- Paid indexing must include `--allow-paid-run`.
- Paid querying must include `--allow-paid-query`.
- Never print or log `.vault-graphrag/workspace/.env` contents.
- Use LlamaIndex skill/routing for `.vault-llamaindex-rag/`; this skill is only for GraphRAG.

## Lifecycle

GraphRAG is a staged workflow. Do not imply that every query rebuilds the graph.

0. **Bootstrap** creates `.vault-graphrag/` in a new vault from the bundled template. Do this only when the target vault does not already have `.vault-graphrag/`.
1. **Setup** creates or validates the dedicated `obsidian-graphrag` conda environment and renders workspace settings.
2. **Prepare input** converts vault Markdown into `.vault-graphrag/workspace/input/obsidian_graphrag_input.json`. This is offline and should be rerun when notes change enough to matter.
3. **Index** builds or refreshes the GraphRAG graph from the prepared JSON. This is the expensive paid graph-building step and requires `--allow-paid-run`.
4. **Query** asks questions against the existing indexed graph. Queries can still be paid model calls, but they should not rebuild the graph.

Default query mode for synthesis is `--method global`. Use LlamaIndex, not GraphRAG, for fast local note retrieval.

## Commands

Bootstrap a new vault from the installed skill template:

```bash
~/.agents/skills/obsidian-graphrag-index/scripts/install_into_vault.sh /path/to/vault
```

Preview bootstrap without writing:

```bash
~/.agents/skills/obsidian-graphrag-index/scripts/install_into_vault.sh /path/to/vault --dry-run
```

Replace an existing `.vault-graphrag/` only when the user explicitly requests it:

```bash
~/.agents/skills/obsidian-graphrag-index/scripts/install_into_vault.sh /path/to/vault --overwrite
```

Setup:

```bash
bash .vault-graphrag/scripts/setup_graphrag.sh
```

Prepare input dry-run:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/prepare_graphrag_input.py --dry-run --json
```

Prepare input:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/prepare_graphrag_input.py --json
```

Index dry-run:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/index_graphrag.py --dry-run --json
```

Paid index:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/index_graphrag.py --method fast --allow-paid-run
```

Query dry-run:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/query_graphrag.py "query text" --method global --dry-run --json
```

Paid query:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/query_graphrag.py "query text" --method global --allow-paid-query --json
```

Offline validation:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/validate_graphrag.py --json
```
