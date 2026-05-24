import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app


def test_cli_check_style_and_all(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "intro.tex").write_text(
        "In this paper, we propose a system---bad.\n", encoding="utf-8"
    )

    style = runner.invoke(
        app, ["check", "style", "--section", "intro", "--workspace", str(tmp_path)]
    )
    assert style.exit_code == 1
    style_payload = json.loads(style.stdout)
    assert style_payload["action"] == "check.style"
    assert style_payload["result"]["checker"] == "style"
    assert style_payload["errors"][0]["code"] == "STYLE_BANNED_PUNCT"

    all_result = runner.invoke(
        app, ["check", "all", "--section", "intro", "--workspace", str(tmp_path)]
    )
    assert all_result.exit_code == 1
    assert json.loads(all_result.stdout)["result"]["checker"] == "all"


def test_cli_check_word_count_warning_exits_zero(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "intro.tex").write_text("Too short.\n", encoding="utf-8")

    result = runner.invoke(
        app, ["check", "word-count", "--section", "intro", "--workspace", str(tmp_path)]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["warnings"][0].startswith("WORD_COUNT_LOW")
