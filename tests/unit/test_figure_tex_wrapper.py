"""Tests for paper_toolkit.figures.tex_wrapper."""

from __future__ import annotations

import pytest

from paper_toolkit.figures.tex_wrapper import wrap_figure_tex


def test_single_width_uses_columnwidth() -> None:
    text = wrap_figure_tex(figure_id="fig1", caption="Demo", label="fig:fig1", width="single")
    assert "\\columnwidth" in text
    assert "\\textwidth" not in text
    assert "\\includegraphics[width=\\columnwidth]{figures/fig1.pdf}" in text
    assert "\\caption{Demo}" in text
    assert "\\label{fig:fig1}" in text


def test_double_width_uses_textwidth() -> None:
    text = wrap_figure_tex(figure_id="fig2", caption="Demo", label="fig:fig2", width="double")
    assert "\\textwidth" in text
    assert "\\columnwidth" not in text


def test_caption_escapes_special_chars() -> None:
    text = wrap_figure_tex(
        figure_id="fig3",
        caption="A & B 100% C_d",
        label="fig:fig3",
        width="single",
    )
    assert "\\&" in text
    assert "\\%" in text
    assert "\\_" in text
    # No unescaped ampersand (every & must be preceded by a backslash).
    for idx, ch in enumerate(text):
        if ch == "&":
            assert text[idx - 1] == "\\", f"unescaped & at offset {idx}"


def test_unsupported_width_raises() -> None:
    with pytest.raises(ValueError):
        wrap_figure_tex(figure_id="x", caption="y", label="fig:x", width="huge")
