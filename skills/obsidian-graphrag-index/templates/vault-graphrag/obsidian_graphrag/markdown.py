from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]\n]+)\]\]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]\n]*)\]\(([^)\n]+)\)")


@dataclass(frozen=True)
class MarkdownImageRef:
    raw_target: str
    alt_text: str
    line_number: int
    context: str
    syntax: str


@dataclass(frozen=True)
class ParsedMarkdown:
    frontmatter: dict[str, Any]
    body: str
    wikilinks: list[str]
    image_refs: list[MarkdownImageRef]


def parse_markdown(text: str, context_lines: int = 3, context_chars: int = 1000) -> ParsedMarkdown:
    frontmatter, body = split_frontmatter(text)
    lines = body.splitlines()
    return ParsedMarkdown(
        frontmatter=frontmatter,
        body=body,
        wikilinks=extract_wikilinks(body),
        image_refs=extract_image_refs(lines, context_lines, context_chars),
    )


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw_frontmatter = match.group(1)
    body = text[match.end() :]
    loaded = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(loaded, dict):
        return {}, body
    return loaded, body


def extract_wikilinks(text: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for match in WIKILINK_RE.finditer(text):
        link = match.group(1).strip()
        if "|" in link:
            link = link.split("|", 1)[0].strip()
        if "#" in link:
            link = link.split("#", 1)[0].strip()
        if link and link not in seen:
            seen.add(link)
            links.append(link)
    return links


def extract_image_refs(lines: list[str], context_lines: int, context_chars: int) -> list[MarkdownImageRef]:
    refs: list[MarkdownImageRef] = []
    for index, line in enumerate(lines):
        for match in MARKDOWN_IMAGE_RE.finditer(line):
            refs.append(
                MarkdownImageRef(
                    raw_target=match.group(2).strip(),
                    alt_text=match.group(1).strip(),
                    line_number=index + 1,
                    context=_nearby_context(lines, index, context_lines, context_chars),
                    syntax="markdown",
                )
            )
        for match in OBSIDIAN_EMBED_RE.finditer(line):
            target = match.group(1).strip()
            refs.append(
                MarkdownImageRef(
                    raw_target=target.split("|", 1)[0].strip(),
                    alt_text=target,
                    line_number=index + 1,
                    context=_nearby_context(lines, index, context_lines, context_chars),
                    syntax="obsidian",
                )
            )
    return refs


def metadata_list(frontmatter: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        if key in frontmatter:
            return _as_list(frontmatter[key])
    return []


def metadata_scalar(frontmatter: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        if key in frontmatter and frontmatter[key] is not None:
            value = frontmatter[key]
            if isinstance(value, list):
                return ", ".join(str(item) for item in value)
            return str(value)
    return None


def title_from_note(relative_path: str, frontmatter: dict[str, Any]) -> str:
    title = metadata_scalar(frontmatter, "Title", "title")
    if title:
        return title
    stem = relative_path.rsplit("/", 1)[-1]
    return stem[:-3] if stem.endswith(".md") else stem


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def _nearby_context(lines: list[str], index: int, context_lines: int, context_chars: int) -> str:
    before: list[str] = []
    cursor = index - 1
    while cursor >= 0 and len(before) < context_lines:
        stripped = lines[cursor].strip()
        if stripped:
            before.append(stripped)
        cursor -= 1
    after: list[str] = []
    cursor = index + 1
    while cursor < len(lines) and len(after) < context_lines:
        stripped = lines[cursor].strip()
        if stripped:
            after.append(stripped)
        cursor += 1
    context = "\n".join(list(reversed(before)) + [lines[index].strip()] + after)
    return context[:context_chars]
