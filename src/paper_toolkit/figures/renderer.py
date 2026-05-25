"""Orchestrate spec validation → data load → matplotlib draw → file output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from paper_toolkit.figures.charts import (
    draw_bar,
    draw_forest,
    draw_line,
    draw_scatter,
)
from paper_toolkit.figures.data_loader import load_data
from paper_toolkit.figures.layout import apply_axes_layout
from paper_toolkit.figures.palettes import resolve_palette
from paper_toolkit.figures.style import apply_publication_style
from paper_toolkit.figures.tex_wrapper import wrap_figure_tex
from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.figure_spec import (
    BarFigureSpec,
    CompositeFigureSpec,
    FigureSpec,
    ForestFigureSpec,
    LineFigureSpec,
    ScatterFigureSpec,
)
from paper_toolkit.paths import WorkspacePaths

# Nature column widths (89 mm / 183 mm) in inches.
_SINGLE_IN = (3.5, 2.7)
_DOUBLE_IN = (7.2, 3.5)


@dataclass(frozen=True)
class RenderResult:
    figure_id: str
    pdf_path: Path
    tex_path: Path


def _figsize(width: str) -> tuple[float, float]:
    return _SINGLE_IN if width == "single" else _DOUBLE_IN


def _draw_spec_axes(*, ax: object, spec: FigureSpec, workspace: Path, spec_dir: Path) -> None:
    rows = load_data(data=spec.data, spec_dir=spec_dir, workspace=workspace)
    palette = resolve_palette(spec.palette)

    if isinstance(spec, BarFigureSpec):
        draw_bar(ax, spec, rows, palette)
    elif isinstance(spec, LineFigureSpec):
        draw_line(ax, spec, rows, palette)
    elif isinstance(spec, ScatterFigureSpec):
        draw_scatter(ax, spec, rows, palette)
    elif isinstance(spec, ForestFigureSpec):
        draw_forest(ax, spec, rows, palette)
    else:  # defensive — composite panels should be leaf figures for v1.
        raise TypeError(f"unsupported nested FigureSpec kind: {type(spec).__name__}")

    if spec.xlabel:
        ax.set_xlabel(spec.xlabel)
    if spec.ylabel:
        ax.set_ylabel(spec.ylabel)
    apply_axes_layout(
        ax,
        tick_label_rotation=spec.tick_label_rotation,
        tick_label_wrap=spec.tick_label_wrap,
        title=spec.title,
        title_wrap=spec.title_wrap,
        legend_position=spec.legend_position,
        ylim_mode=spec.ylim_mode,
        ylim_padding_ratio=spec.ylim_padding_ratio,
    )


def render_figure(*, spec: FigureSpec, workspace: Path, spec_dir: Path) -> RenderResult:
    """Render a FigureSpec to `<workspace>/paper/figures/<id>.{pdf,tex}`.

    `spec_dir` is the directory the spec JSON lived in; path-form `data`
    fields are resolved relative to it first.
    """
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    paths = WorkspacePaths(workspace=workspace)
    paths.figures_dir.mkdir(parents=True, exist_ok=True)

    apply_publication_style(font_size=spec.font_size)
    fig = plt.figure(figsize=_figsize(spec.width))
    try:
        if isinstance(spec, CompositeFigureSpec):
            grid = fig.add_gridspec(
                spec.layout.rows,
                spec.layout.cols,
                height_ratios=spec.layout.height_ratios,
                width_ratios=spec.layout.width_ratios,
            )
            for panel in spec.panels:
                ax = fig.add_subplot(
                    grid[
                        panel.row : panel.row + panel.rowspan,
                        panel.col : panel.col + panel.colspan,
                    ]
                )
                _draw_spec_axes(ax=ax, spec=panel.figure, workspace=workspace, spec_dir=spec_dir)
                ax.text(
                    -0.08,
                    1.02,
                    panel.panel_id,
                    transform=ax.transAxes,
                    fontweight="bold",
                    ha="left",
                    va="bottom",
                )
        else:
            ax = fig.subplots()
            _draw_spec_axes(ax=ax, spec=spec, workspace=workspace, spec_dir=spec_dir)
        fig.tight_layout()

        pdf_path = (paths.figures_dir / f"{spec.id}.pdf").resolve()
        fig.savefig(pdf_path)
    finally:
        plt.close(fig)

    wrapper = wrap_figure_tex(
        figure_id=spec.id,
        caption=spec.caption,
        label=spec.resolved_label(),
        width=spec.width,
    )
    tex_path = (paths.figures_dir / f"{spec.id}.tex").resolve()
    write_atomic_text(tex_path, wrapper)
    return RenderResult(figure_id=spec.id, pdf_path=pdf_path, tex_path=tex_path)
