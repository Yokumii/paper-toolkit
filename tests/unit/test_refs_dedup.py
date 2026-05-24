"""Tests for paper_toolkit.refs.dedup."""

from __future__ import annotations

from paper_toolkit.refs.bib_reader import parse_bibtex
from paper_toolkit.refs.dedup import (
    apply_dedup,
    find_duplicates,
    first_author_surname,
    jaccard,
    normalize_doi,
    normalize_title,
    title_tokens,
)


def test_normalize_doi_strips_https_prefix_and_lowercases() -> None:
    assert normalize_doi("https://doi.org/10.1126/Science.AAP9559") == "10.1126/science.aap9559"
    assert normalize_doi("HTTP://dx.doi.org/10.1/X") == "10.1/x"
    assert normalize_doi("  10.1/X  ") == "10.1/x"
    assert normalize_doi(None) is None
    assert normalize_doi("") is None


def test_normalize_title_removes_punctuation_and_collapses_whitespace() -> None:
    assert normalize_title("Foo: Bar (Baz)!") == "foo bar baz"


def test_title_tokens_drops_stopwords() -> None:
    tokens = title_tokens("Effects of the Cross-Cutting News on Polarization")
    # `of`, `the`, `on` are stopwords; the hyphenated "cross-cutting" loses its
    # hyphen via punctuation normalization, leaving two distinct tokens.
    assert "the" not in tokens
    assert "of" not in tokens
    assert {"effects", "cross", "cutting", "news", "polarization"}.issubset(tokens)


def test_first_author_surname_handles_both_formats() -> None:
    assert first_author_surname("Walker, Matthew and Smith, Ada") == "walker"
    assert first_author_surname("Matthew Walker and Ada Smith") == "walker"
    assert first_author_surname("") == ""


def test_jaccard_known_values() -> None:
    a = {"a", "b", "c"}
    b = {"b", "c", "d"}
    assert jaccard(a, b) == 0.5
    assert jaccard(a, a) == 1.0
    assert jaccard(set(), set()) == 0.0


def test_find_duplicates_detects_doi_match() -> None:
    text = """
@article{a, title={Old}, doi={10.1/Y}, author={Doe, J}, journal={J}}

@article{b, title={New}, doi={HTTPS://doi.org/10.1/Y}, author={Doe, J}, journal={J}, year={2024}}
"""
    entries = parse_bibtex(text)
    groups = find_duplicates(entries)
    assert len(groups) == 1
    g = groups[0]
    assert g.reason == "doi"
    # `b` has more filled fields (year), so it becomes the keeper.
    assert g.keeper_cite_key == "b"
    assert g.absorbed_cite_keys == ["a"]


def test_find_duplicates_title_author_jaccard_fallback() -> None:
    text = """
@misc{a, title={Cross-cutting news exposure and polarization}, author={Levy, Ro'ee}}

@misc{b, title={Cross cutting news exposure and polarization}, author={Levy, R}}
"""
    entries = parse_bibtex(text)
    groups = find_duplicates(entries)
    assert len(groups) == 1
    g = groups[0]
    assert g.reason == "title-author"
    assert {g.keeper_cite_key, *g.absorbed_cite_keys} == {"a", "b"}


def test_find_duplicates_ignores_different_authors_even_with_same_title() -> None:
    text = """
@misc{a, title={Cross cutting news}, author={Levy, R}}

@misc{b, title={Cross cutting news}, author={Doe, J}}
"""
    entries = parse_bibtex(text)
    assert find_duplicates(entries) == []


def test_apply_dedup_keeps_keeper_and_drops_absorbed() -> None:
    text = """
@article{a, title={Old}, doi={10.1/Y}}

@article{b, title={New}, doi={10.1/Y}, year={2024}}

@misc{c, title={Independent}}
"""
    entries = parse_bibtex(text)
    groups = find_duplicates(entries)
    deduped = apply_dedup(entries, groups)
    keys = [e.cite_key for e in deduped]
    assert "b" in keys  # keeper
    assert "a" not in keys
    assert "c" in keys  # untouched
