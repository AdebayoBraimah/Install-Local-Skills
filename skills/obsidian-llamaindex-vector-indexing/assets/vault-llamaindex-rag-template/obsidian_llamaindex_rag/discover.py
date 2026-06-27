from __future__ import annotations

import fnmatch
import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .config import RAGConfig


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative_path: str
    size: int
    modified_time: int
    content_hash: str


def discover_markdown_files(config: RAGConfig) -> list[FileRecord]:
    if not config.vault_path.exists():
        raise FileNotFoundError(f"Vault path does not exist: {config.vault_path}")

    records: list[FileRecord] = []
    for path in config.vault_path.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        relative_path = path.relative_to(config.vault_path).as_posix()
        if not _included(relative_path, config.include_globs):
            continue
        if _excluded(relative_path, config.exclude_globs):
            continue
        records.append(_record_for_path(path, relative_path))
    return sorted(records, key=lambda item: item.relative_path)


def should_index_relative_path(relative_path: str, config: RAGConfig) -> bool:
    normalized = relative_path.replace("\\", "/")
    if not normalized.lower().endswith(".md"):
        return False
    return _included(normalized, config.include_globs) and not _excluded(
        normalized, config.exclude_globs
    )


def _record_for_path(path: Path, relative_path: str) -> FileRecord:
    stat = path.stat()
    content = path.read_bytes()
    return FileRecord(
        path=path,
        relative_path=relative_path,
        size=stat.st_size,
        modified_time=stat.st_mtime_ns,
        content_hash=hashlib.sha256(content).hexdigest(),
    )


def _included(relative_path: str, globs: list[str]) -> bool:
    return any(_matches_glob(relative_path, pattern) for pattern in globs)


def _excluded(relative_path: str, globs: list[str]) -> bool:
    return any(_matches_glob(relative_path, pattern) for pattern in globs)


def _matches_glob(relative_path: str, pattern: str) -> bool:
    rel = relative_path.replace("\\", "/")
    pat = pattern.replace("\\", "/")
    path = PurePosixPath(rel)
    if pat.startswith("**/") and _matches_glob(rel, pat[3:]):
        return True
    return (
        fnmatch.fnmatchcase(rel, pat)
        or fnmatch.fnmatchcase("/" + rel, "/" + pat)
        or path.match(pat)
    )
