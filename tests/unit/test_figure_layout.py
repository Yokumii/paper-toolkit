"""Unit tests for figure layout helpers."""

from __future__ import annotations

import pytest

plt = pytest.importorskip("matplotlib.pyplot")

from paper_toolkit.figures.layout import apply_axes_layout


def test_apply_axes_layout_rotates_and_wraps_tick_labels() -> None:
    fig, ax = plt.subplots()
    try:
        ax.bar([0, 1], [1.0, 2.0])
        ax.set_xticks([0, 1])
        ax.set_xticklabels(
            ["Counter Attitudinal Exposure", "Pro Attitudinal Exposure"]
        )

        apply_axes_layout(
            ax,
            tick_label_rotation=30,
            tick_label_wrap=12,
            title=None,
            title_wrap=None,
            legend_position="inside",
            ylim_mode="auto",
            ylim_padding_ratio=0.08,
        )

        labels = [tick.get_text() for tick in ax.get_xticklabels()]
        assert any("\n" in label for label in labels)
        assert ax.get_xticklabels()[0].get_rotation() == 30
    finally:
        plt.close(fig)


def test_apply_axes_layout_tight_ylim_adds_padding() -> None:
    fig, ax = plt.subplots()
    try:
        ax.plot([1, 2, 3], [10.0, 10.2, 10.3])

        apply_axes_layout(
            ax,
            tick_label_rotation=0,
            tick_label_wrap=None,
            title=None,
            title_wrap=None,
            legend_position="inside",
            ylim_mode="tight",
            ylim_padding_ratio=0.1,
        )

        lo, hi = ax.get_ylim()
        assert lo < 10.0
        assert hi > 10.3
    finally:
        plt.close(fig)
