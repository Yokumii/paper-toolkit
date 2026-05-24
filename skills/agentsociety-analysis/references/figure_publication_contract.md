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

You do not set these yourself in a custom matplotlib script — there is no
custom matplotlib script. You author a FigureSpec; the renderer applies
the preset.

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

Heatmap, network, radar, GridSpec multi-panel are NOT in scope for v1.
If your claim needs them, restructure the claim or add the chart in a
follow-up version.

## Editable text + embedded fonts

- `pdf.fonttype = 42` means every glyph in the PDF is an outlined
  TrueType reference, NOT a rasterized image. Reviewers / editors can
  re-typeset.
- `paper check figure-qa` verifies the font dictionary contains
  `FontFile*` entries (i.e., the font IS embedded), the font family is
  one of `Arial / Helvetica / DejaVu / Liberation`, and the PDF width
  matches the column target. Fix what it flags; do not silence it.

## What you must NEVER do

1. Author a matplotlib script of your own. The renderer is the audit
   surface.
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
