from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from .config import RAGConfig
from .constants import FRONTMATTER_LIST_KEYS, FRONTMATTER_SCALAR_KEYS
from .discover import FileRecord

LOGGER = logging.getLogger(__name__)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    metadata: dict[str, str | int | float | bool]


def make_chunk_id(source_path: str, content_hash: str, chunk_index: int) -> str:
    raw = f"{source_path}:{content_hash}:{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def chunk_markdown_file(
    record: FileRecord,
    config: RAGConfig,
    *,
    use_llama_parser: bool = True,
) -> list[Chunk]:
    raw_text = record.path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = split_frontmatter(raw_text, source_path=record.relative_path)
    normalized_frontmatter = normalize_frontmatter(frontmatter, record.relative_path)

    sections = parse_markdown_sections(body, use_llama_parser=use_llama_parser)
    chunks: list[Chunk] = []
    chunk_index = 0
    for section in sections:
        for piece in split_section_text(
            section["text"],
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            use_llama_parser=use_llama_parser,
        ):
            text = piece.strip()
            if not text:
                continue
            chunk_id = make_chunk_id(record.relative_path, record.content_hash, chunk_index)
            metadata: dict[str, str | int | float | bool] = {
                "source_path": record.relative_path,
                "heading": section["heading"],
                "chunk_id": chunk_id,
                "content_hash": record.content_hash,
                "modified_time": record.modified_time,
            }
            metadata.update(normalized_frontmatter)
            chunks.append(Chunk(chunk_id=chunk_id, text=text, metadata=metadata))
            chunk_index += 1
    return chunks


def split_frontmatter(markdown: str, *, source_path: str = "<memory>") -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    raw_frontmatter = match.group(1)
    body = markdown[match.end() :]
    try:
        parsed = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError as exc:
        LOGGER.warning("Malformed YAML frontmatter in %s: %s", source_path, exc)
        return {}, body
    if not isinstance(parsed, dict):
        LOGGER.warning("Ignoring non-mapping YAML frontmatter in %s", source_path)
        return {}, body
    return parsed, body


def normalize_frontmatter(
    frontmatter: dict[str, Any],
    source_path: str = "<memory>",
) -> dict[str, str | int | float | bool]:
    normalized: dict[str, str | int | float | bool] = {}
    for key in FRONTMATTER_SCALAR_KEYS:
        if key not in frontmatter:
            continue
        value = frontmatter[key]
        if value is None:
            continue
        if _is_scalar_frontmatter_value(value):
            normalized[key] = _normalize_scalar_value(value)
        else:
            LOGGER.warning("Dropping nested/non-scalar frontmatter key %s in %s", key, source_path)

    for key in FRONTMATTER_LIST_KEYS:
        if key not in frontmatter:
            continue
        value = frontmatter[key]
        if value is None:
            continue
        if isinstance(value, list):
            kept: list[str] = []
            for item in value:
                if _is_scalar_frontmatter_value(item):
                    kept.append(str(item))
                elif item is not None:
                    LOGGER.warning("Dropping nested value from frontmatter key %s in %s", key, source_path)
            if kept:
                normalized[key] = ", ".join(kept)
        elif _is_scalar_frontmatter_value(value):
            normalized[key] = str(value)
        else:
            LOGGER.warning("Dropping nested/non-scalar frontmatter key %s in %s", key, source_path)
    return normalized


def _is_scalar_frontmatter_value(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, date, datetime))


def _normalize_scalar_value(value: Any) -> str | bool:
    return value if isinstance(value, bool) else str(value)


def parse_markdown_sections(markdown: str, *, use_llama_parser: bool = True) -> list[dict[str, str]]:
    if use_llama_parser:
        try:
            return _parse_markdown_sections_with_llama(markdown)
        except ImportError:
            LOGGER.debug("LlamaIndex unavailable; using fallback Markdown parser")
        except Exception as exc:
            LOGGER.warning("LlamaIndex Markdown parser failed; using fallback parser: %s", exc)
    return _parse_markdown_sections_fallback(markdown)


def split_section_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    use_llama_parser: bool = True,
) -> list[str]:
    if use_llama_parser:
        try:
            from llama_index.core.node_parser import SentenceSplitter

            splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            return splitter.split_text(text)
        except ImportError:
            LOGGER.debug("LlamaIndex unavailable; using fallback text splitter")
        except Exception as exc:
            LOGGER.warning("LlamaIndex SentenceSplitter failed; using fallback splitter: %s", exc)
    return _split_text_fallback(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def _parse_markdown_sections_with_llama(markdown: str) -> list[dict[str, str]]:
    from llama_index.core import Document
    from llama_index.core.node_parser import MarkdownNodeParser
    from llama_index.core.schema import MetadataMode

    parser = MarkdownNodeParser.from_defaults(include_metadata=True)
    nodes = parser.get_nodes_from_documents([Document(text=markdown)])
    sections: list[dict[str, str]] = []
    for node in nodes:
        text = node.get_content(metadata_mode=MetadataMode.NONE).strip()
        if not text:
            continue
        sections.append({"heading": _heading_for_llama_node(text, node.metadata), "text": text})
    return sections or [{"heading": "", "text": markdown.strip()}]


def _heading_for_llama_node(text: str, metadata: dict[str, Any]) -> str:
    current = _first_heading(text)
    header_path = str(metadata.get("header_path", "")).strip("/")
    parts = [part for part in header_path.split("/") if part]
    if current:
        parts.append(current)
    return " / ".join(parts)


def _parse_markdown_sections_fallback(markdown: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_lines: list[str] = []
    heading_stack: list[tuple[int, str]] = []
    current_heading = ""
    in_code_block = False

    def flush() -> None:
        text = "\n".join(current_lines).strip()
        if text:
            sections.append({"heading": current_heading, "text": text})

    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue
        match = HEADING_RE.match(line) if not in_code_block else None
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            current_heading = " / ".join(item[1] for item in heading_stack)
            current_lines = [line]
            continue
        current_lines.append(line)
    flush()
    return sections or [{"heading": "", "text": markdown.strip()}]


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            return match.group(2).strip()
    return ""


def _split_text_fallback(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - chunk_overlap)
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks
