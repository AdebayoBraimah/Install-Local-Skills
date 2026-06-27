# GraphRAG Runbook

Use GraphRAG when you want slower, higher-level synthesis over the vault. Use `.vault-llamaindex-rag/` for routine local semantic retrieval.

## Normal Run

1. Run setup:

   ```bash
   bash .vault-graphrag/scripts/setup_graphrag.sh
   ```

2. Put the rotated OpenAI key in `.vault-graphrag/workspace/.env`.

3. Prepare the input JSON:

   ```bash
   bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/prepare_graphrag_input.py --json
   ```

   If Google Drive files are cloud-backed and you want to wait longer for hydration, raise the per-file read cap:

   ```bash
   GRAPHRAG_FILE_READ_TIMEOUT_SECONDS=5 bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/prepare_graphrag_input.py --json
   ```

4. Dry-run the index command:

   ```bash
   bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/index_graphrag.py --dry-run --json
   ```

5. Run the paid index only when the corpus preview looks right:

   ```bash
   bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/index_graphrag.py --method fast --allow-paid-run
   ```

## Troubleshooting

- If `run_in_env.sh` reports that `active_env.json` is missing, run setup again.
- Setup uses the dedicated conda environment `obsidian-graphrag`; inspect `.vault-graphrag/logs/` if provisioning fails.
- If a paid command exits with code `2`, check for the explicit allow flag and a real `GRAPHRAG_API_KEY` in `.vault-graphrag/workspace/.env`.
- If the staged corpus is unexpectedly small, inspect `.vault-graphrag/config/ignore_patterns.txt` and run `prepare_graphrag_input.py --dry-run --json`.
