"""CLI and REST helpers for checking text with Pangram V3."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable, TextIO

try:
    from .pangram_config import MISSING_KEY_MESSAGE, find_pangram_api_key, mask_key
except ImportError:  # pragma: no cover - direct script execution
    from pangram_config import MISSING_KEY_MESSAGE, find_pangram_api_key, mask_key

PANGRAM_V3_URL = "https://text.api.pangram.com/v3"
FRACTION_FIELDS = ("fraction_ai", "fraction_ai_assisted", "fraction_human")
COUNT_FIELDS = ("num_ai_segments", "num_ai_assisted_segments", "num_human_segments")
STRING_FIELDS = ("headline", "prediction_short")


class PangramError(Exception):
    """Base class for sanitized Pangram skill errors."""


class PangramUsageError(PangramError):
    """Input or CLI usage error."""


class PangramAPIError(PangramError):
    """Network or HTTP error from Pangram."""


class PangramResponseError(PangramError):
    """Invalid Pangram API response."""


def scrub_secret(message: object, api_key: str | None = None) -> str:
    text = str(message)
    if api_key:
        key = api_key.strip()
        if key:
            text = text.replace(key, mask_key(key))
    return text


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_window(window: Any) -> dict[str, Any]:
    if not isinstance(window, dict):
        raise PangramResponseError("Pangram response field `windows` must contain objects.")

    if "ai_assistance_score" in window:
        score = window["ai_assistance_score"]
        if not _is_number(score) or not 0.0 <= float(score) <= 1.0:
            raise PangramResponseError("Pangram response field `windows[].ai_assistance_score` is invalid.")
    for field in ("start_index", "end_index", "word_count", "token_length"):
        if field in window and not _is_nonnegative_int(window[field]):
            raise PangramResponseError(f"Pangram response field `windows[].{field}` is invalid.")
    if (
        "start_index" in window
        and "end_index" in window
        and window["end_index"] < window["start_index"]
    ):
        raise PangramResponseError("Pangram response window end_index is before start_index.")
    for field in ("text", "label", "confidence"):
        if field in window and not isinstance(window[field], str):
            raise PangramResponseError(f"Pangram response field `windows[].{field}` is invalid.")
    return dict(window)


def validate_pangram_response(payload: Any) -> dict[str, Any]:
    """Validate the fields this skill depends on without coercing strings."""

    if not isinstance(payload, dict):
        raise PangramResponseError("Pangram API returned a non-object JSON response.")

    for field in STRING_FIELDS:
        if field not in payload or not isinstance(payload[field], str):
            raise PangramResponseError(f"Pangram response field `{field}` must be a string.")

    for field in FRACTION_FIELDS:
        value = payload.get(field)
        if not _is_number(value) or not 0.0 <= float(value) <= 1.0:
            raise PangramResponseError(f"Pangram response field `{field}` must be a number from 0.0 to 1.0.")

    for field in COUNT_FIELDS:
        if not _is_nonnegative_int(payload.get(field)):
            raise PangramResponseError(f"Pangram response field `{field}` must be a nonnegative integer.")

    if "dashboard_link" in payload and not isinstance(payload["dashboard_link"], str):
        raise PangramResponseError("Pangram response field `dashboard_link` must be a string.")

    result = dict(payload)
    windows = payload.get("windows", [])
    if windows is None:
        windows = []
    if not isinstance(windows, list):
        raise PangramResponseError("Pangram response field `windows` must be a list.")
    result["windows"] = [_validate_window(window) for window in windows]
    return result


def call_pangram_api(
    text: str,
    public_dashboard_link: bool,
    api_key: str,
    opener: Callable[..., Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Post text to Pangram V3 and return a validated JSON response."""

    if not api_key or not api_key.strip():
        raise PangramAPIError("Missing Pangram API key.")

    body = json.dumps(
        {"text": text, "public_dashboard_link": bool(public_dashboard_link)},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        PANGRAM_V3_URL,
        data=body,
        headers={"Content-Type": "application/json", "x-api-key": api_key.strip()},
        method="POST",
    )
    urlopen = urllib.request.urlopen if opener is None else opener

    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            reason = getattr(response, "reason", "")
            raw = response.read()
    except urllib.error.HTTPError as exc:
        reason = scrub_secret(exc.reason, api_key)
        raise PangramAPIError(f"Pangram API returned HTTP {exc.code} {reason}.") from exc
    except urllib.error.URLError as exc:
        reason = scrub_secret(exc.reason, api_key)
        raise PangramAPIError(f"Pangram API request failed: {reason}.") from exc
    except OSError as exc:
        reason = scrub_secret(exc, api_key)
        raise PangramAPIError(f"Pangram API request failed: {reason}.") from exc

    if status < 200 or status >= 300:
        suffix = f" {reason}" if reason else ""
        raise PangramAPIError(f"Pangram API returned HTTP {status}{suffix}.")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PangramResponseError("Pangram API returned malformed JSON.") from exc

    return validate_pangram_response(payload)


