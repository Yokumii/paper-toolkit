"""Tests for the minimal BibTeX reader in paper_toolkit.refs.bib_reader."""

from __future__ import annotations

from paper_toolkit.refs.bib_reader import parse_bibtex


def test_parse_bibtex_extracts_basic_fields() -> None:
    text = """
@article{walker2018,
  title = {Sleep deprivation impairs cognition},
  author = {Walker, Matthew and Smith, Ada},
  journal = {Science},
  year = {2018},
  doi = {10.1126/science.aap9559}
}
"""
    entries = parse_bibtex(text)
    assert len(entries) == 1
    e = entries[0]
    assert e.cite_key == "walker2018"
    assert e.entry_type == "article"
    assert e.title == "Sleep deprivation impairs cognition"
    assert e.author == "Walker, Matthew and Smith, Ada"
    assert e.doi == "10.1126/science.aap9559"
    assert e.year == "2018"


def test_parse_bibtex_handles_quoted_values_and_nested_braces() -> None:
    text = """
@misc{nested,
  title = "A {Nested} Title",
  note = {with {balanced} braces}
}
"""
    entries = parse_bibtex(text)
    assert len(entries) == 1
    assert entries[0].title == "A {Nested} Title"
    assert entries[0].fields["note"] == "with {balanced} braces"


def test_parse_bibtex_returns_multiple_entries_in_order() -> None:
    text = """
@article{a, title = {A}}

@inproceedings{b, title = {B}, booktitle = {Proc}}

@misc{c, title = {C}}
"""
    entries = parse_bibtex(text)
    assert [e.cite_key for e in entries] == ["a", "b", "c"]
    assert entries[1].entry_type == "inproceedings"


def test_parse_bibtex_preserves_source_text() -> None:
    text = "@misc{x, title = {X}}"
    entries = parse_bibtex(text)
    assert entries[0].source_text == "@misc{x, title = {X}}"
