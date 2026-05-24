"""Render a `LiteratureEntry` as a BibTeX entry block.

Field routing mirrors `compose/bib_writer.py` so a merged refs.bib stays
consistent regardless of which step inserted the entry: `venue` goes to
`journal` for articles, `booktitle` for inproceedings/incollection,
`institution` for tech reports, `school` for theses, and `howpublished`
for the misc fallback.
"""

from __future__ import annotations

from paper_toolkit.lit.models import LiteratureEntry


def _escape_bibtex(value: str) -> str:
    return value.replace("\\", "\\textbackslash{}").replace("{", "\\{").replace("}", "\\}")


def entry_to_bibtex(entry: LiteratureEntry) -> str:
    """Render one entry as a BibTeX block (no trailing blank line)."""
    lines: list[str] = [f"@{entry.entry_type}{{{entry.cite_key},"]
    lines.append(f"  title = {{{_escape_bibtex(entry.title)}}},")
    if entry.authors:
        joined = " and ".join(_escape_bibtex(a) for a in entry.authors)
        lines.append(f"  author = {{{joined}}},")
    if entry.year is not None:
        lines.append(f"  year = {{{entry.year}}},")
    if entry.venue:
        venue = _escape_bibtex(entry.venue)
        if entry.entry_type in ("inproceedings", "incollection"):
            lines.append(f"  booktitle = {{{venue}}},")
        elif entry.entry_type in ("article",):
            lines.append(f"  journal = {{{venue}}},")
        elif entry.entry_type == "techreport":
            lines.append(f"  institution = {{{venue}}},")
        elif entry.entry_type in ("phdthesis", "mastersthesis"):
            lines.append(f"  school = {{{venue}}},")
        else:
            lines.append(f"  howpublished = {{{venue}}},")
    if entry.doi:
        lines.append(f"  doi = {{{_escape_bibtex(entry.doi)}}},")
    if entry.url:
        lines.append(f"  url = {{{_escape_bibtex(entry.url)}}},")
    if entry.abstract:
        # Abstracts can be very long; squeeze whitespace so the block stays readable.
        squeezed = " ".join(entry.abstract.split())
        lines.append(f"  abstract = {{{_escape_bibtex(squeezed)}}},")
    lines.append("}")
    return "\n".join(lines)


def entries_to_bibtex(entries: list[LiteratureEntry]) -> str:
    """Render a list of entries as a contiguous BibTeX document."""
    if not entries:
        return ""
    blocks = [entry_to_bibtex(e) for e in entries]
    return "\n\n".join(blocks) + "\n"
