"""Tests for the table renderer."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.models.table_spec import TableColumn, TableSpec
from paper_toolkit.tables.renderer import render_table, render_table_source


def _spec() -> TableSpec:
    return TableSpec(
        id="tab1",
        caption="Treatment effects",
        columns=[
            TableColumn(header="Arm", align="l"),
            TableColumn(header="N", align="r"),
            TableColumn(header="Endline gap (SE)", align="r"),
        ],
        rows=[
            ["Control", "1,012", "0.42 (0.03)"],
            ["Counter-attitudinal", "1,008", "0.31 (0.03)"],
        ],
        notes=["SE in parentheses.", "$n=2020$ total."],
    )


def test_render_table_source_contains_booktabs_landmarks() -> None:
    text = render_table_source(_spec())
    for marker in ("\\toprule", "\\midrule", "\\bottomrule"):
        assert marker in text
    assert "\\caption{Treatment effects}" in text
    assert "\\label{tab:tab1}" in text
    assert "\\begin{tabular}{lrr}" in text


def test_render_table_source_includes_notes_block() -> None:
    text = render_table_source(_spec())
    assert "\\footnotesize" in text
    assert "SE in parentheses." in text
    # The dollar sign in a note must be LaTeX-escaped.
    assert "\\$n=2020\\$" in text


def test_render_table_source_omits_notes_block_when_empty() -> None:
    spec = TableSpec(
        id="tab_nonote",
        caption="No notes",
        columns=[TableColumn(header="A")],
        rows=[["x"]],
    )
    text = render_table_source(spec)
    assert "\\footnotesize" not in text


def test_render_table_writes_file_under_tables_dir(tmp_path: Path) -> None:
    result = render_table(spec=_spec(), workspace=tmp_path)
    assert result.tex_path == (tmp_path / "paper" / "tables" / "tab1.tex").resolve()
    content = result.tex_path.read_text(encoding="utf-8")
    assert "\\toprule" in content


def test_render_table_column_spec_override() -> None:
    spec = TableSpec(
        id="tab_x",
        caption="Custom spec",
        columns=[TableColumn(header="A"), TableColumn(header="B")],
        rows=[],
        column_spec="l@{}r",
    )
    text = render_table_source(spec)
    assert "\\begin{tabular}{l@{}r}" in text


def test_render_table_escapes_cells() -> None:
    spec = TableSpec(
        id="tab_esc",
        caption="Demo",
        columns=[TableColumn(header="X & Y")],
        rows=[["a_b"], ["100%"]],
    )
    text = render_table_source(spec)
    assert "X \\& Y" in text
    assert "a\\_b" in text
    assert "100\\%" in text
