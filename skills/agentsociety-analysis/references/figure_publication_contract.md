# Figure publication contract (the hard rules)

paper-toolkit's `paper figure render` already enforces the publication
floor. Specifically it applies these in
`src/paper_toolkit/figures/style.py` and the palette module:

## rcParams the renderer sets for you

```python
"font.family": "sans-serif",
"font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
"svg.fonttype": "none",       # editable text in SVG
"pdf.fonttype": 42,           # editable TrueType in PDF
"font.size": <spec.font_size> # default 10; clamp 5..24
"axes.spines.right": False,
"axes.spines.top": False,
"axes.linewidth": 0.8,
"legend.frameon": False,
```

Structured figures inherit these automatically. Script-backed figures
must emit outputs that satisfy the same contract.

## Column widths

- `width: "single"` → 89 mm (3.5 inch fig width, single column)
- `width: "double"` → 183 mm (7.2 inch fig width, double column)

`paper check figure-qa` lints the rendered PDF against ±10 mm of these
targets. If it warns, the spec asked for the wrong width relative to
what the chart actually needs.

## Palettes

Pick one per spec via the `palette:` field. Four palettes ship with the
renderer:

- `nmi_pastel` — default. Pastel blues / greens / corals. Good for
  multi-arm comparisons where saturation should not shout.
- `nature_imaging` — saturated, photography-adjacent. Best for figures
  that sit beside images.
- `nature_material` — earth tones; right for materials / mechanics
  papers.
- `nature_clinical` — clinical reds / greens / neutrals; right when one
  arm is the treatment and one is control.

No rainbow colormaps. Red and green must NEVER be the sole encoding —
add line styles / hatch patterns / direct labels if you really need
those two together.

## Chart kinds the spec accepts

| Kind | When to use | Required fields |
|---|---|---|
| `bar` | discrete comparison of one variable across categories | `x_field`, `y_field` (+ `group_field`, `error_field` optional) |
| `line` | a continuous trend over an ordered axis | `x_field`, `y_field` (+ `series_field`, `shadow_field` optional) |
| `scatter` | the relationship between two variables across N observations | `x_field`, `y_field` (+ `series_field`, `size_field` optional) |
| `forest` | effect sizes with confidence intervals across studies / arms | `label_field`, `estimate_field`, `ci_low_field`, `ci_high_field` |

`composite` supports quantitative multi-panel layouts that can be
expressed with the built-in chart kinds. `script` exists for layouts
that need asymmetric hero panels, dedicated legend axes, dark image
plates, or chart families outside the built-in set. If a script-backed
figure is used, the selected backend must still emit `<id>.pdf` and
`<id>.svg` under `paper/figures/`.

## Editable text + embedded fonts

- `pdf.fonttype = 42` means every glyph in the PDF is an outlined
  TrueType reference, NOT a rasterized image. Reviewers / editors can
  re-typeset.
- `paper check figure-qa` verifies the font dictionary contains
  `FontFile*` entries (i.e., the font IS embedded), the font family is
  one of `Arial / Helvetica / DejaVu / Liberation`, and the PDF width
  matches the column target. Fix what it flags; do not silence it.

## Panel hierarchy + label policy

- Multi-panel figures should visibly rank evidence: one hero panel or
  hero row, then supporting panels.
- Panel labels stay lowercase, bold, and near the top-left of each
  panel unless a dark image plate requires an inside-white variant.
- Prefer direct labels or one shared legend area over repeating the same
  legend in every panel.

## What you must NEVER do

1. Emit only a PDF. Every rendered figure needs the editable SVG
   companion with matching content.
2. Use a fifth palette. Add one to the toolkit if you need it — do not
   pass a custom dict in the spec.
3. Set `font.size` above 24 or below 5. The renderer's validator rejects
   it.
4. Resave the PDF after rendering to "fix" anything. The PDF is the
   audit artifact; if it's wrong, fix the spec and re-render.

## The QA you must run after rendering

```text
paper check figure-qa --workspace .
```

It's deterministic — width, font family, font embedding. Treat each
finding as an input, not a debate.
