from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from .markdown import MarkdownImageRef


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp", ".svg"}


@dataclass(frozen=True)
class ResolvedImage:
    raw_target: str
    alt_text: str
    source_path: str | None
    context: str
    warning: str | None = None


def resolve_image_ref(
    ref: MarkdownImageRef,
    note_path: Path,
    vault_path: Path,
    image_dirs: list[Path],
) -> ResolvedImage:
    target = _clean_target(ref.raw_target)
    if _is_external(target):
        return ResolvedImage(ref.raw_target, ref.alt_text, None, ref.context, "external image skipped")
    if not target:
        return ResolvedImage(ref.raw_target, ref.alt_text, None, ref.context, "empty image target")

    candidates = [
        (note_path.parent / target).resolve(),
        (vault_path / target).resolve(),
    ]
    basename = Path(target).name
    candidates.extend(_unique_basename_matches(basename, image_dirs))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
            try:
                rel = candidate.relative_to(vault_path).as_posix()
            except ValueError:
                rel = str(candidate)
            return ResolvedImage(ref.raw_target, ref.alt_text, rel, ref.context)
    return ResolvedImage(ref.raw_target, ref.alt_text, None, ref.context, "image not found")


def image_context_block(images: list[ResolvedImage]) -> str:
    usable = [image for image in images if image.source_path or image.alt_text or image.context]
    if not usable:
        return ""
    lines = ["", "## Referenced Image Context"]
    for image in usable:
        label = image.source_path or image.raw_target
        lines.append("")
        lines.append(f"- Image: {label}")
        if image.alt_text:
            lines.append(f"  Alt: {image.alt_text}")
        if image.context:
            lines.append("  Nearby context:")
            for context_line in image.context.splitlines():
                lines.append(f"  {context_line}")
        if image.warning:
            lines.append(f"  Warning: {image.warning}")
    return "\n".join(lines)


def _clean_target(target: str) -> str:
    target = target.strip().strip("<>")
    if "|" in target:
        target = target.split("|", 1)[0].strip()
    if "#" in target:
        target = target.split("#", 1)[0].strip()
    return unquote(target)


def _is_external(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme.lower() in {"http", "https", "data"}


def _unique_basename_matches(basename: str, image_dirs: list[Path]) -> list[Path]:
    if not basename:
        return []
    matches: list[Path] = []
    for directory in image_dirs:
        if not directory.exists():
            continue
        matches.extend(path.resolve() for path in directory.rglob(basename) if path.is_file())
    unique = sorted(set(matches))
    return unique if len(unique) == 1 else []
