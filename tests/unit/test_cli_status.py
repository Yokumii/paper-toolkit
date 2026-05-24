import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app

runner = CliRunner()


def _init(tmp_workspace: Path) -> None:
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


def test_paper_status_on_initialized_workspace(tmp_workspace: Path) -> None:
    _init(tmp_workspace)
    result = runner.invoke(app, ["status", "--workspace", str(tmp_workspace)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "status"
    assert payload["result"]["title"] == "Demo"
    assert payload["result"]["venue"] == "nature"
    summary = payload["state_summary"]
    assert summary["section_count"] == 0
    assert summary["figure_count"] == 0
    assert summary["graph_valid"] is True


def test_paper_status_on_uninitialized_workspace(tmp_workspace: Path) -> None:
    result = runner.invoke(app, ["status", "--workspace", str(tmp_workspace)])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    codes = [e["code"] for e in payload["errors"]]
    assert "WS_NOT_INITIALIZED" in codes


def test_paper_status_verbose_state_returns_full_paper_json(tmp_workspace: Path) -> None:
    _init(tmp_workspace)
    result = runner.invoke(app, ["status", "--workspace", str(tmp_workspace), "--verbose-state"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    # --verbose-state replaces state_summary with the full paper.json content.
    state = payload["state_summary"]
    assert state["schema_version"] == "1.0"
    assert state["meta"]["title"] == "Demo"
    assert state["meta"]["venue"] == "nature"
    assert "artifacts" in state


def test_paper_status_verbose_state_on_uninitialized_falls_back(tmp_workspace: Path) -> None:
    # --verbose-state with no paper.json: keep the compact zero-summary.
    result = runner.invoke(app, ["status", "--workspace", str(tmp_workspace), "--verbose-state"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "section_count" in payload["state_summary"]


def test_paper_internal_error_returns_envelope(tmp_workspace: Path, monkeypatch) -> None:
    """An uncaught exception must surface as an INTERNAL_ERROR envelope, not a traceback."""
    from paper_toolkit.cli import status as status_cmd

    def boom(*args, **kwargs):
        raise RuntimeError("synthetic crash")

    monkeypatch.setattr(status_cmd, "run", boom)
    result = runner.invoke(app, ["status", "--workspace", str(tmp_workspace)])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    codes = [e["code"] for e in payload["errors"]]
    assert "INTERNAL_ERROR" in codes
    assert "synthetic crash" in payload["errors"][0]["message"]
