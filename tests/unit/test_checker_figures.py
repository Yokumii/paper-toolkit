from pathlib import Path

from paper_toolkit.checkers.figures import check_figures
from paper_toolkit.models.paper_state import FigureArtifact
from paper_toolkit.models.venue import load_venue
from paper_toolkit.state.workspace import init_workspace, write_state


def test_figures_checker_reports_unreferenced_and_missing_packed_file(tmp_path: Path) -> None:
    state = init_workspace(workspace=tmp_path, title="Demo", venue="nature", language="en")
    state.artifacts.figures = [
        FigureArtifact(
            id="fig1",
            src=str(tmp_path / "source.png"),
            packed="paper/figures/fig1.png",
            caption="Short caption.",
            referenced_by=[],
        )
    ]
    write_state(workspace=tmp_path, state=state)
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "results.tex").write_text("See Figure~\\ref{fig:missing}.\n", encoding="utf-8")

    report = check_figures(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )

    codes = [issue.code for issue in report.issues]
    assert "FIGURE_MISSING_FILE" in codes
    assert "FIGURE_UNREFERENCED" in codes
    assert "FIGURE_UNRESOLVED_REF" in codes


def test_figures_checker_passes_referenced_existing_figure(tmp_path: Path) -> None:
    state = init_workspace(workspace=tmp_path, title="Demo", venue="nature", language="en")
    fig = tmp_path / "paper" / "figures" / "fig1.png"
    fig.parent.mkdir(parents=True, exist_ok=True)
    fig.write_text("fake image", encoding="utf-8")
    state.artifacts.figures = [
        FigureArtifact(
            id="fig1",
            src=str(tmp_path / "source.png"),
            packed="paper/figures/fig1.png",
            caption=(
                "This caption has enough words to satisfy the lower bound for the "
                "configured Nature venue caption checker."
            ),
            referenced_by=["results"],
        )
    ]
    write_state(workspace=tmp_path, state=state)
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "results.tex").write_text("See Figure~\\ref{fig:fig1}.\n", encoding="utf-8")

    report = check_figures(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )

    assert report.ok is True


def test_figures_checker_flags_redundant_caption_prefix(tmp_path: Path) -> None:
    init_workspace(workspace=tmp_path, title="Demo", venue="nature", language="en")
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "results.tex").write_text(
        "\\begin{figure}[tbp]\n"
        "\\includegraphics{x}\n"
        "\\caption{Figure 1. Endline outcome distribution.}\n"
        "\\label{fig:x}\n"
        "\\end{figure}\n",
        encoding="utf-8",
    )

    report = check_figures(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )
    codes = [i.code for i in report.issues]
    assert "FIGURE_REDUNDANT_CAPTION_PREFIX" in codes


def test_figures_checker_flags_bad_float_placement(tmp_path: Path) -> None:
    init_workspace(workspace=tmp_path, title="Demo", venue="nature", language="en")
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "intro.tex").write_text(
        "\\begin{figure}[h!]\n\\caption{ok}\n\\label{fig:a}\n\\end{figure}\n"
        "\\begin{figure}[t]\n\\caption{ok}\n\\label{fig:b}\n\\end{figure}\n"
        "\\begin{figure}[tbp]\n\\caption{ok}\n\\label{fig:c}\n\\end{figure}\n",
        encoding="utf-8",
    )

    report = check_figures(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )
    bad = [i for i in report.issues if i.code == "FIGURE_BAD_FLOAT_PLACEMENT"]
    # [h!] and [t] should fire; [tbp] should not.
    assert len(bad) == 2


def test_figures_checker_flags_duplicate_figure_label(tmp_path: Path) -> None:
    init_workspace(workspace=tmp_path, title="Demo", venue="nature", language="en")
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    fig_block = (
        "\\begin{{figure}}[tbp]\n\\includegraphics{{x}}\n"
        "\\caption{{ok}}\n\\label{{{label}}}\n\\end{{figure}}\n"
    )
    (sections / "intro.tex").write_text(fig_block.format(label="fig:x"), encoding="utf-8")
    (sections / "results.tex").write_text(fig_block.format(label="fig:x"), encoding="utf-8")

    report = check_figures(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )
    dup = [i for i in report.issues if i.code == "FIGURE_DUPLICATE_ENV"]
    assert len(dup) == 1
    assert "intro" in dup[0].message and "results" in dup[0].message
