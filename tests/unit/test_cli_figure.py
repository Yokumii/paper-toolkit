"""CLI integration tests for `paper figure ...`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytest.importorskip("matplotlib")

from paper_toolkit.cli.main import app


def _init_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "init",
            "--title",
            "Demo",
            "--workspace",
            str(tmp_path),
        ],
    )


def test_list_palettes_emits_sorted_names() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["figure", "list-palettes"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["palettes"] == sorted(payload["result"]["palettes"])
    assert "nmi_pastel" in payload["result"]["palettes"]


def test_render_missing_spec_returns_spec_not_found(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "figure",
            "render",
            "--spec",
            str(tmp_path / "missing.json"),
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "FIG_SPEC_NOT_FOUND"


def test_render_malformed_spec_returns_spec_invalid(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_path = tmp_path / "paper" / "figure_specs" / "bad.json"
    spec_path.write_text("{ this is not JSON", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "figure",
            "render",
            "--spec",
            str(spec_path),
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "FIG_SPEC_INVALID"


def test_render_happy_path_writes_pdf_and_wrapper(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_path = tmp_path / "paper" / "figure_specs" / "fig1.json"
    spec_path.write_text(
        json.dumps(
            {
                "id": "fig1",
                "kind": "bar",
                "caption": "Demo",
                "data": [{"arm": "A", "y": 0.4}, {"arm": "B", "y": 0.6}],
                "x_field": "arm",
                "y_field": "y",
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["figure_id"] == "fig1"
    assert Path(payload["result"]["pdf_path"]).is_file()
    assert Path(payload["result"]["tex_path"]).is_file()


def test_render_all_iterates_spec_dir(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_dir = tmp_path / "paper" / "figure_specs"
    for figure_id in ("a_fig", "b_fig"):
        (spec_dir / f"{figure_id}.json").write_text(
            json.dumps(
                {
                    "id": figure_id,
                    "kind": "bar",
                    "caption": "Demo",
                    "data": [{"arm": "x", "y": 1.0}],
                    "x_field": "arm",
                    "y_field": "y",
                }
            ),
            encoding="utf-8",
        )
    runner = CliRunner()
    result = runner.invoke(app, ["figure", "render-all", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    ids = sorted(entry["figure_id"] for entry in payload["result"]["rendered"])
    assert ids == ["a_fig", "b_fig"]


def test_render_script_spec_happy_path(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_dir = tmp_path / "paper" / "figure_specs"
    (spec_dir / "emit_script.py").write_text(
        """
from pathlib import Path
import sys

import matplotlib.pyplot as plt


def main(out_dir: str) -> None:
    out = Path(out_dir)
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    fig.savefig(out / "fig_script.pdf")
    fig.savefig(out / "fig_script.svg")
    plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
""".strip(),
        encoding="utf-8",
    )
    spec_path = spec_dir / "fig_script.json"
    spec_path.write_text(
        json.dumps(
            {
                "kind": "script",
                "id": "fig_script",
                "caption": "Scripted figure",
                "backend": "python",
                "entrypoint": "emit_script.py",
                "data": [],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["result"]["figure_id"] == "fig_script"
