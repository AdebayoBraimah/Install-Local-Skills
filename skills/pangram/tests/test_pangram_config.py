from __future__ import annotations

from pathlib import Path

import pangram_config


def repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".git").mkdir()
    return root


def test_environment_key_takes_precedence(tmp_path: Path) -> None:
    root = repo_root(tmp_path)
    (root / ".env").write_text("PANGRAM_API_KEY=pg_from_file\n", encoding="utf-8")

    discovery = pangram_config.find_pangram_api_key(root, environ={"PANGRAM_API_KEY": " pg_from_env "})

    assert discovery.api_key == "pg_from_env"
    assert discovery.source == "environment"


def test_dotenv_parsing_supports_export_quotes_whitespace_and_comments() -> None:
    assert pangram_config.parse_pangram_key_line("PANGRAM_API_KEY=pg_plain # comment") == "pg_plain"
    assert pangram_config.parse_pangram_key_line(" export PANGRAM_API_KEY = 'pg quoted # kept' ") == (
        "pg quoted # kept"
    )
    assert pangram_config.parse_pangram_key_line('PANGRAM_API_KEY="pg_double" # comment') == "pg_double"
    assert pangram_config.parse_pangram_key_line("PANGRAM_API_KEY=pg_hash#kept") == "pg_hash#kept"
    assert pangram_config.parse_pangram_key_line("PANGRAM_API_KEY=   ") is None
    assert pangram_config.parse_pangram_key_line("NOT_PANGRAM_API_KEY=pg_wrong") is None
    assert pangram_config.parse_pangram_key_line("# PANGRAM_API_KEY=pg_comment") is None


def test_dotenv_precedes_envrc_in_same_directory(tmp_path: Path) -> None:
    root = repo_root(tmp_path)
    (root / ".env").write_text("PANGRAM_API_KEY=pg_env\n", encoding="utf-8")
    (root / ".envrc").write_text("export PANGRAM_API_KEY=pg_envrc\n", encoding="utf-8")

    discovery = pangram_config.find_pangram_api_key(root, environ={})

    assert discovery.api_key == "pg_env"
    assert discovery.source == str(root / ".env")


def test_upward_search_uses_nearest_key_and_includes_vcs_root(tmp_path: Path) -> None:
    root = repo_root(tmp_path)
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    (root / ".env").write_text("PANGRAM_API_KEY=pg_root\n", encoding="utf-8")
    (nested / ".envrc").write_text("export PANGRAM_API_KEY=pg_nested\n", encoding="utf-8")

    discovery = pangram_config.find_pangram_api_key(nested, environ={})

    assert discovery.api_key == "pg_nested"
    assert discovery.source == str(nested / ".envrc")

    (nested / ".envrc").unlink()
    discovery = pangram_config.find_pangram_api_key(nested, environ={})
    assert discovery.api_key == "pg_root"
    assert discovery.source == str(root / ".env")


def test_upward_search_stops_after_first_vcs_root(tmp_path: Path) -> None:
    parent_key = tmp_path / ".env"
    parent_key.write_text("PANGRAM_API_KEY=pg_parent\n", encoding="utf-8")
    root = repo_root(tmp_path)
    nested = root / "child"
    nested.mkdir()

    discovery = pangram_config.find_pangram_api_key(nested, environ={})

    assert discovery.api_key is None
    assert discovery.source is None


def test_empty_values_are_skipped_without_mutating_files(tmp_path: Path) -> None:
    root = repo_root(tmp_path)
    nested = root / "child"
    nested.mkdir()
    nested_env = nested / ".env"
    root_env = root / ".env"
    nested_content = "PANGRAM_API_KEY=\n"
    root_content = "PANGRAM_API_KEY=pg_root\n"
    nested_env.write_text(nested_content, encoding="utf-8")
    root_env.write_text(root_content, encoding="utf-8")

    discovery = pangram_config.find_pangram_api_key(nested, environ={})

    assert discovery.api_key == "pg_root"
    assert nested_env.read_text(encoding="utf-8") == nested_content
    assert root_env.read_text(encoding="utf-8") == root_content


def test_mask_key_never_returns_full_key() -> None:
    key = "pg_supersecretabcd"

    masked = pangram_config.mask_key(key)

    assert masked == "pg_****abcd"
    assert key not in masked