def _last_paragraph_boundary(text: str, start: int, limit: int) -> int | None:
    best: int | None = None
    search_from = start
    while True:
        index = text.find("\n\n", search_from, limit)
        if index == -1:
            return best
        boundary = index + 2
        if boundary > start:
            best = boundary
        search_from = index + 2


def _last_sentence_boundary(text: str, start: int, limit: int) -> int | None:
    best: int | None = None
    for match in re.finditer(r"[.!?](?=\s)", text[start:limit]):
        boundary = start + match.end()
        if boundary > start:
            best = boundary
    return best


def chunk_text(text: str, max_chars: int = 40000) -> list[tuple[int, str]]:
    """Split text into chunks while preserving exact reconstruction and offsets."""

    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")
    if text == "":
        return []

    chunks: list[tuple[int, str]] = []
    start = 0
    length = len(text)
    while start < length:
        limit = min(start + max_chars, length)
        if limit == length:
            chunks.append((start, text[start:limit]))
            break

        split_at = _last_paragraph_boundary(text, start, limit)
        if split_at is None:
            split_at = _last_sentence_boundary(text, start, limit)
        if split_at is None or split_at <= start:
            split_at = limit

        chunks.append((start, text[start:split_at]))
        start = split_at

    return chunks


def _rank_windows(responses: Iterable[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for offset, response in responses:
        for window in response.get("windows", []):
            score = window.get("ai_assistance_score")
            start_index = window.get("start_index")
            end_index = window.get("end_index")
            if not (_is_number(score) and _is_nonnegative_int(start_index) and _is_nonnegative_int(end_index)):
                continue
            adjusted = dict(window)
            adjusted["start_index"] = start_index + offset
            adjusted["end_index"] = end_index + offset
            windows.append(adjusted)
    return sorted(windows, key=lambda item: float(item["ai_assistance_score"]), reverse=True)[:5]


def aggregate_chunk_responses(
    text: str,
    chunk_responses: list[tuple[int, str, dict[str, Any]]],
) -> dict[str, Any]:
    """Aggregate validated Pangram responses from text chunks."""

    if len(chunk_responses) == 1:
        return dict(chunk_responses[0][2])

    total_chars = sum(len(chunk) for _, chunk, _ in chunk_responses)
    if total_chars <= 0:
        raise PangramResponseError("Cannot aggregate empty Pangram chunks.")

    result: dict[str, Any] = {
        "headline": "Multi-chunk Pangram analysis",
        "prediction_short": "Mixed",
        "text": text,
        "num_chunks": len(chunk_responses),
    }

    predictions = {response["prediction_short"] for _, _, response in chunk_responses}
    if len(predictions) == 1:
        result["prediction_short"] = next(iter(predictions))

    for field in FRACTION_FIELDS:
        result[field] = sum(float(response[field]) * len(chunk) for _, chunk, response in chunk_responses) / total_chars
    for field in COUNT_FIELDS:
        result[field] = sum(int(response[field]) for _, _, response in chunk_responses)

    offset_responses = [(offset, response) for offset, _, response in chunk_responses]
    result["windows"] = _rank_windows(offset_responses)

    chunk_dashboard_links = []
    for index, (offset, _, response) in enumerate(chunk_responses):
        link = response.get("dashboard_link")
        if isinstance(link, str) and link:
            chunk_dashboard_links.append(
                {"chunk_index": index, "start_offset": offset, "dashboard_link": link}
            )
    if chunk_dashboard_links:
        result["chunk_dashboard_links"] = chunk_dashboard_links

    return result


def analyze_text(
    text: str,
    public_dashboard_link: bool,
    api_key: str,
    opener: Callable[..., Any] | None = None,
    timeout: int = 30,
    max_chars: int = 40000,
) -> dict[str, Any]:
    chunks = chunk_text(text, max_chars=max_chars)
    responses: list[tuple[int, str, dict[str, Any]]] = []
    for offset, chunk in chunks:
        response = call_pangram_api(
            chunk,
            public_dashboard_link=public_dashboard_link,
            api_key=api_key,
            opener=opener,
            timeout=timeout,
        )
        responses.append((offset, chunk, response))
    return aggregate_chunk_responses(text, responses)


def has_controlling_tty() -> bool:
    if os.name == "nt":
        return sys.stdin.isatty()
    try:
        with open("/dev/tty", "r", encoding="utf-8"):
            return True
    except OSError:
        return False


def resolve_api_key(
    prompt_key: bool,
    project_root: Path | None = None,
    prompt_fn: Callable[[str], str] | None = None,
    has_tty_fn: Callable[[], bool] | None = None,
) -> str:
    discovery = find_pangram_api_key(project_root)
    if discovery.found and discovery.api_key:
        return discovery.api_key

    if not prompt_key:
        raise PangramUsageError(MISSING_KEY_MESSAGE)

    tty_check = has_controlling_tty if has_tty_fn is None else has_tty_fn
    if not tty_check():
        raise PangramUsageError("No controlling TTY is available for --prompt-key.")

    prompt = getpass.getpass if prompt_fn is None else prompt_fn
    key = prompt("PANGRAM_API_KEY: ").strip()
    if not key:
        raise PangramUsageError(MISSING_KEY_MESSAGE)
    return key


def read_input_text(args: argparse.Namespace, stdin: TextIO) -> str:
    if args.text is not None:
        text = args.text
    elif args.file is not None:
        try:
            text = args.file.read_text(encoding="utf-8")
        except OSError as exc:
            raise PangramUsageError(f"Could not read input file: {exc}.") from exc
    else:
        if stdin.isatty():
            raise PangramUsageError("No input text provided. Pass --text, --file, or pipe text on stdin.")
        text = stdin.read()

    if not text or not text.strip():
        raise PangramUsageError("Input text is empty. Exiting without running the Pangram skill.")
    return text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check writing with Pangram V3 AI detection.")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", default=None, help="Text to check.")
    input_group.add_argument("--file", type=Path, default=None, help="UTF-8 text file to check.")
    parser.add_argument("--prompt-key", action="store_true", help="Prompt for PANGRAM_API_KEY if not discovered.")
    parser.add_argument(
        "--public-dashboard-link",
        action="store_true",
        help="Request public dashboard links from Pangram.",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Print parseable JSON.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Directory to start upward .env/.envrc key discovery from.",
    )
    return parser


def _json_safe_result(result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(result)
    return safe


def format_human_result(result: dict[str, Any]) -> str:
    lines = [
        f"Headline: {result['headline']}",
        f"Prediction: {result['prediction_short']}",
        "Fractions:",
        f"  AI: {float(result['fraction_ai']):.3f}",
        f"  AI-assisted: {float(result['fraction_ai_assisted']):.3f}",
        f"  Human: {float(result['fraction_human']):.3f}",
        "Segments:",
        f"  AI: {int(result['num_ai_segments'])}",
        f"  AI-assisted: {int(result['num_ai_assisted_segments'])}",
        f"  Human: {int(result['num_human_segments'])}",
    ]

    dashboard_link = result.get("dashboard_link")
    if isinstance(dashboard_link, str) and dashboard_link:
        lines.append(f"Dashboard: {dashboard_link}")

    chunk_links = result.get("chunk_dashboard_links")
    if isinstance(chunk_links, list) and chunk_links:
        lines.append("Chunk dashboard links:")
        for item in chunk_links:
            lines.append(
                f"  Chunk {int(item['chunk_index']) + 1} @ {int(item['start_offset'])}: "
                f"{item['dashboard_link']}"
            )

    windows = result.get("windows")
    if isinstance(windows, list) and windows:
        lines.append("Top windows:")
        for window in windows[:5]:
            label = window.get("label", "unlabeled")
            confidence = window.get("confidence", "unknown confidence")
            lines.append(
                f"  {window['start_index']}-{window['end_index']} "
                f"score={float(window['ai_assistance_score']):.3f} "
                f"label={label} confidence={confidence}"
            )

    return "\n".join(lines)


def _emit_error(message: str, exit_code: int, json_output: bool, stderr: TextIO) -> None:
    if json_output:
        print(json.dumps({"error": message, "exit_code": exit_code}, sort_keys=True), file=stderr)
    else:
        print(message, file=stderr)


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    opener: Callable[..., Any] | None = None,
    prompt_fn: Callable[[str], str] | None = None,
    has_tty_fn: Callable[[], bool] | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    api_key: str | None = None
    try:
        text = read_input_text(args, stdin)
        api_key = resolve_api_key(args.prompt_key, args.project_root, prompt_fn, has_tty_fn)
        result = analyze_text(
            text,
            public_dashboard_link=args.public_dashboard_link,
            api_key=api_key,
            opener=opener,
        )
    except PangramUsageError as exc:
        _emit_error(scrub_secret(exc, api_key), 2, args.json_output, stderr)
        return 2
    except PangramError as exc:
        _emit_error(scrub_secret(exc, api_key), 4, args.json_output, stderr)
        return 4

    if args.json_output:
        print(json.dumps(_json_safe_result(result), sort_keys=True), file=stdout)
    else:
        print(format_human_result(result), file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
