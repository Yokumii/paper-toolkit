# Figure and Table Spec Schemas

The toolkit owns rendering; the Skill owns spec authoring. Every spec is a
JSON file validated by Pydantic — typos and shape errors fail loud rather
than silently producing the wrong artifact.

- FigureSpec: `src/paper_toolkit/models/figure_spec.py` (discriminated union).
- TableSpec: `src/paper_toolkit/models/table_spec.py`.

## Common figure fields (every `kind`)

| field | type | notes |
|---|---|---|
| `id` | str | `[A-Za-z0-9_-]+`; used as filename stem. |
| `caption` | str | LaTeX-escaped automatically. |
| `label` | str \| null | Defaults to `fig:<id>`. |
| `palette` | one of `nmi_pastel` / `nature_imaging` / `nature_material` / `nature_clinical` | Default `nmi_pastel`. |
| `width` | `single` (89 mm) \| `double` (183 mm) | Default `single`. |
| `font_size` | 5–24 | Default 10. |
| `xlabel`, `ylabel`, `title` | str \| null | Optional. |
| `data` | list of row-dicts OR path | Path is resolved spec-dir → workspace → absolute. `.csv` / `.json` only. |

Run `paper figure list-palettes` to see the registered names from a
script.

## Bar (`kind: "bar"`)

```json
{
  "id": "fig_bar",
  "kind": "bar",
  "caption": "Endline gap by arm.",
  "data": [
    {"arm": "Control", "y": 0.42, "se": 0.03},
    {"arm": "Treatment", "y": 0.31, "se": 0.03}
  ],
  "x_field": "arm",
  "y_field": "y",
  "error_field": "se",
  "ylabel": "Affective gap"
}
```

Optional: `group_field` (grouped bars), `bar_width` (0–1, default 0.8),
`annotate` (writes the value on top of each bar).

## Line (`kind: "line"`)

```json
{
  "id": "fig_trend",
  "kind": "line",
  "caption": "Cross-cutting share over time.",
  "data": "trend.csv",
  "x_field": "t",
  "y_field": "share",
  "series_field": "arm",
  "shadow_field": "se"
}
```

`shadow_field` shades a `±value` band around the line. Omit
`series_field` for a single-line plot.

## Scatter (`kind: "scatter"`)

```json
{
  "id": "fig_scatter",
  "kind": "scatter",
  "caption": "Endline gap vs. baseline gap.",
  "data": "scatter.json",
  "x_field": "baseline",
  "y_field": "endline",
  "series_field": "arm",
  "size_field": "n"
}
```

`size_field` scales marker area by the column value.

## Forest (`kind: "forest"`)

```json
{
  "id": "fig_forest",
  "kind": "forest",
  "caption": "Per-study effect sizes with 95% CIs.",
  "data": "studies.csv",
  "label_field": "study",
  "estimate_field": "est",
  "ci_low_field": "lo",
  "ci_high_field": "hi",
  "ref": 0.0
}
```

`ref` draws a vertical reference line (typically 0 for effects, 1 for
odds ratios).

## TableSpec

```json
{
  "id": "tab1",
  "caption": "Treatment effects on cross-cutting reading.",
  "label": "tab:treatment",
  "columns": [
    {"header": "Arm", "align": "l"},
    {"header": "N", "align": "r"},
    {"header": "Endline gap (SE)", "align": "r"}
  ],
  "rows": [
    ["Control", "1,012", "0.42 (0.03)"],
    ["Counter-attitudinal", "1,008", "0.31 (0.03)"]
  ],
  "notes": ["SE in parentheses."],
  "placement": "h"
}
```

`column_spec` overrides the auto-derived alignment string when needed
(e.g. `"l@{}rr"`). Each `rows` entry must have exactly `len(columns)`
cells; Pydantic rejects the spec otherwise.

## Workflow

1. Write the spec at `paper/figure_specs/<id>.json` or
   `paper/table_specs/<id>.json`.
2. `paper figure render --spec ...` (or `paper table render --spec ...`).
3. Reference from a section: `\input{figures/<id>.tex}` or
   `\input{tables/<id>.tex}`.
4. `paper compose pack-figures` (for figures only) → `paper compose
   assemble-latex` → `paper compile-once`.

The Skill should add an evidence node for each rendered artifact:
`source.kind = figure` (or `table`), `source.ref = <id>`. This keeps
`paper check claim-coverage` aware of the new artifact.
