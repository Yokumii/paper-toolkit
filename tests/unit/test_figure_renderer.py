"""End-to-end tests for the figure renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from paper_toolkit.figures import renderer as renderer_mod
from paper_toolkit.figures.renderer import render_figure
from paper_toolkit.models.figure_spec import (
    BarFigureSpec,
    FigureSpec,
    ForestFigureSpec,
    LineFigureSpec,
    ScatterFigureSpec,
)

pytest.importorskip("matplotlib")


def _seed_workspace(tmp_path: Path) -> Path:
    (tmp_path / "paper" / "figures").mkdir(parents=True)
    return tmp_path


def _adapter() -> TypeAdapter[FigureSpec]:
    return TypeAdapter(FigureSpec)


def _assert_wrapper(tex_text: str, figure_id: str) -> None:
    assert "\\includegraphics" in tex_text
    assert f"figures/{figure_id}.pdf" in tex_text
    assert f"\\label{{fig:{figure_id}}}" in tex_text
    assert "\\caption{" in tex_text


def test_render_bar_writes_pdf_and_wrapper(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    spec = BarFigureSpec(
        id="fig_bar",
        caption="Bar demo",
        data=[
            {"arm": "Control", "y": 0.42, "se": 0.03},
            {"arm": "Treatment", "y": 0.31, "se": 0.03},
        ],
        x_field="arm",
        y_field="y",
        error_field="se",
    )

    result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)

    assert result.pdf_path.is_file()
    assert result.pdf_path.stat().st_size > 1000
    assert result.tex_path.is_file()
    _assert_wrapper(result.tex_path.read_text(encoding="utf-8"), "fig_bar")


def test_render_line_with_series(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    spec = LineFigureSpec(
        id="fig_line",
        caption="Line demo",
        data=[
            {"t": 0, "v": 1.0, "arm": "A"},
            {"t": 1, "v": 0.7, "arm": "A"},
            {"t": 2, "v": 0.5, "arm": "A"},
            {"t": 0, "v": 1.0, "arm": "B"},
            {"t": 1, "v": 0.9, "arm": "B"},
            {"t": 2, "v": 0.8, "arm": "B"},
        ],
        x_field="t",
        y_field="v",
        series_field="arm",
    )

    result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)

    assert result.pdf_path.is_file()
    assert result.pdf_path.stat().st_size > 1000


def test_render_scatter_basic(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    spec = ScatterFigureSpec(
        id="fig_sc",
        caption="Scatter demo",
        data=[
            {"x": 0.1, "y": 0.2},
            {"x": 0.3, "y": 0.5},
            {"x": 0.5, "y": 0.7},
        ],
        x_field="x",
        y_field="y",
    )

    result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)

    assert result.pdf_path.is_file()


def test_render_forest_writes_pdf(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    spec = ForestFigureSpec(
        id="fig_forest",
        caption="Forest demo",
        data=[
            {"study": "S1", "est": 0.1, "lo": -0.05, "hi": 0.25},
            {"study": "S2", "est": 0.2, "lo": 0.05, "hi": 0.35},
            {"study": "S3", "est": -0.05, "lo": -0.15, "hi": 0.05},
        ],
        label_field="study",
        estimate_field="est",
        ci_low_field="lo",
        ci_high_field="hi",
    )

    result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)

    assert result.pdf_path.is_file()
    assert result.tex_path.is_file()
    _assert_wrapper(result.tex_path.read_text(encoding="utf-8"), "fig_forest")


def test_render_loads_csv_data_relative_to_spec_dir(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    specs_dir = tmp_path / "paper" / "figure_specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "data.csv").write_text("arm,y\nControl,0.4\nTreat,0.6\n", encoding="utf-8")
    spec = BarFigureSpec(
        id="fig_csv",
        caption="CSV demo",
        data="data.csv",
        x_field="arm",
        y_field="y",
    )

    result = render_figure(spec=spec, workspace=tmp_path, spec_dir=specs_dir)

    assert result.pdf_path.is_file()


def test_render_bar_with_wrapped_ticks_and_right_legend(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    called: dict[str, Any] = {}

    def _fake_apply_axes_layout(ax: Any, **kwargs: Any) -> None:
        called["kwargs"] = kwargs

    original = getattr(renderer_mod, "apply_axes_layout", None)
    renderer_mod.apply_axes_layout = _fake_apply_axes_layout
    spec = BarFigureSpec(
        id="fig_wrapped",
        caption="Wrapped labels",
        data=[
            {"metric": "Counter Attitudinal Exposure", "group": "Control", "y": 0.4},
            {"metric": "Counter Attitudinal Exposure", "group": "Treatment", "y": 0.6},
        ],
        x_field="metric",
        y_field="y",
        group_field="group",
        tick_label_rotation=30,
        tick_label_wrap=12,
        legend_position="right",
    )

    try:
        result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)
    finally:
        if original is None:
            delattr(renderer_mod, "apply_axes_layout")
        else:
            renderer_mod.apply_axes_layout = original

    assert result.pdf_path.is_file()
    assert called["kwargs"]["tick_label_rotation"] == 30
    assert called["kwargs"]["tick_label_wrap"] == 12
    assert called["kwargs"]["legend_position"] == "right"


def test_render_line_tight_ylim_does_not_raise(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    called: dict[str, Any] = {}

    def _fake_apply_axes_layout(ax: Any, **kwargs: Any) -> None:
        called["kwargs"] = kwargs

    original = getattr(renderer_mod, "apply_axes_layout", None)
    renderer_mod.apply_axes_layout = _fake_apply_axes_layout
    spec = LineFigureSpec(
        id="fig_tight",
        caption="Tight line",
        data=[{"x": 1, "y": 10.0}, {"x": 2, "y": 10.2}, {"x": 3, "y": 10.3}],
        x_field="x",
        y_field="y",
        ylim_mode="tight",
    )

    try:
        result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)
    finally:
        if original is None:
            delattr(renderer_mod, "apply_axes_layout")
        else:
            renderer_mod.apply_axes_layout = original

    assert result.pdf_path.is_file()
    assert called["kwargs"]["ylim_mode"] == "tight"


def test_render_composite_figure_writes_pdf_and_wrapper(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    composite = _adapter().validate_python(
        {
            "kind": "composite",
            "id": "fig_composite",
            "caption": "Composite demo",
            "width": "double",
            "layout": {"rows": 2, "cols": 2, "height_ratios": [2.0, 1.0]},
            "panels": [
                {
                    "panel_id": "a",
                    "row": 0,
                    "col": 0,
                    "colspan": 2,
                    "figure": {
                        "kind": "line",
                        "id": "fig_nested_line",
                        "caption": "Nested",
                        "data": [{"x": 1, "y": 0.1}, {"x": 2, "y": 0.2}],
                        "x_field": "x",
                        "y_field": "y",
                    },
                },
                {
                    "panel_id": "b",
                    "row": 1,
                    "col": 0,
                    "figure": {
                        "kind": "bar",
                        "id": "fig_nested_bar",
                        "caption": "Nested",
                        "data": [{"arm": "A", "y": 1.0}],
                        "x_field": "arm",
                        "y_field": "y",
                    },
                },
            ],
        }
    )

    result = render_figure(spec=composite, workspace=tmp_path, spec_dir=tmp_path)

    assert result.pdf_path.is_file()
    assert result.tex_path.is_file()
