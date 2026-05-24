import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app

runner = CliRunner()


def test_paper_init_creates_workspace(tmp_workspace: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "--title",
            "Demo",
            "--venue",
            "nature",
            "--language",
            "en",
            "--workspace",
            str(tmp_workspace),
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "init"
    assert payload["result"]["paper_state_path"].endswith("paper/paper.json")
    assert (tmp_workspace / "paper" / "paper.json").is_file()
    assert (tmp_workspace / "paper" / "sections").is_dir()
    assert (tmp_workspace / "paper" / "figures").is_dir()


def test_paper_init_refuses_double_init(tmp_workspace: Path) -> None:
    runner.invoke(
        app,
        [
            "init",
            "--title",
            "Demo",
            "--venue",
            "nature",
            "--language",
            "en",
            "--workspace",
            str(tmp_workspace),
        ],
    )
    result = runner.invoke(
        app,
        [
            "init",
            "--title",
            "Demo",
            "--venue",
            "nature",
            "--language",
            "en",
            "--workspace",
            str(tmp_workspace),
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    codes = [e["code"] for e in payload["errors"]]
    assert "WS_ALREADY_INITIALIZED" in codes


def test_paper_init_rejects_bad_language(tmp_workspace: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "--title",
            "Demo",
            "--venue",
            "nature",
            "--language",
            "fr",
            "--workspace",
            str(tmp_workspace),
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    codes = [e["code"] for e in payload["errors"]]
    assert "INIT_BAD_LANGUAGE" in codes


def test_paper_init_human_mode(tmp_workspace: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "--title",
            "Demo",
            "--venue",
            "nature",
            "--language",
            "en",
            "--workspace",
            str(tmp_workspace),
            "--human",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "[OK] init" in result.stdout
    assert "sections=0" in result.stdout
