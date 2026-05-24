"""Write paper/refs.bib from citation nodes in the evidence graph."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.evidence import EvidenceGraph, GraphNode
from paper_toolkit.paths import WorkspacePaths


def _escape_bibtex(value: str) -> str:
    return value.replace("\\", "\\textbackslash{}").replace("{", "\\{").replace("}", "\\}")


def _citation_nodes(graph: EvidenceGraph) -> list[GraphNode]:
    return sorted(
        (node for node in graph.nodes if node.kind == "citation"),
        key=lambda n: n.cite_key or n.id,
    )


def _entry_lines(node: GraphNode) -> list[str]:
    """Render a single citation node as BibTeX lines."""
    entry_type = node.entry_type or "misc"
    cite_key = node.cite_key
    assert cite_key is not None  # citation invariant enforced by model
    lines = [f"@{entry_type}{{{cite_key},"]
    lines.append(f"  title = {{{_escape_bibtex(node.label)}}},")
    if node.authors:
        lines.append(f"  author = {{{_escape_bibtex(node.authors)}}},")
    if node.year:
        lines.append(f"  year = {{{_escape_bibtex(node.year)}}},")
    # Route `venue` to booktitle/journal based on entry_type; fall through to
    # the misc note field if entry_type doesn't take a venue.
    if node.venue:
        venue_escaped = _escape_bibtex(node.venue)
        if entry_type in ("inproceedings", "incollection"):
            lines.append(f"  booktitle = {{{venue_escaped}}},")
        elif entry_type in ("article",):
            lines.append(f"  journal = {{{venue_escaped}}},")
        elif entry_type in ("techreport",):
            lines.append(f"  institution = {{{venue_escaped}}},")
        elif entry_type in ("phdthesis", "mastersthesis"):
            lines.append(f"  school = {{{venue_escaped}}},")
        else:
            lines.append(f"  howpublished = {{{venue_escaped}}},")
    if node.doi:
        lines.append(f"  doi = {{{_escape_bibtex(node.doi)}}},")
    if node.url:
        lines.append(f"  url = {{{_escape_bibtex(node.url)}}},")
    # Note field: only emit when body is set OR when this is a bare @misc with
    # no other field (so the entry isn't reduced to just a title — preserves
    # the prior "Generated from..." fallback).
    has_metadata = any((node.authors, node.year, node.venue, node.doi, node.url))
    if node.body:
        lines.append(f"  note = {{{_escape_bibtex(node.body)}}},")
    elif entry_type == "misc" and not has_metadata:
        lines.append("  note = {Generated from paper-toolkit evidence graph.},")
    lines.append("}")
    return lines


def bibtex_for_citation_nodes(graph: EvidenceGraph) -> str:
    seen: set[str] = set()
    entries: list[str] = []
    for node in _citation_nodes(graph):
        if not node.cite_key or node.cite_key in seen:
            continue
        seen.add(node.cite_key)
        entries.append("\n".join(_entry_lines(node)))
    return "\n\n".join(entries) + ("\n" if entries else "")


def write_bib(*, workspace: Path, graph: EvidenceGraph) -> Path:
    paths = WorkspacePaths(workspace=workspace)
    paths.refs_bib.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(paths.refs_bib, bibtex_for_citation_nodes(graph))
    return paths.refs_bib
