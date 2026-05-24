"""Render a `TableSpec` to a booktabs LaTeX snippet."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from paper_toolkit.compose.latex_assembly import latex_escape
from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.table_spec import TableSpec
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.tables.latex_format import (
    format_data_row,
    format_header_row,
    format_note_block,
)


@dataclass(frozen=True)
class TableRenderResult:
    table_id: str
    tex_path: Path


def render_table_source(spec: TableSpec) -> str:
    """Return the LaTeX source for the table — no file I/O."""
    column_spec = spec.resolved_column_spec()
    header_row = format_header_row([col.header for col in spec.columns])
    data_rows = [format_data_row(row) for row in spec.rows]
    notes_block = format_note_block(spec.notes)

    lines: list[str] = [
        f"\\begin{{table}}[{spec.placement}]",
        "  \\centering",
        f"  \\caption{{{latex_escape(spec.caption)}}}",
        f"  \\label{{{spec.resolved_label()}}}",
        f"  \\begin{{tabular}}{{{column_spec}}}",
        "  \\toprule",
        f"  {header_row}",
        "  \\midrule",
    ]
    for row in data_rows:
        lines.append(f"  {row}")
    lines.append("  \\bottomrule")
    lines.append("  \\end{tabular}")
    if notes_block:
        lines.append(f"  {notes_block}")
    lines.append("\\end{table}")
    lines.append("")
    return "\n".join(lines)


def render_table(*, spec: TableSpec, workspace: Path) -> TableRenderResult:
    paths = WorkspacePaths(workspace=workspace)
    paths.tables_dir.mkdir(parents=True, exist_ok=True)
    source = render_table_source(spec)
    out_path = (paths.tables_dir / f"{spec.id}.tex").resolve()
    write_atomic_text(out_path, source)
    return TableRenderResult(table_id=spec.id, tex_path=out_path)
