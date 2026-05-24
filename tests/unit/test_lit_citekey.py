"""Tests for paper_toolkit.lit.citekey."""

from __future__ import annotations

from paper_toolkit.lit.citekey import make_cite_key


def test_make_cite_key_first_author_last_name_lowercase() -> None:
    key = make_cite_key(
        authors=["Ro'ee Levy", "Co-Author"],
        year=2021,
        title="Social Media News Consumption",
    )
    assert key.startswith("levy2021_")
    assert key == key.lower()


def test_make_cite_key_handles_lastname_first_comma() -> None:
    key = make_cite_key(authors=["Walker, Matthew"], year=2018, title="Sleep")
    assert key.startswith("walker2018_")


def test_make_cite_key_diacritics_stripped() -> None:
    key = make_cite_key(authors=["Müller, Hans"], year=2020, title="Why")
    assert key.startswith("muller2020_")


def test_make_cite_key_falls_back_when_metadata_missing() -> None:
    key = make_cite_key(authors=[], year=None, title="Untitled")
    assert key.startswith("anonnd_")


def test_make_cite_key_is_deterministic_for_same_input() -> None:
    a = make_cite_key(authors=["Doe, Jane"], year=2024, title="Repeatability")
    b = make_cite_key(authors=["Doe, Jane"], year=2024, title="Repeatability")
    assert a == b


def test_make_cite_key_differentiates_on_title() -> None:
    a = make_cite_key(authors=["Doe, Jane"], year=2024, title="Paper A")
    b = make_cite_key(authors=["Doe, Jane"], year=2024, title="Paper B")
    assert a != b
