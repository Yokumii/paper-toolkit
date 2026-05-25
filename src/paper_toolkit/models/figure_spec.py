"""Pydantic specs for the figure renderer.

The four chart kinds — bar, line, scatter, forest — share a base set of
fields plus their own kind-specific config. The discriminated union lets
the CLI dispatch on `kind` without manual `if/elif` plumbing.

Specs are written by the Claude Code skill layer (the toolkit never
authors a spec). Each spec is validated with `extra="forbid"` so typos
fail loud rather than silently producing the wrong chart.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

PaletteName = Literal["nmi_pastel", "nature_imaging", "nature_material", "nature_clinical"]
Width = Literal["single", "double"]
LegendPosition = Literal["inside", "right", "bottom", "none"]
YLimMode = Literal["auto", "zero", "tight"]
ScriptBackend = Literal["python", "r"]

# Row shape produced by the data loader: dict with str keys + scalar values.
RowValue = str | int | float | None
DataPathOrInline = list[dict[str, RowValue]] | str


class _FigureBase(BaseModel):
    """Fields shared by every chart kind."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[A-Za-z0-9_-]+$", description="Stable id used in filenames.")
    caption: str
    label: str | None = Field(
        default=None, description="LaTeX label. Defaults to f'fig:{id}' when None."
    )
    palette: PaletteName = "nmi_pastel"
    width: Width = "single"
    font_size: int = Field(default=10, ge=5, le=24)
    tick_label_rotation: int = Field(default=0, ge=0, le=90)
    tick_label_wrap: int | None = Field(default=None, ge=4, le=40)
    title_wrap: int | None = Field(default=None, ge=12, le=120)
    legend_position: LegendPosition = "inside"
    ylim_mode: YLimMode = "auto"
    ylim_padding_ratio: float = Field(default=0.08, ge=0.0, le=0.5)
    xlabel: str | None = None
    ylabel: str | None = None
    title: str | None = None
    data: DataPathOrInline = Field(
        ..., description="Inline list of row dicts OR a workspace/spec-relative path to .csv/.json."
    )

    def resolved_label(self) -> str:
        return self.label or f"fig:{self.id}"


class BarFigureSpec(_FigureBase):
    kind: Literal["bar"] = "bar"
    x_field: str
    y_field: str
    group_field: str | None = None
    error_field: str | None = None
    bar_width: float = Field(default=0.8, gt=0.0, le=1.0)
    annotate: bool = False


class LineFigureSpec(_FigureBase):
    kind: Literal["line"] = "line"
    x_field: str
    y_field: str
    series_field: str | None = None
    marker: str = "o"
    shadow_field: str | None = Field(
        default=None,
        description=(
            "Optional column whose value is plotted as a shaded band around the line "
            "(useful for SE / CI envelopes)."
        ),
    )


class ScatterFigureSpec(_FigureBase):
    kind: Literal["scatter"] = "scatter"
    x_field: str
    y_field: str
    series_field: str | None = None
    size_field: str | None = None


class ForestFigureSpec(_FigureBase):
    kind: Literal["forest"] = "forest"
    label_field: str
    estimate_field: str
    ci_low_field: str
    ci_high_field: str
    ref: float = Field(
        default=0.0, description="Reference line (typically 0 for effects, 1 for ORs)."
    )


class PanelFigureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    panel_id: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    figure: FigureSpec


class CompositeLayoutSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: int = Field(..., ge=1, le=6)
    cols: int = Field(..., ge=1, le=6)
    height_ratios: list[float] | None = None
    width_ratios: list[float] | None = None


class CompositeFigureSpec(_FigureBase):
    kind: Literal["composite"] = "composite"
    layout: CompositeLayoutSpec
    panels: list[PanelFigureSpec]
    hero_panel: str | None = None
    data: DataPathOrInline = Field(default_factory=list)


class ScriptFigureSpec(_FigureBase):
    kind: Literal["script"] = "script"
    backend: ScriptBackend
    entrypoint: str
    data: DataPathOrInline = Field(default_factory=list)


FigureSpec = Annotated[
    BarFigureSpec
    | LineFigureSpec
    | ScatterFigureSpec
    | ForestFigureSpec
    | CompositeFigureSpec
    | ScriptFigureSpec,
    Field(discriminator="kind"),
]


PanelFigureSpec.model_rebuild()
CompositeFigureSpec.model_rebuild()
