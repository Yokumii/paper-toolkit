from pathlib import Path

import pytest

from paper_toolkit.compose.bib_writer import bibtex_for_citation_nodes, write_bib
from paper_toolkit.models.evidence import EvidenceGraph, GraphNode


def test_bibtex_for_citation_nodes_deduplicates_by_cite_key() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="ref1", kind="citation", label="Smith Study", cite_key="smith2020"),
            GraphNode(
                id="ref2",
                kind="citation",
                label="Smith Study Duplicate",
                cite_key="smith2020",
            ),
            GraphNode(id="ref3", kind="citation", label="Doe Study", cite_key="doe2021"),
        ],
    )

    text = bibtex_for_citation_nodes(graph)

    assert text.count("@misc{smith2020") == 1
    assert "@misc{doe2021" in text
    assert "title = {Smith Study}" in text


def test_write_bib_writes_refs_file(tmp_path: Path) -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[GraphNode(id="ref1", kind="citation", label="Smith Study", cite_key="smith2020")],
    )

    out = write_bib(workspace=tmp_path, graph=graph)

    assert out == (tmp_path / "paper" / "refs.bib").resolve()
    assert "@misc{smith2020" in out.read_text(encoding="utf-8")


def test_bibtex_renders_article_entry_with_journal_and_doi() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(
                id="ref1",
                kind="citation",
                label="A formal study of polarization dynamics",
                cite_key="levy2021",
                entry_type="article",
                authors="Levy, Ro'ee and Razin, Ronny",
                year="2021",
                venue="Nature Reviews Physics",
                doi="10.1038/s42254-021-00345-w",
                url="https://www.nature.com/articles/s42254-021-00345-w",
            )
        ],
    )

    text = bibtex_for_citation_nodes(graph)

    assert "@article{levy2021," in text
    assert "title = {A formal study of polarization dynamics}" in text
    assert "author = {Levy, Ro'ee and Razin, Ronny}" in text
    assert "year = {2021}" in text
    assert "journal = {Nature Reviews Physics}" in text
    assert "doi = {10.1038/s42254-021-00345-w}" in text
    # The placeholder "Generated from..." note must NOT appear when real fields are present.
    assert "Generated from paper-toolkit" not in text


def test_bibtex_renders_inproceedings_with_booktitle() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(
                id="ref1",
                kind="citation",
                label="Echo Chambers Online",
                cite_key="bakshy2015",
                entry_type="inproceedings",
                authors="Bakshy, Eytan and Messing, Solomon and Adamic, Lada",
                year="2015",
                venue="Proceedings of WWW",
            )
        ],
    )

    text = bibtex_for_citation_nodes(graph)
    assert "@inproceedings{bakshy2015," in text
    assert "booktitle = {Proceedings of WWW}" in text


def test_citation_node_rejects_placeholder_cite_key() -> None:
    with pytest.raises(ValueError, match="placeholder"):
        GraphNode(id="ref1", kind="citation", label="Smith", cite_key="ref_id")


def test_citation_node_rejects_invalid_cite_key() -> None:
    with pytest.raises(ValueError, match="must match"):
        GraphNode(id="ref1", kind="citation", label="Smith", cite_key="42invalid")


def test_non_citation_node_rejects_citation_fields() -> None:
    with pytest.raises(ValueError, match="only valid for citation nodes"):
        GraphNode(id="c1", kind="claim", label="A claim", year="2024")
