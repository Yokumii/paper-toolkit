"""Layout helpers for publication-style axes."""

from __future__ import annotations

from textwrap import fill
from typing import Any


def _wrap_text(text: str, width: int | None) -> str:
    if width is None or len(text) <= width:
        return text
    return fill(text, width=width)


def apply_axes_layout(
    ax: Any,
    *,
    tick_label_rotation: int,
    tick_label_wrap: int | None,
    title: str | None,
    title_wrap: int | None,
    legend_position: str,
    ylim_mode: str,
    ylim_padding_ratio: float,
) -> None:
    """Apply simple publication layout rules to an axes."""

    if title:
        ax.set_title(_wrap_text(title, title_wrap))

    labels = ax.get_xticklabels()
    wrapped_labels = []
    for tick in labels:
        wrapped = _wrap_text(tick.get_text(), tick_label_wrap)
        tick.set_rotation(tick_label_rotation)
        tick.set_ha("right" if tick_label_rotation else "center")
        wrapped_labels.append(wrapped)
    xticks = ax.get_xticks()
    if len(xticks) == len(wrapped_labels) and wrapped_labels:
        ax.set_xticks(
            xticks,
            labels=wrapped_labels,
            rotation=tick_label_rotation,
            ha="right" if tick_label_rotation else "center",
        )

    legend = ax.get_legend()
    if legend is not None:
        if legend_position == "right":
            ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
        elif legend_position == "bottom":
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
        elif legend_position == "none":
            legend.remove()

    if ylim_mode == "zero":
        _, hi = ax.get_ylim()
        ax.set_ylim(bottom=0.0, top=hi)
    elif ylim_mode == "tight":
        lo, hi = ax.dataLim.intervaly
        span = hi - lo
        pad = max(span * ylim_padding_ratio, 1e-9)
        ax.set_ylim(lo - pad, hi + pad)
