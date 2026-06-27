from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_graphrag.discover import discover_markdown_files, is_ignored, load_ignore_patterns


def test_ignore_pattern_semantics(sample_config) -> None:
    patterns = load_ignore_patterns(sample_config.ignore_patterns_path)

    assert is_ignored(".vault-graphrag/config/settings.yaml", patterns)
    assert is_ignored("Templates/lit.md", patterns)
    assert is_ignored("Ideas/Meetings/meeting-a-2026.md", patterns)
    assert is_ignored("misc/meeting-person.md", patterns)
    assert is_ignored("AGENTS.md", patterns)
    assert not is_ignored("Ideas/Research/paper.md", patterns)


def test_ignore_pattern_negation_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "ignore_patterns.txt"
    path.write_text("!Ideas/Keep.md\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Negation"):
        load_ignore_patterns(path)


def test_discover_includes_academic_notes_and_excludes_tooling(sample_config) -> None:
    vault = sample_config.vault_path
    (vault / "Ideas" / "Research").mkdir(parents=True)
    (vault / "Ideas" / "Research" / "paper.md").write_text("paper", encoding="utf-8")
    (vault / "Templates").mkdir()
    (vault / "Templates" / "template.md").write_text("template", encoding="utf-8")
    (vault / "AGENTS.md").write_text("tooling", encoding="utf-8")

    records = discover_markdown_files(sample_config)

    assert [record.relative_path for record in records] == ["Ideas/Research/paper.md"]
