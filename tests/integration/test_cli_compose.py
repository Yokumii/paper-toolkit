import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from paper_toolkit.cli.main import app


def _init_workspace(runner: CliRunner, workspace: Path) -> None:
    result = runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(workspace)])
    assert result.exit_code == 0


def test_cli_compose_write_bib_and_assemble_latex(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "add-citation",
                "--id",
                "ref1",
                "--cite-key",
                "smith2020",
                "--label",
                "Smith Study",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "intro.tex").write_text(
        "\\section{Intro}\nText \\cite{smith2020}.\n", encoding="utf-8"
    )

    bib = runner.invoke(app, ["compose", "write-bib", "--workspace", str(tmp_path)])
    assert bib.exit_code == 0
    bib_payload = json.loads(bib.stdout)
    assert bib_payload["ok"] is True
    assert bib_payload["result"]["bib_path"].endswith("paper/refs.bib")

    latex = runner.invoke(app, ["compose", "assemble-latex", "--workspace", str(tmp_path)])
    assert latex.exit_code == 0
    latex_payload = json.loads(latex.stdout)
    assert latex_payload["result"]["main_tex_path"].endswith("paper/main.tex")
    assert (tmp_path / "paper" / "main.tex").exists()


def test_cli_compose_pack_figures_from_figure_evidence(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    src = tmp_path / "source_fig.png"
    src.write_text("fake image", encoding="utf-8")
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "add-evidence",
                "--id",
                "e1",
                "--label",
                "Figure evidence",
                "--source-kind",
                "figure",
                "--source-ref",
                str(src),
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(app, ["compose", "pack-figures", "--workspace", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["result"]["packed_figure_count"] == 1
    assert (tmp_path / "paper" / "figures" / "fig1.png").exists()


def test_cli_compose_pack_figures_populates_referenced_by(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    # Section file that references fig1 and fig:1 (both spellings).
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "intro.tex").write_text(
        "See Fig. \\ref{fig1} and again \\ref{fig1}.\n", encoding="utf-8"
    )
    (sections / "results.tex").write_text("We also discuss Fig. \\ref{fig:1}.\n", encoding="utf-8")
    src = tmp_path / "source_fig.png"
    src.write_text("fake image", encoding="utf-8")
    runner.invoke(
        app,
        [
            "evidence",
            "add-evidence",
            "--id",
            "e1",
            "--label",
            "Fig",
            "--source-kind",
            "figure",
            "--source-ref",
            str(src),
            "--workspace",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["compose", "pack-figures", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    referenced_by = payload["result"]["referenced_by"]["fig1"]
    assert set(referenced_by) == {"intro", "results"}


def _write_bar_spec(tmp_path: Path, figure_id: str) -> Path:
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


def test_cli_compose_pack_figures_from_registered_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    runner = CliRunner()
    _init_workspace(runner, tmp_path)

    spec_path = _write_bar_spec(tmp_path, figure_id="fig_demo")
    assert (
        runner.invoke(
            app,
            ["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["figure", "register", "--spec", str(spec_path), "--workspace", str(tmp_path)],
        ).exit_code
        == 0
    )

    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "results.tex").write_text("Refer to \\ref{fig_demo}.\n", encoding="utf-8")

    result = runner.invoke(app, ["compose", "pack-figures", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["packed_figure_count"] == 1
    assert payload["result"]["referenced_by"]["fig_demo"] == ["results"]


def test_cli_compose_pack_figures_reports_missing_packed_pdf(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    spec_path = _write_bar_spec(tmp_path, figure_id="fig_orphan")
    # Render so the PDF exists, register, then delete the PDF to simulate the gap.
    runner.invoke(app, ["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)])
    runner.invoke(
        app, ["figure", "register", "--spec", str(spec_path), "--workspace", str(tmp_path)]
    )
    (tmp_path / "paper" / "figures" / "fig_orphan.pdf").unlink()

    result = runner.invoke(app, ["compose", "pack-figures", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "FIGURE_PACKED_MISSING"
    assert "fig_orphan" in payload["errors"][0]["message"]
