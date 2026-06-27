from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .chunking import Chunk, chunk_markdown_file
from .config import ConfigError, RAGConfig, ensure_contained
from .discover import FileRecord, discover_markdown_files
from .manifest import diff_records, empty_manifest, load_manifest, manifest_entry, write_manifest_atomic


@dataclass(frozen=True)
class IndexSummary:
    discovered: int
    indexed: int
    deleted: int
    unchanged: int
    chunks_added: int
    dry_run: bool = False


def rebuild_index(config: RAGConfig, *, force: bool = False) -> IndexSummary:
    if not force and not config.allow_rebuild_delete:
        raise ConfigError("Refusing rebuild delete without --force or allow_rebuild_delete: true")
    _assert_delete_targets_safe(config)
    if config.chroma_path.exists():
        shutil.rmtree(config.chroma_path)
    if config.manifest_path.exists():
        config.manifest_path.unlink()

    records = discover_markdown_files(config)
    collection = _collection(config)
    chunks_by_path = _chunk_records(records, config)
    all_chunks = [chunk for chunks in chunks_by_path.values() for chunk in chunks]
    _add_chunks_to_collection(all_chunks, config, collection)
    manifest = empty_manifest(config.collection_name)
    for record in records:
        chunks = chunks_by_path[record.relative_path]
        manifest["files"][record.relative_path] = manifest_entry(
            record,
            [chunk.chunk_id for chunk in chunks],
        )
    write_manifest_atomic(config.manifest_path, manifest)
    return IndexSummary(
        discovered=len(records),
        indexed=len(records),
        deleted=0,
        unchanged=0,
        chunks_added=len(all_chunks),
    )


def update_index(config: RAGConfig, *, dry_run: bool = False) -> IndexSummary:
    records = discover_markdown_files(config)
    manifest = load_manifest(config.manifest_path, config.collection_name)
    changed, deleted, unchanged = diff_records(records, manifest)

    if dry_run:
        return IndexSummary(
            discovered=len(records),
            indexed=len(changed),
            deleted=len(deleted),
            unchanged=len(unchanged),
            chunks_added=0,
            dry_run=True,
        )

    collection = _collection(config)
    for relative_path in deleted:
        _delete_source(collection, relative_path)
        manifest["files"].pop(relative_path, None)

    chunks_added = 0
    for record in changed:
        _delete_source(collection, record.relative_path)
        chunks = chunk_markdown_file(record, config)
        _add_chunks_to_collection(chunks, config, collection)
        manifest["files"][record.relative_path] = manifest_entry(
            record,
            [chunk.chunk_id for chunk in chunks],
        )
        chunks_added += len(chunks)

    write_manifest_atomic(config.manifest_path, manifest)
    return IndexSummary(
        discovered=len(records),
        indexed=len(changed),
        deleted=len(deleted),
        unchanged=len(unchanged),
        chunks_added=chunks_added,
    )


def validate_smoke_index(config: RAGConfig) -> dict[str, Any]:
    validation_root = config.validation_path
    ensure_contained(validation_root, config.rag_dir, "validation_path")
    if validation_root.exists():
        shutil.rmtree(validation_root)
    sample_vault = validation_root / "sample_vault"
    sample_vault.mkdir(parents=True, exist_ok=True)
    sample_note = sample_vault / "sample.md"
    sample_note.write_text(
        "---\nTitle: Validation Note\ntags: [validation, llamaindex]\n---\n"
        "# Validation\n\n"
        "This smoke test confirms local HuggingFace embeddings and Chroma retrieval.\n",
        encoding="utf-8",
    )
    validation_config = _replace_config_paths_for_validation(config, sample_vault, validation_root)
    summary = rebuild_index(validation_config, force=True)
    from .search import search

    results = search("local HuggingFace embeddings", validation_config, top_k=1)
    return {
        "summary": summary,
        "results": results,
        "validation_root": validation_root,
    }


def _replace_config_paths_for_validation(
    config: RAGConfig,
    sample_vault: Path,
    validation_root: Path,
) -> RAGConfig:
    return RAGConfig(
        config_path=config.config_path,
        base_dir=config.base_dir,
        vault_path=sample_vault.resolve(),
        rag_dir=config.rag_dir,
        chroma_path=(validation_root / "chroma_db").resolve(),
        manifest_path=(validation_root / "llama_index_manifest.json").resolve(),
        cache_path=config.cache_path,
        validation_path=validation_root.resolve(),
        log_path=config.log_path,
        collection_name=f"{config.collection_name}_validation",
        embedding_model=config.embedding_model,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        top_k_default=config.top_k_default,
        allow_rebuild_delete=True,
        include_globs=config.include_globs,
        exclude_globs=config.exclude_globs,
    )


def _chunk_records(records: list[FileRecord], config: RAGConfig) -> dict[str, list[Chunk]]:
    return {
        record.relative_path: chunk_markdown_file(record, config)
        for record in records
    }


def _add_chunks_to_collection(chunks: list[Chunk], config: RAGConfig, collection: Any) -> None:
    if not chunks:
        return
    nodes = [_chunk_to_text_node(chunk) for chunk in chunks]
    vector_store, storage_context, embed_model = _llama_vector_store(config, collection)
    from llama_index.core import VectorStoreIndex

    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    # Keep vector_store referenced until construction completes.
    _ = vector_store


def _delete_source(collection: Any, relative_path: str) -> None:
    collection.delete(where={"source_path": relative_path})


def _collection(config: RAGConfig) -> Any:
    import chromadb

    config.chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(config.chroma_path))
    return client.get_or_create_collection(config.collection_name)


def _llama_vector_store(config: RAGConfig, collection: Any) -> tuple[Any, Any, Any]:
    from llama_index.core import Settings, StorageContext
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore

    Settings.llm = None
    embed_model = HuggingFaceEmbedding(model_name=config.embedding_model)
    Settings.embed_model = embed_model
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return vector_store, storage_context, embed_model


def _chunk_to_text_node(chunk: Chunk) -> Any:
    from llama_index.core.schema import TextNode

    metadata_keys = list(chunk.metadata)
    node = TextNode(id_=chunk.chunk_id, text=chunk.text, metadata=chunk.metadata)
    node.excluded_embed_metadata_keys = metadata_keys
    node.excluded_llm_metadata_keys = metadata_keys
    return node


def _assert_delete_targets_safe(config: RAGConfig) -> None:
    ensure_contained(config.chroma_path, config.rag_dir, "chroma_path")
    ensure_contained(config.manifest_path, config.rag_dir, "manifest_path")
    if config.chroma_path == config.rag_dir:
        raise ConfigError("chroma_path must not be the RAG directory itself")
    if config.manifest_path == config.rag_dir:
        raise ConfigError("manifest_path must not be the RAG directory itself")
