import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app

FIXTURE = Path(__file__).parents[1] / "fixtures" / "as_workspace"


def test_cli_scan_writes_research_pack_and_updates_state(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE, workspace)
    runner = CliRunner()

    init_result = runner.invoke(
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
            str(workspace),
        ],
    )
    assert init_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--workspace", str(workspace)])
    assert scan_result.exit_code == 0
    payload = json.loads(scan_result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "scan"
    assert payload["result"]["research_pack_path"].endswith("paper/research_pack.json")
    assert payload["result"]["hypothesis_count"] == 1
    assert payload["result"]["candidate_figure_count"] == 1
    assert payload["state_summary"]["last_updated_artifact"] == "paper/research_pack.json"

    paper_json = json.loads((workspace / "paper" / "paper.json").read_text())
    assert paper_json["artifacts"]["research_pack"]["path"] == "paper/research_pack.json"


def test_cli_scan_rejects_unknown_scanner(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)])
    assert init_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--scanner", "unknown", "--workspace", str(tmp_path)])
    assert scan_result.exit_code == 1
    payload = json.loads(scan_result.stdout)
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "SCAN_UNKNOWN_SCANNER"
