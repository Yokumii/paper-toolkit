"""Tests for figure palette registry."""

from __future__ import annotations

import pytest

from paper_toolkit.figures.palettes import PALETTES, list_palette_names, resolve_palette


def test_list_palette_names_is_sorted_and_complete() -> None:
    names = list_palette_names()
    assert names == sorted(PALETTES.keys())
    assert set(names) == {"nmi_pastel", "nature_imaging", "nature_material", "nature_clinical"}


def test_resolve_palette_returns_expected_first_color() -> None:
    assert resolve_palette("nmi_pastel")[0] == "#484878"
    assert resolve_palette("nature_imaging")[0] == "#22D7E6"


def test_resolve_palette_returns_a_copy() -> None:
    first = resolve_palette("nmi_pastel")
    first[0] = "#000000"
    second = resolve_palette("nmi_pastel")
    assert second[0] == "#484878"


def test_resolve_palette_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError):
        resolve_palette("not_a_palette")
