from pathlib import Path

from paper_toolkit.models.venue import load_venue


def test_load_builtin_nature_venue() -> None:
    venue = load_venue(workspace=Path("/tmp/no-workspace"), venue_name="nature")

    assert venue.name == "nature"
    assert venue.section_names == ["abstract", "intro", "results", "discussion", "methods"]
    assert venue.word_range_for("intro") == (400, 800)
    assert venue.figure_constraints.caption_words == (25, 200)
    assert any(rule.pattern == "---" for rule in venue.style_rules.banned_punct)


def test_workspace_venue_override_merges_sections_and_style(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "venue.yaml").write_text(
        """
name: custom
sections:
  - { name: intro, word_range: [10, 20] }
style_rules:
  banned_phrases:
    - { pattern: "forbidden", reason: "custom phrase" }
""",
        encoding="utf-8",
    )

    venue = load_venue(workspace=tmp_path, venue_name="nature")

    assert venue.name == "custom"
    assert venue.word_range_for("intro") == (10, 20)
    assert any(rule.pattern == "forbidden" for rule in venue.style_rules.banned_phrases)
