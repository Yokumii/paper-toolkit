"""Chart drawers — one per FigureSpec kind.

Each drawer receives:
- `ax`: a matplotlib Axes
- `spec`: the kind-specific Pydantic spec
- `rows`: the loaded data (list of dicts)
- `palette`: an ordered list of hex colors

Drawers mutate `ax` in place; the renderer owns the figure-level setup
(size, labels, title, savefig). Drawers never call `plt.show()` or
`plt.savefig`.
"""

from __future__ import annotations

from itertools import cycle
from typing import Any

from paper_toolkit.models.figure_spec import (
    BarFigureSpec,
    ForestFigureSpec,
    LineFigureSpec,
    ScatterFigureSpec,
)


class ChartDataError(ValueError):
    """Raised when the rows are missing required fields or have inconsistent types."""


def _require_field(row: dict[str, Any], field: str, row_index: int) -> Any:
    if field not in row:
        raise ChartDataError(f"row {row_index} is missing required field {field!r}.")
    return row[field]


def _as_float(value: Any, *, field: str, row_index: int) -> float:
    if value is None or value == "":
        raise ChartDataError(f"row {row_index} field {field!r} is empty.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ChartDataError(f"row {row_index} field {field!r}={value!r} is not numeric.") from exc


def _group_by(rows: list[dict[str, Any]], field: str) -> dict[Any, list[dict[str, Any]]]:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        key = row.get(field)
        groups.setdefault(key, []).append(row)
    return groups


def draw_bar(ax: Any, spec: BarFigureSpec, rows: list[dict[str, Any]], palette: list[str]) -> None:
    import numpy as np

    if spec.group_field is None:
        categories: list[str] = []
        values: list[float] = []
        errors: list[float] = []
        for idx, row in enumerate(rows):
            categories.append(str(_require_field(row, spec.x_field, idx)))
            values.append(
                _as_float(_require_field(row, spec.y_field, idx), field=spec.y_field, row_index=idx)
            )
            if spec.error_field is not None:
                errors.append(
                    _as_float(
                        _require_field(row, spec.error_field, idx),
                        field=spec.error_field,
                        row_index=idx,
                    )
                )
        positions = np.arange(len(categories))
        ax.bar(
            positions,
            values,
            width=spec.bar_width,
            color=palette[0],
            yerr=errors if errors else None,
            capsize=3 if errors else 0,
        )
        ax.set_xticks(positions)
        ax.set_xticklabels(categories)
        if spec.annotate:
            for x, y in zip(positions, values, strict=True):
                ax.text(x, y, f"{y:.2f}", ha="center", va="bottom")
        return

    # Grouped bars: group_field defines color buckets sharing each x value.
    x_values: list[str] = []
    for row in rows:
        v = str(row.get(spec.x_field, ""))
        if v not in x_values:
            x_values.append(v)
    groups = _group_by(rows, spec.group_field)
    n_groups = len(groups)
    if n_groups == 0:
        raise ChartDataError("no rows to draw a grouped bar chart from.")
    group_width = spec.bar_width / n_groups
    color_cycle = cycle(palette)
    for offset, (group_key, group_rows) in enumerate(groups.items()):
        color = next(color_cycle)
        bar_positions: list[float] = []
        values = []
        errors = []
        for x_idx, x_val in enumerate(x_values):
            match = next((r for r in group_rows if str(r.get(spec.x_field, "")) == x_val), None)
            if match is None:
                continue
            bar_positions.append(x_idx + (offset - (n_groups - 1) / 2) * group_width)
            values.append(
                _as_float(
                    _require_field(match, spec.y_field, x_idx), field=spec.y_field, row_index=x_idx
                )
            )
            if spec.error_field is not None:
                errors.append(
                    _as_float(
                        _require_field(match, spec.error_field, x_idx),
                        field=spec.error_field,
                        row_index=x_idx,
                    )
                )
        ax.bar(
            bar_positions,
            values,
            width=group_width,
            color=color,
            label=str(group_key),
            yerr=errors if errors else None,
            capsize=2 if errors else 0,
        )
    ax.set_xticks(range(len(x_values)))
    ax.set_xticklabels(x_values)
    ax.legend()


def draw_line(
    ax: Any, spec: LineFigureSpec, rows: list[dict[str, Any]], palette: list[str]
) -> None:
    if spec.series_field is None:
        xs = [
            _as_float(_require_field(row, spec.x_field, idx), field=spec.x_field, row_index=idx)
            for idx, row in enumerate(rows)
        ]
        ys = [
            _as_float(_require_field(row, spec.y_field, idx), field=spec.y_field, row_index=idx)
            for idx, row in enumerate(rows)
        ]
        ax.plot(xs, ys, marker=spec.marker, color=palette[0])
        if spec.shadow_field is not None:
            band = [
                _as_float(
                    _require_field(row, spec.shadow_field, idx),
                    field=spec.shadow_field,
                    row_index=idx,
                )
                for idx, row in enumerate(rows)
            ]
            lo = [y - b for y, b in zip(ys, band, strict=True)]
            hi = [y + b for y, b in zip(ys, band, strict=True)]
            ax.fill_between(xs, lo, hi, alpha=0.2, color=palette[0])
        return

    groups = _group_by(rows, spec.series_field)
    color_cycle = cycle(palette)
    for series_key, series_rows in groups.items():
        color = next(color_cycle)
        series_sorted = sorted(
            series_rows,
            key=lambda r: _as_float(
                _require_field(r, spec.x_field, 0), field=spec.x_field, row_index=0
            ),
        )
        xs = [
            _as_float(_require_field(r, spec.x_field, idx), field=spec.x_field, row_index=idx)
            for idx, r in enumerate(series_sorted)
        ]
        ys = [
            _as_float(_require_field(r, spec.y_field, idx), field=spec.y_field, row_index=idx)
            for idx, r in enumerate(series_sorted)
        ]
        ax.plot(xs, ys, marker=spec.marker, color=color, label=str(series_key))
        if spec.shadow_field is not None:
            band = [
                _as_float(
                    _require_field(r, spec.shadow_field, idx),
                    field=spec.shadow_field,
                    row_index=idx,
                )
                for idx, r in enumerate(series_sorted)
            ]
            ax.fill_between(
                xs,
                [y - b for y, b in zip(ys, band, strict=True)],
                [y + b for y, b in zip(ys, band, strict=True)],
                alpha=0.2,
                color=color,
            )
    ax.legend()


def draw_scatter(
    ax: Any, spec: ScatterFigureSpec, rows: list[dict[str, Any]], palette: list[str]
) -> None:
    base_size = 30.0
    if spec.series_field is None:
        xs = [
            _as_float(_require_field(row, spec.x_field, idx), field=spec.x_field, row_index=idx)
            for idx, row in enumerate(rows)
        ]
        ys = [
            _as_float(_require_field(row, spec.y_field, idx), field=spec.y_field, row_index=idx)
            for idx, row in enumerate(rows)
        ]
        sizes: list[float] | float
        if spec.size_field is not None:
            sizes = [
                base_size
                * _as_float(
                    _require_field(row, spec.size_field, idx), field=spec.size_field, row_index=idx
                )
                for idx, row in enumerate(rows)
            ]
        else:
            sizes = base_size
        ax.scatter(xs, ys, s=sizes, c=palette[0], alpha=0.75, edgecolor="none")
        return

    groups = _group_by(rows, spec.series_field)
    color_cycle = cycle(palette)
    for series_key, series_rows in groups.items():
        color = next(color_cycle)
        xs = [
            _as_float(_require_field(r, spec.x_field, idx), field=spec.x_field, row_index=idx)
            for idx, r in enumerate(series_rows)
        ]
        ys = [
            _as_float(_require_field(r, spec.y_field, idx), field=spec.y_field, row_index=idx)
            for idx, r in enumerate(series_rows)
        ]
        if spec.size_field is not None:
            sizes = [
                base_size
                * _as_float(
                    _require_field(r, spec.size_field, idx), field=spec.size_field, row_index=idx
                )
                for idx, r in enumerate(series_rows)
            ]
        else:
            sizes = base_size
        ax.scatter(xs, ys, s=sizes, c=color, alpha=0.75, edgecolor="none", label=str(series_key))
    ax.legend()


def draw_forest(
    ax: Any, spec: ForestFigureSpec, rows: list[dict[str, Any]], palette: list[str]
) -> None:
    labels: list[str] = []
    estimates: list[float] = []
    lows: list[float] = []
    highs: list[float] = []
    for idx, row in enumerate(rows):
        labels.append(str(_require_field(row, spec.label_field, idx)))
        estimates.append(
            _as_float(
                _require_field(row, spec.estimate_field, idx),
                field=spec.estimate_field,
                row_index=idx,
            )
        )
        lows.append(
            _as_float(
                _require_field(row, spec.ci_low_field, idx), field=spec.ci_low_field, row_index=idx
            )
        )
        highs.append(
            _as_float(
                _require_field(row, spec.ci_high_field, idx),
                field=spec.ci_high_field,
                row_index=idx,
            )
        )
    y_positions = list(range(len(labels)))
    primary = palette[0]
    ax.axvline(spec.ref, linestyle="--", color="#888888", linewidth=0.6)
    # Draw whiskers + point estimates.
    for y, est, lo, hi in zip(y_positions, estimates, lows, highs, strict=True):
        ax.hlines(y, lo, hi, color=primary, linewidth=1.2)
        ax.plot([est], [y], marker="s", color=primary, markersize=5)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # first label on top
