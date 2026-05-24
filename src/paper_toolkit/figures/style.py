"""Matplotlib rcParams preset.

`apply_publication_style` enforces editable SVG text
(`svg.fonttype = "none"`), TrueType-embedded PDF text
(`pdf.fonttype = 42`), Arial-family fallback, and slim axes. Matplotlib
imports are lazy so CLI startup stays cheap.
"""

from __future__ import annotations


def apply_publication_style(*, font_size: int = 10, axes_linewidth: float = 0.8) -> None:
    """Set rcParams so figures look like a journal submission.

    Call once before creating any figures. The defaults target single-column
    panels (~89 mm). Bump `font_size` and `axes_linewidth` for poster
    or full-page panels.
    """
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["font.size"] = font_size
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.linewidth"] = axes_linewidth
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["figure.dpi"] = 300
