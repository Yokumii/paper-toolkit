import json
from pathlib import Path

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
