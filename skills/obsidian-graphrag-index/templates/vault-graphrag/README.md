# Obsidian Microsoft GraphRAG

This directory contains a separate, infrequent Microsoft GraphRAG synthesis workflow for the academic Obsidian vault. It does not replace `.vault-llamaindex-rag/`, which remains the fast local retrieval workflow.

## Safety Contract

- Runtime secrets live only in `.vault-graphrag/workspace/.env`.
- Keep `.vault-graphrag/workspace/.env` untracked. Rotate any pasted key before running a paid index or query.
- Indexing requires `--allow-paid-run`.
- Querying requires `--allow-paid-query`.
- Dry-runs do not require GraphRAG credentials.

Default models:

- Chat/model: `gpt-5-nano`
- Embeddings: `text-embedding-3-small`

## Setup

```bash
bash .vault-graphrag/scripts/setup_graphrag.sh
```

Setup creates or updates a dedicated conda environment named `obsidian-graphrag`. If this vault also has `.vault-llamaindex-rag/` and an `obsidian-rag` environment, setup validates and snapshots those first; otherwise it skips the LlamaIndex checks. It does not install GraphRAG into `obsidian-rag`.

Create the local env file after setup:

```dotenv
GRAPHRAG_API_KEY=replace-with-rotated-key
GRAPHRAG_MODEL=gpt-5-nano
GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small
```

## Prepare Input

Preview the Markdown corpus without writing files:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/prepare_graphrag_input.py --dry-run --json
```

Stage the actual GraphRAG JSON input:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/prepare_graphrag_input.py --json
```

Cloud-backed Google Drive files that do not hydrate quickly are skipped and recorded in the manifest warnings. The per-file read cap defaults to `0.5` seconds and can be changed for a fuller pass:

```bash
GRAPHRAG_FILE_READ_TIMEOUT_SECONDS=5 bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/prepare_graphrag_input.py --json
```

This writes:

- `.vault-graphrag/workspace/input/obsidian_graphrag_input.json`
- `.vault-graphrag/manifests/graphrag_input_manifest.json`

## Index And Query

Inspect the index command without credentials:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/index_graphrag.py --dry-run --json
```

Run a paid fast index:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/index_graphrag.py --method fast --allow-paid-run
```

Inspect a query without credentials:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/query_graphrag.py "query text" --method global --dry-run --json
```

Run a paid query:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/query_graphrag.py "query text" --method global --allow-paid-query --json
```

## Validate

Offline validation:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/validate_graphrag.py --json
```

Paid-readiness validation:

```bash
bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/validate_graphrag.py --paid --json
```

## Documentation Sources

- Microsoft GraphRAG inputs: <https://microsoft.github.io/graphrag/index/inputs/>
- Microsoft GraphRAG YAML config: <https://microsoft.github.io/graphrag/config/yaml/>
- Microsoft GraphRAG CLI: <https://microsoft.github.io/graphrag/cli/>
