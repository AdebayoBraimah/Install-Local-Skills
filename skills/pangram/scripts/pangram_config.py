"""Safe discovery of PANGRAM_API_KEY for the Pangram skill."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

KEY_NAME = "PANGRAM_API_KEY"
ENV_FILENAMES = (".env", ".envrc")
MISSING_KEY_MESSAGE = (
    "PANGRAM_API_KEY was not found in the environment, `.env`, or `.envrc`, "
    "and no key was provided. Exiting without running the Pangram skill."
)


@dataclass(frozen=True)
class KeyDiscovery:
    """Result of a Pangram API key lookup."""

    api_key: str | None
    source: str | None = None

    @property
    def found(self) -> bool:
        return bool(self.api_key)


def mask_key(api_key: str | None) -> str:
    """Return a non-secret status string for a Pangram key."""

    if not api_key:
        return "****"
    key = api_key.strip()
    if len(key) <= 4:
        return "****"
    suffix = key[-4:]
    if key.startswith("pg_"):
        return f"pg_****{suffix}"
    return f"****{suffix}"


def _strip_unquoted_comment(value: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_double:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index]
    return value


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_pangram_key_line(line: str) -> str | None:
    """Parse one dotenv-style line and return a non-empty key value if present."""

    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    match = re.match(r"^(?:export\s+)?PANGRAM_API_KEY\s*=\s*(.*)$", stripped)
    if not match:
        return None

    raw_value = _strip_unquoted_comment(match.group(1)).strip()
    value = _unquote(raw_value).strip()
    return value or None


def _as_directory(path: Path) -> Path:
    path = path.expanduser()
    if path.exists() and path.is_file():
        return path.parent.resolve()
    return path.resolve()


def iter_search_directories(project_root: Path | str | None = None) -> list[Path]:
    """Return directories searched from nearest to farthest, stopping at VCS root."""

    current = _as_directory(Path(project_root) if project_root is not None else Path.cwd())
    directories: list[Path] = []
    while True:
        directories.append(current)
        if (current / ".git").exists() or (current / ".hg").exists():
            break
        if current.parent == current:
            break
        current = current.parent
    return directories


def _read_key_from_file(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                key = parse_pangram_key_line(line)
                if key:
                    return key
    except OSError:
        return None
    return None


def find_pangram_api_key(
    project_root: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> KeyDiscovery:
    """Find PANGRAM_API_KEY without mutating files or process environment."""

    env = os.environ if environ is None else environ
    env_value = env.get(KEY_NAME)
    if env_value and env_value.strip():
        return KeyDiscovery(env_value.strip(), "environment")

    for directory in iter_search_directories(project_root):
        for filename in ENV_FILENAMES:
            path = directory / filename
            if not path.exists() or not path.is_file():
                continue
            key = _read_key_from_file(path)
            if key:
                return KeyDiscovery(key, str(path))

    return KeyDiscovery(None, None)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check safe Pangram API key discovery.")
    parser.add_argument("--check", action="store_true", help="Check whether PANGRAM_API_KEY is discoverable.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Directory to start upward .env/.envrc discovery from.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 2

    discovery = find_pangram_api_key(args.project_root)
    if discovery.found:
        print("PANGRAM_API_KEY found.")
        return 0

    print(MISSING_KEY_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
