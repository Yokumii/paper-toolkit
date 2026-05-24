"""Tests for paper_toolkit.lit.bibtex_emit."""

from __future__ import annotations

from paper_toolkit.lit.bibtex_emit import entries_to_bibtex, entry_to_bibtex
from paper_toolkit.lit.models import LiteratureEntry


def _article() -> LiteratureEntry:
    return LiteratureEntry(
        source="crossref",
        source_id="10.1126/science.aap9559",
        title="Sleep deprivation impairs cognition",
        authors=["Walker, Matthew", "Smith, Ada"],
        year=2018,
        venue="Science",
        doi="10.1126/science.aap9559",
        url="https://science.example.org/aap9559",
        abstract="Long\n   abstract with    whitespace.",
        entry_type="article",
        cite_key="walker2018_a53f",
    )


def test_article_routes_venue_to_journal() -> None:
    text = entry_to_bibtex(_article())
    assert text.startswith("@article{walker2018_a53f,")
    assert "journal = {Science}," in text
    assert "doi = {10.1126/science.aap9559}," in text
    # Abstract whitespace is normalized to single spaces.
    assert "Long abstract with whitespace." in text


def test_inproceedings_routes_venue_to_booktitle() -> None:
    entry = _article().model_copy(update={"entry_type": "inproceedings"})
    text = entry_to_bibtex(entry)
    assert text.startswith("@inproceedings{")
    assert "booktitle = {Science}," in text


def test_techreport_routes_venue_to_institution() -> None:
    entry = _article().model_copy(update={"entry_type": "techreport"})
    text = entry_to_bibtex(entry)
    assert "institution = {Science}," in text


def test_phdthesis_routes_venue_to_school() -> None:
    entry = _article().model_copy(update={"entry_type": "phdthesis"})
    text = entry_to_bibtex(entry)
    assert "school = {Science}," in text


def test_misc_routes_venue_to_howpublished() -> None:
    entry = _article().model_copy(update={"entry_type": "misc"})
    text = entry_to_bibtex(entry)
    assert "howpublished = {Science}," in text


def test_entries_to_bibtex_joins_with_blank_line() -> None:
    first = _article()
    second = first.model_copy(update={"cite_key": "walker2018_b001", "title": "Other"})
    text = entries_to_bibtex([first, second])
    # Two entries separated by exactly one blank line.
    assert text.count("@article{") == 2
    assert "\n\n@article{walker2018_b001," in text


def test_authors_joined_with_and() -> None:
    text = entry_to_bibtex(_article())
    assert "author = {Walker, Matthew and Smith, Ada}," in text
