"""Tests for index round-trip and merge dedup."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.lit.index import (
    entries_to_jsonl,
    parse_jsonl,
    read_index,
    slugify_query,
    write_index,
)
from paper_toolkit.lit.merge import existing_cite_keys, merge_into_bib
from paper_toolkit.lit.models import LiteratureEntry


def _entry(cite_key: str, *, title: str = "Demo") -> LiteratureEntry:
    return LiteratureEntry(
        source="crossref",
        source_id=cite_key,
        title=title,
        authors=["Doe, Jane"],
        year=2024,
        venue="J",
        doi=f"10.0000/{cite_key}",
        entry_type="article",
        cite_key=cite_key,
    )


def test_slugify_query_handles_punctuation_and_diacritics() -> None:
    assert slugify_query("Café & cross-cutting exposure!") == "cafe-cross-cutting-exposure"


def test_slugify_query_falls_back_when_only_punctuation() -> None:
    assert slugify_query("?!??") == "query"


def test_slugify_query_truncates_to_max_length() -> None:
    long = "a" * 100
    assert len(slugify_query(long, max_length=12)) == 12


def test_entries_to_jsonl_roundtrip() -> None:
    items = [_entry("doe2024_a001", title="Alpha"), _entry("doe2024_b002", title="Beta")]
    jsonl = entries_to_jsonl(items)
    parsed = parse_jsonl(jsonl)
    assert [e.cite_key for e in parsed] == [e.cite_key for e in items]
    assert [e.title for e in parsed] == ["Alpha", "Beta"]


def test_write_and_read_index(tmp_path: Path) -> None:
    workspace = tmp_path
    items = [_entry("doe2024_a001"), _entry("doe2024_b002")]
    out_path = write_index(workspace=workspace, slug="demo", entries=items)
    assert out_path == (workspace / "paper" / "lit" / "demo.jsonl").resolve()
    parsed = read_index(out_path)
    assert [e.cite_key for e in parsed] == ["doe2024_a001", "doe2024_b002"]


def test_existing_cite_keys_finds_all_entry_types() -> None:
    text = "@article{walker2018, ...}\n@misc{anon_x, ...}"
    assert existing_cite_keys(text) == {"walker2018", "anon_x"}


def test_merge_into_bib_creates_file_when_missing(tmp_path: Path) -> None:
    items = [_entry("doe2024_a001"), _entry("doe2024_b002")]
    report = merge_into_bib(workspace=tmp_path, entries=items)
    assert report.added == ["doe2024_a001", "doe2024_b002"]
    assert not report.skipped
    text = report.bib_path.read_text(encoding="utf-8")
    assert "@article{doe2024_a001," in text
    assert "@article{doe2024_b002," in text


def test_merge_into_bib_skips_existing_keys(tmp_path: Path) -> None:
    bib = tmp_path / "paper" / "refs.bib"
    bib.parent.mkdir(parents=True)
    bib.write_text("@article{doe2024_a001,\n  title = {Old}\n}\n", encoding="utf-8")

    report = merge_into_bib(
        workspace=tmp_path,
        entries=[_entry("doe2024_a001"), _entry("doe2024_b002")],
    )
    assert report.added == ["doe2024_b002"]
    assert report.skipped == ["doe2024_a001"]
    text = report.bib_path.read_text(encoding="utf-8")
    assert text.count("@article{doe2024_a001,") == 1
    assert "title = {Old}" in text  # original entry preserved verbatim
    assert "@article{doe2024_b002," in text
