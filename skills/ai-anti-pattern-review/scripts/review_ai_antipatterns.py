#!/usr/bin/env python3
"""Review text for AI writing anti-patterns using an updateable JSON database."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".sh",
    ".tex",
}
REQUIRED_ROOT_KEYS = {"metadata", "patterns", "master_prompt_instructions"}
REQUIRED_PATTERN_KEYS = {
    "id",
    "category",
    "description",
    "severity",
    "examples",
    "frequency",
    "fixes",
    "prompt_instruction",
    "detectors",
}
VALID_DETECTORS = {"literal", "regex", "density", "structural", "agent_judgment"}
CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "manual": 0}


class InputError(Exception):
    """Raised when the input source is invalid."""


class SchemaError(Exception):
    """Raised when the pattern JSON is invalid."""


def default_patterns_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "ai_antipatterns.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", help="Text to review")
    group.add_argument("--file", help="UTF-8 text-like file to review")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--min-severity",
        type=int,
        default=1,
        help="Only return patterns with this severity or higher",
    )
    parser.add_argument(
        "--patterns-json",
        default=str(default_patterns_path()),
        help="Pattern JSON file to load",
    )
    return parser.parse_args()


def load_patterns(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SchemaError(f"Could not read patterns JSON: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SchemaError(f"Patterns JSON is invalid: {exc}") from exc

    validate_patterns(data)
    return data


def validate_patterns(data: dict[str, Any]) -> None:
    missing_root = REQUIRED_ROOT_KEYS - set(data)
    if missing_root:
        raise SchemaError(f"Missing root keys: {', '.join(sorted(missing_root))}")
    if not isinstance(data["patterns"], list) or not data["patterns"]:
        raise SchemaError("'patterns' must be a non-empty list")

    seen_ids: set[str] = set()
    for index, pattern in enumerate(data["patterns"]):
        if not isinstance(pattern, dict):
            raise SchemaError(f"Pattern at index {index} must be an object")
        missing = REQUIRED_PATTERN_KEYS - set(pattern)
        if missing:
            pid = pattern.get("id", f"index {index}")
            raise SchemaError(f"Pattern {pid} missing keys: {', '.join(sorted(missing))}")
        pid = pattern["id"]
        if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9_]+", pid):
            raise SchemaError(f"Pattern id must be stable snake_case: {pid!r}")
        if pid in seen_ids:
            raise SchemaError(f"Duplicate pattern id: {pid}")
        seen_ids.add(pid)
        severity = pattern["severity"]
        if not isinstance(severity, int) or severity < 1 or severity > 5:
            raise SchemaError(f"Pattern {pid} severity must be an integer from 1 to 5")
        detectors = pattern["detectors"]
        if not isinstance(detectors, list) or not detectors:
            raise SchemaError(f"Pattern {pid} must have a non-empty detectors list")
        for detector in detectors:
            if not isinstance(detector, dict):
                raise SchemaError(f"Pattern {pid} detector must be an object")
            dtype = detector.get("type")
            if dtype not in VALID_DETECTORS:
                raise SchemaError(f"Pattern {pid} has unsupported detector type: {dtype}")
            if dtype == "literal" and not detector.get("terms"):
                raise SchemaError(f"Pattern {pid} literal detector requires terms")
            if dtype == "regex" and not detector.get("pattern"):
                raise SchemaError(f"Pattern {pid} regex detector requires pattern")
            if dtype == "density" and not (detector.get("targets") or detector.get("pattern")):
                raise SchemaError(f"Pattern {pid} density detector requires targets or pattern")
            if dtype == "structural" and not detector.get("checks"):
                raise SchemaError(f"Pattern {pid} structural detector requires checks")
            if dtype == "agent_judgment" and not detector.get("guidance"):
                raise SchemaError(f"Pattern {pid} agent_judgment detector requires guidance")


def read_input(args: argparse.Namespace) -> tuple[str, str]:
    if args.text is not None:
        reject_extra_stdin()
        return args.text, "text"
    if args.file is not None:
        reject_extra_stdin()
        path = Path(args.file)
        return read_text_file(path), "file"
    stdin_text = sys.stdin.read()
    if stdin_text == "":
        raise InputError("Provide exactly one input source: --text, --file, or stdin")
    return stdin_text, "stdin"


def reject_extra_stdin() -> None:
    if sys.stdin.isatty():
        return
    extra = sys.stdin.read()
    if extra.strip():
        raise InputError("Provide exactly one input source: --text, --file, or stdin")


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise InputError(f"File does not exist: {path}")
    if path.is_dir():
        raise InputError(f"Expected a file, got a directory: {path}")
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise InputError(f"Unsupported file extension for v1 text review: {path.suffix or '<none>'}")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputError(f"Could not read file: {exc}") from exc
    if b"\x00" in raw:
        raise InputError("Unsupported binary file: NUL byte detected")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(f"File is not valid UTF-8: {exc}") from exc


def line_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    line_start = text.rfind("\n", 0, index) + 1
    return line, index - line_start + 1


def evidence_snippet(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    snippet = text[line_start:line_end].strip()
    if len(snippet) > 160:
        snippet = snippet[:157].rstrip() + "..."
    return snippet


def make_finding(
    pattern: dict[str, Any],
    detector: dict[str, Any],
    text: str,
    start: int,
    end: int,
    detector_type: str,
) -> dict[str, Any]:
    line, column = line_column(text, start)
    return {
        "pattern_id": pattern["id"],
        "category": pattern["category"],
        "severity": pattern["severity"],
        "confidence": detector.get("confidence", "medium"),
        "detector_type": detector_type,
        "line": line,
        "column": column,
        "evidence": evidence_snippet(text, start, end),
        "explanation": pattern["description"],
        "fixes": pattern["fixes"],
    }


def regex_flags(detector: dict[str, Any]) -> int:
    raw = str(detector.get("flags", "i"))
    flags = 0
    if "i" in raw.lower():
        flags |= re.IGNORECASE
    if "m" in raw.lower():
        flags |= re.MULTILINE
    return flags


def term_pattern(term: str, word_boundary: bool) -> str:
    escaped = re.escape(term)
    if not word_boundary:
        return escaped
    prefix = r"\b" if term and term[0].isalnum() else ""
    suffix = r"\b" if term and term[-1].isalnum() else ""
    return prefix + escaped + suffix


def detect_literal(pattern: dict[str, Any], detector: dict[str, Any], text: str) -> list[dict[str, Any]]:
    flags = 0 if detector.get("case_sensitive", False) else re.IGNORECASE
    word_boundary = bool(detector.get("word_boundary", False))
    findings = []
    for term in detector["terms"]:
        compiled = re.compile(term_pattern(term, word_boundary), flags)
        for match in compiled.finditer(text):
            findings.append(make_finding(pattern, detector, text, match.start(), match.end(), "literal"))
    return findings


def detect_regex(pattern: dict[str, Any], detector: dict[str, Any], text: str) -> list[dict[str, Any]]:
    compiled = re.compile(detector["pattern"], regex_flags(detector))
    return [
        make_finding(pattern, detector, text, match.start(), match.end(), "regex")
        for match in compiled.finditer(text)
    ]


def detect_density(pattern: dict[str, Any], detector: dict[str, Any], text: str) -> list[dict[str, Any]]:
    matches: list[tuple[int, int]] = []
    if detector.get("pattern"):
        compiled = re.compile(detector["pattern"], regex_flags(detector))
        matches = [(match.start(), match.end()) for match in compiled.finditer(text)]
    else:
        for target in detector.get("targets", []):
            start = 0
            while True:
                index = text.find(target, start)
                if index == -1:
                    break
                matches.append((index, index + len(target)))
                start = index + max(1, len(target))
    word_count = max(1, len(re.findall(r"\b\w+\b", text)))
    max_per_words = max(1, int(detector.get("max_per_words", 500)))
    threshold = max(1, int(detector.get("threshold", 2)))
    allowed_segments = max(1, math.ceil(word_count / max_per_words))
    required_count = threshold * allowed_segments
    if len(matches) < required_count:
        return []
    start, end = sorted(matches)[0]
    finding = make_finding(pattern, detector, text, start, end, "density")
    finding["explanation"] = f"{pattern['description']} ({len(matches)} matches across {word_count} words)"
    return [finding]


def detect_structural(pattern: dict[str, Any], detector: dict[str, Any], text: str) -> list[dict[str, Any]]:
    checks = detector.get("checks", [])
    threshold = int(detector.get("threshold", 1))
    findings = []
    for check in checks:
        matches: list[tuple[int, int]] = []
        if check == "markdown_headers":
            matches = line_regex_matches(text, re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE))
        elif check == "bullet_lines":
            matches = line_regex_matches(text, re.compile(r"^\s*(?:[-*+]|\d+[.)]|[•◦])\s+\S", re.MULTILINE))
        elif check == "emphasis_markers":
            compiled = re.compile(r"(?<!\*)\*[^*\n]{2,}\*(?!\*)|\*\*[^*\n]{2,}\*\*|(?<!_)_[^_\n]{2,}_(?!_)|__[^_\n]{2,}__")
            matches = [(match.start(), match.end()) for match in compiled.finditer(text)]
        if len(matches) >= threshold and matches:
            start, end = matches[0]
            finding = make_finding(pattern, detector, text, start, end, "structural")
            finding["explanation"] = f"{pattern['description']} ({check}, {len(matches)} match(es))"
            findings.append(finding)
    return findings


def line_regex_matches(text: str, compiled: re.Pattern[str]) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in compiled.finditer(text)]


def scan(text: str, data: dict[str, Any], min_severity: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    for pattern in data["patterns"]:
        if pattern["severity"] < min_severity:
            continue
        for detector in pattern["detectors"]:
            dtype = detector["type"]
            if dtype == "agent_judgment":
                manual.append(
                    {
                        "pattern_id": pattern["id"],
                        "category": pattern["category"],
                        "severity": pattern["severity"],
                        "guidance": detector["guidance"],
                        "examples": pattern["examples"],
                        "fixes": pattern["fixes"],
                    }
                )
            elif dtype == "literal":
                findings.extend(detect_literal(pattern, detector, text))
            elif dtype == "regex":
                findings.extend(detect_regex(pattern, detector, text))
            elif dtype == "density":
                findings.extend(detect_density(pattern, detector, text))
            elif dtype == "structural":
                findings.extend(detect_structural(pattern, detector, text))

    findings.sort(key=lambda item: (-item["severity"], -CONFIDENCE_RANK.get(item["confidence"], 0), item["line"], item["column"]))
    manual.sort(key=lambda item: (-item["severity"], item["pattern_id"]))
    return dedupe_findings(findings), manual


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    unique = []
    for finding in findings:
        key = (
            finding["pattern_id"],
            finding["line"],
            finding["column"],
            finding["evidence"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def make_result(
    patterns_path: Path,
    input_source: str,
    min_severity: int,
    pattern_count: int,
    findings: list[dict[str, Any]],
    manual: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[str, Any]:
    highest = max((finding["severity"] for finding in findings), default=None)
    return {
        "metadata": {
            "patterns_file": str(patterns_path),
            "input_source": input_source,
            "min_severity": min_severity,
            "pattern_count": pattern_count,
        },
        "summary": {
            "finding_count": len(findings),
            "manual_review_count": len(manual),
            "highest_severity": highest,
        },
        "findings": findings,
        "manual_review_patterns": manual,
        "errors": errors or [],
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"Summary: {result['summary']['finding_count']} finding(s), {result['summary']['manual_review_count']} manual-review pattern(s).",
        "",
        "Findings",
    ]
    if not result["findings"]:
        lines.append("- No deterministic findings.")
    else:
        for finding in result["findings"]:
            location = f"line {finding['line']}, column {finding['column']}"
            lines.extend(
                [
                    f"- [Severity {finding['severity']}] {finding['pattern_id']} ({finding['confidence']})",
                    f"  Evidence: \"{finding['evidence']}\" ({location})",
                    f"  Why it was flagged: {finding['explanation']}",
                    f"  Suggested fix: {finding['fixes'][0] if finding['fixes'] else 'Revise for a more natural style.'}",
                ]
            )
    lines.extend(["", "Manual Review Patterns"])
    if not result["manual_review_patterns"]:
        lines.append("- No manual-review patterns at this severity.")
    else:
        for item in result["manual_review_patterns"]:
            lines.append(f"- [Severity {item['severity']}] {item['pattern_id']}: {item['guidance']}")
    if result["errors"]:
        lines.extend(["", "Errors"])
        lines.extend(f"- {error}" for error in result["errors"])
    return "\n".join(lines)


def emit_error(args: argparse.Namespace, patterns_path: Path, message: str, exit_code: int) -> int:
    result = make_result(patterns_path, "unknown", args.min_severity, 0, [], [], [message])
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(result))
    print(message, file=sys.stderr)
    return exit_code


def main() -> int:
    args = parse_args()
    patterns_path = Path(args.patterns_json)
    if args.min_severity < 1 or args.min_severity > 5:
        return emit_error(args, patterns_path, "--min-severity must be between 1 and 5", 2)

    try:
        data = load_patterns(patterns_path)
    except SchemaError as exc:
        return emit_error(args, patterns_path, str(exc), 3)

    try:
        text, input_source = read_input(args)
    except InputError as exc:
        return emit_error(args, patterns_path, str(exc), 2)

    findings, manual = scan(text, data, args.min_severity)
    result = make_result(patterns_path, input_source, args.min_severity, len(data["patterns"]), findings, manual)
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
