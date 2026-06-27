from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .discover import FileRecord

MANIFEST_VERSION = 1


def empty_manifest(collection_name: str) -> dict[str, Any]:
    return {
        "version": MANIFEST_VERSION,
        "collection_name": collection_name,
        "generated_at": None,
        "files": {},
    }


def load_manifest(path: Path, collection_name: str) -> dict[str, Any]:
    if not path.exists():
        return empty_manifest(collection_name)
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise ValueError(f"Invalid manifest shape: {path}")
    manifest.setdefault("version", MANIFEST_VERSION)
    manifest.setdefault("collection_name", collection_name)
    manifest.setdefault("generated_at", None)
    return manifest


def write_manifest_atomic(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = dict(manifest)
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def diff_records(
    records: list[FileRecord],
    manifest: dict[str, Any],
) -> tuple[list[FileRecord], list[str], list[FileRecord]]:
    files = manifest.get("files", {})
    current_by_path = {record.relative_path: record for record in records}
    changed: list[FileRecord] = []
    unchanged: list[FileRecord] = []

    for record in records:
        previous = files.get(record.relative_path)
        if not previous or _record_changed(record, previous):
            changed.append(record)
        else:
            unchanged.append(record)

    deleted = sorted(set(files) - set(current_by_path))
    return changed, deleted, unchanged


def manifest_entry(record: FileRecord, chunk_ids: list[str]) -> dict[str, Any]:
    return {
        "relative_path": record.relative_path,
        "size": record.size,
        "modified_time": record.modified_time,
        "content_hash": record.content_hash,
        "chunk_ids": chunk_ids,
        "last_indexed_at": datetime.now(timezone.utc).isoformat(),
    }


def _record_changed(record: FileRecord, previous: dict[str, Any]) -> bool:
    return (
        previous.get("size") != record.size
        or previous.get("modified_time") != record.modified_time
        or previous.get("content_hash") != record.content_hash
    )

