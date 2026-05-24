"""Public surface for the `paper figure ...` command family."""

from __future__ import annotations

from paper_toolkit.figures.palettes import list_palette_names, resolve_palette
from paper_toolkit.figures.renderer import RenderResult, render_figure

__all__ = ["RenderResult", "list_palette_names", "render_figure", "resolve_palette"]
