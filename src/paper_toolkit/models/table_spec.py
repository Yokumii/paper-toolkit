"""Pydantic spec for `paper table` rendering."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Align = Literal["l", "c", "r"]


class TableColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header: str
    align: Align = "l"


class TableSpec(BaseModel):
    """JSON-authored spec for a booktabs-style LaTeX table."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[A-Za-z0-9_-]+$")
    caption: str
    label: str | None = Field(default=None, description="Defaults to f'tab:{id}' when None.")
    columns: list[TableColumn] = Field(..., min_length=1)
    rows: list[list[str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    column_spec: str | None = Field(
        default=None,
        description=(
            "Optional LaTeX column-spec override (e.g. 'l@{}rr'). When None we "
            "concatenate the per-column align values."
        ),
    )
    placement: str = "h"

    @model_validator(mode="after")
    def _rows_match_columns(self) -> TableSpec:
        width = len(self.columns)
        for idx, row in enumerate(self.rows):
            if len(row) != width:
                raise ValueError(
                    f"row {idx} has {len(row)} cells but the table declares {width} columns."
                )
        return self

    def resolved_label(self) -> str:
        return self.label or f"tab:{self.id}"

    def resolved_column_spec(self) -> str:
        return self.column_spec or "".join(col.align for col in self.columns)
