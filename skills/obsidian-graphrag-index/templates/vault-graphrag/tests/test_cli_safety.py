from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from obsidian_graphrag.graphrag_cli import has_real_api_key, load_graphrag_env


ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_index_requires_no_api_key() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "index_graphrag.py"), "--dry-run", "--json"],
        cwd=ROOT.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["operation"] == "index"
    assert payload["dry_run"] is True


def test_paid_index_without_flag_exits_two() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "index_graphrag.py")],
        cwd=ROOT.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 2
    assert "paid GraphRAG operation" in completed.stderr


def test_env_loader_allows_only_graphrag_keys(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "GRAPHRAG_API_KEY=replace-with-rotated-key",
                "GRAPHRAG_MODEL=gpt-5-nano",
                "OPENAI_API_KEY=should-not-pass-through",
            ]
        ),
        encoding="utf-8",
    )

    values = load_graphrag_env(env_path)

    assert "OPENAI_API_KEY" not in values
    assert values["GRAPHRAG_MODEL"] == "gpt-5-nano"
    assert not has_real_api_key(values)
