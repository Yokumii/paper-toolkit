"""Unit tests for `paper figure register` (the spec→paper.json bridge)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytest.importorskip("matplotlib")

from paper_toolkit.cli.main import app


def _init(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout


def _write_spec(tmp_path: Path, *, figure_id: str = "fig_demo") -> Path:
    spec = {
        "kind": "bar",
        "id": figure_id,
        "caption": "demo bar",
        "data": [{"arm": "A", "y": 0.4}, {"arm": "B", "y": 0.6}],
        "x_field": "arm",
        "y_field": "y",
    }
    target = tmp_path / "paper" / "figure_specs" / f"{figure_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(spec), encoding="utf-8")
    return target


def test_register_inserts_artifact_after_render(tmp_path: Path) -> None:
    _init(tmp_path)
    spec_path = _write_spec(tmp_path)
    runner = CliRunner()
    rendered = runner.invoke(
        app, ["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)]
    )
    assert rendered.exit_code == 0, rendered.stdout
    registered = runner.invoke(
        app,
        ["figure", "register", "--spec", str(spec_path), "--workspace", str(tmp_path)],
    )
    assert registered.exit_code == 0, registered.stdout
    payload = json.loads(registered.stdout)
    assert payload["result"]["action"] == "inserted"
    paper_json = json.loads((tmp_path / "paper" / "paper.json").read_text(encoding="utf-8"))
    assert any(
        f["id"] == "fig_demo" and f["packed"] == "paper/figures/fig_demo.pdf"
        for f in paper_json["artifacts"]["figures"]
    )


def test_register_fails_when_pdf_missing(tmp_path: Path) -> None:
    _init(tmp_path)
    spec_path = _write_spec(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["figure", "register", "--spec", str(spec_path), "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "FIG_PDF_MISSING"


def test_register_is_idempotent(tmp_path: Path) -> None:
    _init(tmp_path)
    spec_path = _write_spec(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)])
    runner.invoke(
        app, ["figure", "register", "--spec", str(spec_path), "--workspace", str(tmp_path)]
    )
    second = runner.invoke(
        app, ["figure", "register", "--spec", str(spec_path), "--workspace", str(tmp_path)]
    )
    assert second.exit_code == 0, second.stdout
    payload = json.loads(second.stdout)
    assert payload["result"]["action"] == "updated"
    paper_json = json.loads((tmp_path / "paper" / "paper.json").read_text(encoding="utf-8"))
    assert sum(1 for f in paper_json["artifacts"]["figures"] if f["id"] == "fig_demo") == 1
