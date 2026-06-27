from __future__ import annotations

import json

from obsidian_graphrag.markdown import parse_markdown
from obsidian_graphrag.staging import prepare_input


def test_markdown_extracts_frontmatter_links_and_image_refs() -> None:
    parsed = parse_markdown(
        """---
Title: Test Note
tags: [rlhf, safety]
---
Body with [[Some Note|alias]].
![Figure alt](../Files/Images/plot.png)
![[diagram.png|400]]
""",
    )

    assert parsed.frontmatter["Title"] == "Test Note"
    assert parsed.wikilinks == ["Some Note"]
    assert [ref.raw_target for ref in parsed.image_refs] == ["../Files/Images/plot.png", "diagram.png"]


def test_prepare_input_dry_run_writes_nothing(sample_config) -> None:
    vault = sample_config.vault_path
    (vault / "Ideas" / "note.md").write_text("hello", encoding="utf-8")

    result = prepare_input(sample_config, dry_run=True)

    assert result.document_count == 1
    assert not sample_config.input_json_path.exists()
    assert not sample_config.manifest_path.exists()


def test_prepare_input_writes_graphrag_json_and_manifest(sample_config) -> None:
    vault = sample_config.vault_path
    image = vault / "Files" / "Images" / "plot.png"
    image.write_bytes(b"not really a png")
    (vault / "Ideas" / "note.md").write_text(
        """---
Title: Utility Privacy
tags: [privacy]
Aliases: [UP]
Keywords: [utility, privacy]
Category: Research
---
Before figure.
![Tradeoff plot](plot.png)
After figure with [[Other Note]].
""",
        encoding="utf-8",
    )

    result = prepare_input(sample_config, dry_run=False)

    assert result.document_count == 1
    documents = json.loads(sample_config.input_json_path.read_text(encoding="utf-8"))
    manifest = json.loads(sample_config.manifest_path.read_text(encoding="utf-8"))
    document = documents[0]
    assert document["title"] == "Utility Privacy"
    assert "## Referenced Image Context" in document["text"]
    assert document["metadata"]["source_path"] == "Ideas/note.md"
    assert document["metadata"]["tags"] == ["privacy"]
    assert document["metadata"]["aliases"] == ["UP"]
    assert document["metadata"]["keywords"] == ["utility", "privacy"]
    assert document["metadata"]["category"] == "Research"
    assert document["metadata"]["wikilinks"] == ["Other Note"]
    assert document["metadata"]["image_refs"][0]["source_path"] == "Files/Images/plot.png"
    assert manifest["document_count"] == 1
