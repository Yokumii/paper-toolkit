"""Spec-model tests for paper_toolkit.models.figure_spec."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from paper_toolkit.models.figure_spec import (
    BarFigureSpec,
    FigureSpec,
    ForestFigureSpec,
    LineFigureSpec,
    ScatterFigureSpec,
)


def _adapter() -> TypeAdapter[FigureSpec]:
    return TypeAdapter(FigureSpec)


def _row(**fields: object) -> dict[str, object]:
    return fields


def test_discriminator_routes_to_bar() -> None:
    payload = {
        "id": "fig1",
        "kind": "bar",
        "caption": "Demo bar",
        "data": [_row(arm="A", y=0.1), _row(arm="B", y=0.2)],
        "x_field": "arm",
        "y_field": "y",
    }
    spec = _adapter().validate_python(payload)
    assert isinstance(spec, BarFigureSpec)
    assert spec.resolved_label() == "fig:fig1"
    assert spec.palette == "nmi_pastel"


def test_discriminator_routes_to_line() -> None:
    payload = {
        "id": "fig-trend",
        "kind": "line",
        "caption": "Demo line",
        "data": "trend.csv",
        "x_field": "t",
        "y_field": "v",
    }
    spec = _adapter().validate_python(payload)
    assert isinstance(spec, LineFigureSpec)
    assert spec.resolved_label() == "fig:fig-trend"


def test_discriminator_routes_to_scatter() -> None:
    payload = {
        "id": "fig_sc",
        "kind": "scatter",
        "caption": "Demo scatter",
        "data": [],
        "x_field": "x",
        "y_field": "y",
    }
    spec = _adapter().validate_python(payload)
    assert isinstance(spec, ScatterFigureSpec)


def test_discriminator_routes_to_forest() -> None:
    payload = {
        "id": "fig_forest",
        "kind": "forest",
        "caption": "Demo forest",
        "data": [],
        "label_field": "study",
        "estimate_field": "est",
        "ci_low_field": "lo",
        "ci_high_field": "hi",
    }
    spec = _adapter().validate_python(payload)
    assert isinstance(spec, ForestFigureSpec)
    assert spec.ref == 0.0


def test_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        _adapter().validate_python(
            {
                "id": "fig1",
                "kind": "violin",
                "caption": "?",
                "data": [],
                "x_field": "x",
                "y_field": "y",
            }
        )


def test_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _adapter().validate_python(
            {
                "id": "fig1",
                "kind": "bar",
                "caption": "Demo",
                "data": [],
                "x_field": "arm",
                "y_field": "y",
                "stranger": "value",
            }
        )


def test_explicit_label_overrides_default() -> None:
    spec = _adapter().validate_python(
        {
            "id": "fig1",
            "kind": "bar",
            "caption": "Demo",
            "label": "fig:custom",
            "data": [],
            "x_field": "x",
            "y_field": "y",
        }
    )
    assert spec.resolved_label() == "fig:custom"


def test_id_rejects_invalid_characters() -> None:
    with pytest.raises(ValidationError):
        _adapter().validate_python(
            {
                "id": "fig 1!",
                "kind": "bar",
                "caption": "x",
                "data": [],
                "x_field": "x",
                "y_field": "y",
            }
        )
