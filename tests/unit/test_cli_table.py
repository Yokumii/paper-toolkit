"""CLI integration tests for `paper table ...`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app


def _init_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        app,
        ["init", "--title", "Demo", "--workspace", str(tmp_path)],
    )


def test_render_missing_spec_returns_spec_not_found(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["table", "render", "--spec", str(tmp_path / "missing.json"), "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "TABLE_SPEC_NOT_FOUND"


def test_render_invalid_spec_returns_spec_invalid(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_path = tmp_path / "paper" / "table_specs" / "bad.json"
    spec_path.write_text(
        json.dumps(
            {
                "id": "bad",
                "caption": "Mismatch",
                "columns": [{"header": "A"}, {"header": "B"}],
                "rows": [["only one"]],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app, ["table", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)]
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "TABLE_SPEC_INVALID"


def test_render_happy_path_writes_tex(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_path = tmp_path / "paper" / "table_specs" / "tab1.json"
    spec_path.write_text(
        json.dumps(
            {
                "id": "tab1",
                "caption": "Demo",
                "columns": [{"header": "A"}, {"header": "B", "align": "r"}],
                "rows": [["a1", "b1"], ["a2", "b2"]],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app, ["table", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)]
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    tex_path = Path(payload["result"]["tex_path"])
    assert tex_path.is_file()
    content = tex_path.read_text(encoding="utf-8")
    assert "\\toprule" in content
    assert "\\label{tab:tab1}" in content


def test_render_all_iterates_spec_dir(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_dir = tmp_path / "paper" / "table_specs"
    for table_id in ("tab_a", "tab_b"):
        (spec_dir / f"{table_id}.json").write_text(
            json.dumps(
                {
                    "id": table_id,
                    "caption": "Demo",
                    "columns": [{"header": "X"}],
                    "rows": [["v"]],
                }
            ),
            encoding="utf-8",
        )
    runner = CliRunner()
    result = runner.invoke(app, ["table", "render-all", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    ids = sorted(entry["table_id"] for entry in payload["result"]["rendered"])
    assert ids == ["tab_a", "tab_b"]
