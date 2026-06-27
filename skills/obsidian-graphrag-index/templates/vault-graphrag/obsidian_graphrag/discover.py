from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path

from .config import GraphRAGConfig


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative_path: str
    size: int
    mtime_ns: int
    sha256: str


def load_ignore_patterns(path: Path) -> list[str]:
    patterns: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("!"):
            raise ValueError(f"Negation is not supported in GraphRAG ignore patterns: {stripped}")
        patterns.append(stripped.replace("\\", "/"))
    return patterns


def discover_markdown_files(config: GraphRAGConfig) -> list[FileRecord]:
    patterns = load_ignore_patterns(config.ignore_patterns_path)
    records: list[FileRecord] = []
    for dirpath, dirnames, filenames in os.walk(config.vault_path, topdown=True, followlinks=False):
        current_dir = Path(dirpath)
        current_rel = _relative_path(current_dir, config.vault_path)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _directory_ignored(current_rel, dirname, patterns)
        ]
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            path = current_dir / filename
            if not path.is_file():
                continue
            relative_path = path.relative_to(config.vault_path).as_posix()
            if not _included(relative_path, config.include_globs):
                continue
            if is_ignored(relative_path, patterns):
                continue
            records.append(record_for_path(path, relative_path))
    return sorted(records, key=lambda record: record.relative_path)


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return ""


def _directory_ignored(current_rel: str, dirname: str, patterns: list[str]) -> bool:
    rel = dirname if current_rel in {"", "."} else f"{current_rel.rstrip('/')}/{dirname}"
    return is_ignored(rel + "/", patterns) or is_ignored(rel, patterns)


def is_ignored(relative_path: str, patterns: list[str]) -> bool:
    rel = relative_path.replace("\\", "/").lstrip("/")
    segments = rel.split("/")
    for pattern in patterns:
        if _matches_ignore_pattern(rel, segments, pattern):
            return True
    return False


def record_for_path(path: Path, relative_path: str) -> FileRecord:
    stat = path.stat()
    return FileRecord(
        path=path,
        relative_path=relative_path,
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        sha256="",
    )


def _included(relative_path: str, patterns: list[str]) -> bool:
    return any(_matches_include_pattern(relative_path, pattern) for pattern in patterns)


def _matches_include_pattern(relative_path: str, pattern: str) -> bool:
    rel = relative_path.replace("\\", "/").lstrip("/")
    pat = pattern.replace("\\", "/")
    return fnmatch.fnmatchcase(rel, pat) or fnmatch.fnmatchcase("/" + rel, "/" + pat)


def _matches_ignore_pattern(relative_path: str, segments: list[str], pattern: str) -> bool:
    pat = pattern.strip("/")
    if pattern.endswith("/"):
        return relative_path == pat or relative_path.startswith(pat + "/") or pat in segments
    if "/" in pattern:
        return fnmatch.fnmatchcase(relative_path, pat)
    return any(fnmatch.fnmatchcase(segment, pattern) for segment in segments)
