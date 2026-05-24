import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app


def test_template_list_and_expand(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )

    listed = runner.invoke(app, ["template", "list", "--workspace", str(tmp_path)])
    assert listed.exit_code == 0
    payload = json.loads(listed.stdout)
    assert "intro" in payload["result"]["templates"]

    expanded = runner.invoke(
        app, ["template", "expand", "--section", "intro", "--workspace", str(tmp_path)]
    )
    assert expanded.exit_code == 0
    expanded_payload = json.loads(expanded.stdout)
    assert expanded_payload["result"]["section_path"].endswith("paper/sections/intro.tex")
    assert "% slot: hook" in (tmp_path / "paper" / "sections" / "intro.tex").read_text(
        encoding="utf-8"
    )


def test_template_expand_returns_envelope_error_for_missing_template(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )

    result = runner.invoke(
        app, ["template", "expand", "--section", "unknown", "--workspace", str(tmp_path)]
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "TEMPLATE_NOT_FOUND"
