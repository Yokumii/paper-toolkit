"""LaTeX-string helpers for the table renderer."""

from __future__ import annotations

from paper_toolkit.compose.latex_assembly import latex_escape


def escape_cell(value: str) -> str:
    """Escape a string for use inside a `tabular` cell."""
    return latex_escape(value)


def format_header_row(headers: list[str]) -> str:
    return " & ".join(escape_cell(h) for h in headers) + " \\\\"


def format_data_row(cells: list[str]) -> str:
    return " & ".join(escape_cell(c) for c in cells) + " \\\\"


def format_note_block(notes: list[str]) -> str:
    if not notes:
        return ""
    joined = " ".join(escape_cell(note) for note in notes)
    return f"\\par\\footnotesize {joined}"
