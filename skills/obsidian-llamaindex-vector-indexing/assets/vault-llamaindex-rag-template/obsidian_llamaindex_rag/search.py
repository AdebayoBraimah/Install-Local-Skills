from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import RAGConfig


@dataclass(frozen=True)
class SearchResult:
    source_path: str
    heading: str
    score: float | None
    excerpt: str


def search(query: str, config: RAGConfig, *, top_k: int | None = None) -> list[SearchResult]:
    if not query.strip():
        raise ValueError("query must be non-empty")
    top_k = top_k or config.top_k_default

    import chromadb
    from llama_index.core import Settings, VectorStoreIndex
    from llama_index.core.schema import MetadataMode
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore

    Settings.llm = None
    embed_model = HuggingFaceEmbedding(model_name=config.embedding_model)
    Settings.embed_model = embed_model

    client = chromadb.PersistentClient(path=str(config.chroma_path))
    collection = client.get_or_create_collection(config.collection_name)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)

    results: list[SearchResult] = []
    for node_with_score in nodes:
        node = node_with_score.node
        metadata: dict[str, Any] = dict(getattr(node, "metadata", {}) or {})
        text = (
            node.get_content(metadata_mode=MetadataMode.NONE)
            if hasattr(node, "get_content")
            else str(getattr(node, "text", ""))
        )
        results.append(
            SearchResult(
                source_path=str(metadata.get("source_path", "")),
                heading=str(metadata.get("heading", "")),
                score=node_with_score.score,
                excerpt=_excerpt(text),
            )
        )
    return sorted(results, key=lambda result: result.score if result.score is not None else float("-inf"), reverse=True)


def format_results(results: list[SearchResult]) -> str:
    if not results:
        return "No results."
    rendered: list[str] = []
    for idx, result in enumerate(results, start=1):
        score = "None" if result.score is None else f"{result.score:.6f}"
        heading = result.heading or "(no heading)"
        rendered.append(
            f"{idx}. source_path: {result.source_path}\n"
            f"   heading: {heading}\n"
            f"   score: {score}\n"
            f"   excerpt: {result.excerpt}"
        )
    return "\n\n".join(rendered)


def _excerpt(text: str, *, max_chars: int = 420) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 3].rstrip() + "..."
