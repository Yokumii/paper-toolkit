import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app


def test_cli_compile_once_returns_missing_engine_envelope(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )
    (tmp_path / "paper" / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}\n", encoding="utf-8"
    )

    result = runner.invoke(
        app,
        ["compile-once", "--engine", "definitely-missing-engine", "--workspace", str(tmp_path)],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["action"] == "compile-once"
    assert payload["errors"][0]["code"] == "missing-engine"
    assert payload["state_summary"]["last_compile"]["id"] == "r1"
