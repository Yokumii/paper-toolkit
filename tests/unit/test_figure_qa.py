"""End-to-end tests for the figure-qa checker."""

from __future__ import annotations

from pathlib import Path

import pytest

from paper_toolkit.checkers.figure_qa import (
    _font_is_approved,
    _strip_subset_prefix,
    check_figure_qa,
)
from paper_toolkit.figures.renderer import render_figure
from paper_toolkit.models.figure_spec import BarFigureSpec

pytest.importorskip("matplotlib")
pytest.importorskip("pypdf")


def test_strip_subset_prefix_removes_six_char_tag() -> None:
    assert _strip_subset_prefix("ABCDEF+ArialMT") == "ArialMT"
    assert _strip_subset_prefix("ArialMT") == "ArialMT"


def test_font_is_approved_accepts_arial_helvetica_dejavu() -> None:
    assert _font_is_approved("ABCDEF+ArialMT") is True
    assert _font_is_approved("Helvetica-Bold") is True
    assert _font_is_approved("DejaVuSans") is True
    assert _font_is_approved("CMR10") is False
    assert _font_is_approved("Times-Roman") is False


def _seed_workspace_with_rendered_bar(tmp_path: Path) -> None:
    (tmp_path / "paper" / "figures").mkdir(parents=True)
    spec = BarFigureSpec(
        id="fig_qa_demo",
        caption="QA demo",
        data=[{"arm": "A", "y": 0.4}, {"arm": "B", "y": 0.6}],
        x_field="arm",
        y_field="y",
    )
    render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)


def test_check_figure_qa_passes_for_toolkit_rendered_bar(tmp_path: Path) -> None:
    _seed_workspace_with_rendered_bar(tmp_path)
    report = check_figure_qa(workspace=tmp_path)
    assert report.checker == "figure-qa"
    # No errors — DejaVu Sans is approved + embedded by matplotlib with fonttype=42.
    assert all(issue.severity != "error" for issue in report.issues), [
        (i.code, i.message) for i in report.issues
    ]
    inspected = report.result["inspected"]
    assert any(entry["figure_id"] == "fig_qa_demo" for entry in inspected)
    entry = next(e for e in inspected if e["figure_id"] == "fig_qa_demo")
    assert entry["width_mm"] is not None
    # Single-column target is 89 mm; tolerance is ±10 mm.
    assert 75 <= entry["width_mm"] <= 105
    # Every reported font should be flagged embedded by our parser.
    assert all(font["embedded"] for font in entry["fonts"])


def test_check_figure_qa_returns_empty_report_when_no_figures_dir(tmp_path: Path) -> None:
    report = check_figure_qa(workspace=tmp_path)
    assert report.issues == []
    assert report.result["inspected"] == []


def test_check_figure_qa_flags_unreadable_pdf(tmp_path: Path) -> None:
    (tmp_path / "paper" / "figures").mkdir(parents=True)
    (tmp_path / "paper" / "figures" / "broken.pdf").write_bytes(b"not a pdf")
    report = check_figure_qa(workspace=tmp_path)
    codes = [issue.code for issue in report.issues]
    assert "FQA_UNREADABLE_PDF" in codes
