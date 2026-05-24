"""Tests for paper_toolkit.models.table_spec."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from paper_toolkit.models.table_spec import TableColumn, TableSpec


def test_table_spec_defaults_label_to_id() -> None:
    spec = TableSpec(
        id="tab1",
        caption="Demo",
        columns=[TableColumn(header="A"), TableColumn(header="B", align="r")],
        rows=[["a1", "b1"], ["a2", "b2"]],
    )
    assert spec.resolved_label() == "tab:tab1"
    # Auto-derived column spec concatenates per-column align values.
    assert spec.resolved_column_spec() == "lr"


def test_table_spec_column_spec_override_wins() -> None:
    spec = TableSpec(
        id="tab2",
        caption="Demo",
        columns=[TableColumn(header="A"), TableColumn(header="B")],
        rows=[],
        column_spec="l@{}r",
    )
    assert spec.resolved_column_spec() == "l@{}r"


def test_table_spec_row_count_must_match_columns() -> None:
    with pytest.raises(ValidationError):
        TableSpec(
            id="tab3",
            caption="Demo",
            columns=[TableColumn(header="A"), TableColumn(header="B")],
            rows=[["only one cell"]],
        )


def test_table_spec_requires_at_least_one_column() -> None:
    with pytest.raises(ValidationError):
        TableSpec(id="tab4", caption="Demo", columns=[], rows=[])


def test_table_spec_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TableSpec.model_validate(
            {
                "id": "tab5",
                "caption": "Demo",
                "columns": [{"header": "A"}],
                "rows": [],
                "stranger": True,
            }
        )
