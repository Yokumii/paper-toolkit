import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from paper_toolkit.cli.main import app
from paper_toolkit.models.venue import load_venue


def test_load_custom_workspace_venue_when_meta_venue_is_custom(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "venue.yaml").write_text(
        """
name: custom
sections:
  - { name: intro, word_range: [1, 10] }
style_rules:
  banned_phrases:
    - { pattern: "forbidden", reason: "custom phrase" }
""",
        encoding="utf-8",
    )

    venue = load_venue(workspace=tmp_path, venue_name="custom")

    assert venue.name == "custom"
    assert venue.word_range_for("intro") == (1, 10)


def test_check_cli_returns_json_envelope_for_custom_workspace_venue(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(
            app, ["init", "--title", "Demo", "--venue", "custom", "--workspace", str(tmp_path)]
        ).exit_code
        == 0
    )
    (tmp_path / "paper" / "venue.yaml").write_text(
        "name: custom\nsections:\n  - { name: intro, word_range: [1, 10] }\n",
        encoding="utf-8",
    )
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "intro.tex").write_text("hello world\n", encoding="utf-8")

    result = runner.invoke(
        app, ["check", "word-count", "--section", "intro", "--workspace", str(tmp_path)]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "check.word-count"


def test_load_venue_accepts_extends_key_as_documentation(tmp_path: Path) -> None:
    """`extends: nature` is intuitive but ignored — auto-merge already does this."""
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "venue.yaml").write_text(
        """
name: custom
extends: nature
sections:
  - { name: intro, word_range: [1, 10] }
""",
        encoding="utf-8",
    )

    venue = load_venue(workspace=tmp_path, venue_name="custom")

    assert venue.name == "custom"
    # nature defaults still merged in for fields the user didn't override.
    assert venue.citation_style == "nature"


def test_load_venue_unknown_name_without_yaml_explains_merge(tmp_path: Path) -> None:
    """Unknown venue name + no paper/venue.yaml should surface the auto-merge hint."""
    with pytest.raises(ValueError, match="merged on top of the built-in nature defaults"):
        load_venue(workspace=tmp_path, venue_name="MyCustomVenue")


def test_init_with_custom_venue_scaffolds_venue_yaml(tmp_path: Path) -> None:
    """`paper init --venue X` (non-nature) writes a paper/venue.yaml stub so later checks load."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "--title", "Demo", "--venue", "MyCustomVenue", "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["result"]["venue"] == "MyCustomVenue"
    assert payload["result"]["scaffolded_venue_yaml"].endswith("paper/venue.yaml")

    venue_yaml = tmp_path / "paper" / "venue.yaml"
    assert venue_yaml.exists()
    text = venue_yaml.read_text(encoding="utf-8")
    assert "name: MyCustomVenue" in text
    # The scaffolded file should also load cleanly via load_venue.
    venue = load_venue(workspace=tmp_path, venue_name="MyCustomVenue")
    assert venue.name == "MyCustomVenue"
    assert venue.citation_style == "nature"


def test_init_with_default_nature_venue_does_not_scaffold_venue_yaml(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app, ["init", "--title", "Demo", "--venue", "nature", "--workspace", str(tmp_path)]
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "scaffolded_venue_yaml" not in payload["result"]
    assert not (tmp_path / "paper" / "venue.yaml").exists()
