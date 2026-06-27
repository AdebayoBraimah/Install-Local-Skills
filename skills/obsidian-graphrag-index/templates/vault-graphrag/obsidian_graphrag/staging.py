from __future__ import annotations

import hashlib
import json
import os
import signal
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import GraphRAGConfig
from .discover import FileRecord, discover_markdown_files
from .markdown import metadata_list, metadata_scalar, parse_markdown, title_from_note
from .media import ResolvedImage, image_context_block, resolve_image_ref


FILE_READ_TIMEOUT_SECONDS = float(os.environ.get("GRAPHRAG_FILE_READ_TIMEOUT_SECONDS", "0.5"))


class FileReadTimeout(TimeoutError):
    """Raised when a cloud-backed note stalls during staging."""


@dataclass(frozen=True)
class StagingResult:
    document_count: int
    output_path: str
    manifest_path: str
    dry_run: bool
    warnings: list[str]


def prepare_input(config: GraphRAGConfig, dry_run: bool = False) -> StagingResult:
    records = discover_markdown_files(config)
    if dry_run:
        return StagingResult(
            document_count=len(records),
            output_path=str(config.input_json_path),
            manifest_path=str(config.manifest_path),
            dry_run=True,
            warnings=[],
        )

    documents: list[dict[str, Any]] = []
    warnings: list[str] = []
    for record in records:
        try:
            document, doc_warnings = document_from_record(record, config)
        except FileReadTimeout as exc:
            warnings.append(f"{record.relative_path}: {exc}")
            continue
        except OSError as exc:
            warnings.append(f"{record.relative_path}: could not read file: {exc}")
            continue
        documents.append(document)
        warnings.extend(doc_warnings)

    manifest = build_manifest(config, records, documents, warnings)
    if not dry_run:
        config.input_json_path.parent.mkdir(parents=True, exist_ok=True)
        config.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        config.input_json_path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")
        config.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return StagingResult(
        document_count=len(documents),
        output_path=str(config.input_json_path),
        manifest_path=str(config.manifest_path),
        dry_run=dry_run,
        warnings=warnings,
    )


def document_from_record(record: FileRecord, config: GraphRAGConfig) -> tuple[dict[str, Any], list[str]]:
    raw_bytes = read_bytes_with_timeout(record.path, FILE_READ_TIMEOUT_SECONDS)
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    raw_text = raw_bytes.decode("utf-8", errors="replace")
    parsed = parse_markdown(raw_text, config.image_context_lines, config.image_context_chars)
    resolved_images: list[ResolvedImage] = [
        resolve_image_ref(ref, record.path, config.vault_path, config.referenced_image_dirs)
        for ref in parsed.image_refs
    ]
    warnings = [
        f"{record.relative_path}: {image.raw_target}: {image.warning}"
        for image in resolved_images
        if image.warning
    ]
    text = parsed.body.rstrip() + image_context_block(resolved_images)
    image_refs = [
        {
            "target": image.raw_target,
            "source_path": image.source_path,
            "alt": image.alt_text,
            "warning": image.warning,
        }
        for image in resolved_images
    ]
    sidecar_paths = [image.source_path for image in resolved_images if image.source_path]
    metadata = {
        "source_path": record.relative_path,
        "sha256": sha256,
        "mtime_ns": record.mtime_ns,
        "tags": metadata_list(parsed.frontmatter, "tags", "Tags"),
        "aliases": metadata_list(parsed.frontmatter, "aliases", "Aliases"),
        "keywords": metadata_list(parsed.frontmatter, "Keywords", "keywords"),
        "category": metadata_scalar(parsed.frontmatter, "Category", "category"),
        "wikilinks": parsed.wikilinks,
        "image_refs": image_refs,
        "sidecar_paths": sidecar_paths,
        "warning_count": len(warnings),
    }
    document = {
        "id": stable_document_id(record.relative_path, sha256),
        "title": title_from_note(record.relative_path, parsed.frontmatter),
        "text": text,
        "metadata": metadata,
    }
    document.update(metadata)
    return document, warnings


def stable_document_id(relative_path: str, sha256: str) -> str:
    return f"{relative_path}:{sha256[:16]}"


def read_bytes_with_timeout(path: Path, timeout_seconds: float) -> bytes:
    def handler(_signum, _frame):
        raise FileReadTimeout(f"timed out reading file after {timeout_seconds}s")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, handler)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return path.read_bytes()
    finally:
        signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])
        signal.signal(signal.SIGALRM, previous_handler)


def build_manifest(
    config: GraphRAGConfig,
    records: list[FileRecord],
    documents: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vault_path": str(config.vault_path),
        "input_path": str(config.input_json_path),
        "document_count": len(documents),
        "source_count": len(records),
        "warning_count": len(warnings),
        "warnings": warnings,
        "sources": [
            asdict(record)
            | {
                "path": str(record.path),
                "sha256": document.get("metadata", {}).get("sha256", record.sha256),
            }
            for record, document in zip(records, documents, strict=False)
        ],
    }
