import json
from pathlib import Path

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
