# Obsidian LlamaIndex Vector RAG

Local semantic search for this Obsidian vault using LlamaIndex, HuggingFace embeddings, and persistent Chroma.

The workflow is intentionally named `obsidian-llamaindex-*` so it stays distinct from future GraphRAG tooling. The conda environment is shared as `obsidian-rag`.

## Files

- `config.yaml` - local configuration. Relative paths resolve from this directory.
- `chroma_db/` - persistent Chroma database, ignored by git.
- `llama_index_manifest.json` - file-to-chunk manifest.
- `obsidian_llamaindex_rag/` - Python package for discovery, chunking, indexing, search, and watch mode.
- `skills/obsidian-llamaindex-vector-indexing/SKILL.md` - local agent usage guide.

## Setup

```bash
./.vault-llamaindex-rag/setup_llama-index.sh
```

Use `--skip-tests` to create/update the environment without running pytest and validation.

## Commands

```bash
./.vault-llamaindex-rag/rebuild_llama-index.sh --force
./.vault-llamaindex-rag/update_llama-index.sh --dry-run
./.vault-llamaindex-rag/update_llama-index.sh
./.vault-llamaindex-rag/validate_llama-index.sh
./.vault-llamaindex-rag/search_llama-index.sh "federated multi-agent reinforcement learning" --top-k 5
./.vault-llamaindex-rag/watch_llama-index.sh --debounce 2
```

`rebuild_llama-index.sh` refuses to delete existing Chroma data unless `--force` is passed or `allow_rebuild_delete: true` is set. Artifact paths for Chroma, manifest, cache, validation, and logs must resolve inside `.vault-llamaindex-rag/`.

## Indexing

The indexer discovers Markdown files under `vault_path`, applies the include/exclude globs in `config.yaml`, strips YAML frontmatter, splits Markdown by headings with `MarkdownNodeParser`, and chunks oversized sections with `SentenceSplitter`.

Each chunk stores:

- `source_path`
- `heading`
- `chunk_id`
- `content_hash`
- `modified_time`
- selected frontmatter: `Title`, `Medium`, `Category`, `Date Created`, `Time Created`, `tags`, `Keywords`

Search is retriever-only. The scripts set `Settings.llm = None` and use `BAAI/bge-small-en-v1.5` through local HuggingFace embeddings, so no OpenAI API key is required.

