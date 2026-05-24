# Chart QA — acceptance contract for a rendered figure

Run `paper check figure-qa --workspace .` after every render. The
deterministic floor handles font family / fonttype 42 / column width.
This document covers what the deterministic check CANNOT see —
chart-kind appropriateness, encoding choice, and the data ↔ claim fit.

## Chart-kind chooser

| Claim shape | Honest kind | Why |
|---|---|---|
| "A is higher than B by ~X" | `bar` (with error bars when SE / CI available) | direct length comparison; least cognitive load |
| "Y rises with X" | `line` | implies continuity along X |
| "Y depends on multiple X's, no obvious order" | `scatter` (+ size/series channels if a third dimension matters) | does not impose continuity where there isn't any |
| "These effects across studies / arms cluster around / away from a reference" | `forest` | shows estimate + uncertainty per row; the reference line carries the verdict |

If none of the four fit, do not invent a kind. Re-shape the data to fit
one of them or sharpen the claim so a fit emerges.

## Encoding ladder (use the strongest channel that fits)

1. Position along a common axis (x, y) — strongest.
2. Length / area at a common baseline (bars).
3. Distance from a reference line (forest plots).
4. Slope / direction (line plots).
5. Color hue. Use last; never as the only encoding for an ordinal
   variable; never red/green as the sole encoding (accessibility).

## What a reviewer will flag

- Y-axis truncation that makes a 3% difference look like 80%.
- Logarithmic axes used to hide variance rather than reveal it.
- A `group_field` that produces 6+ bar groups packed together — split
  into panels (a future feature) or pick a different summary stat.
- "Mean ± SE" when the claim is about distribution shape — use a
  scatter / quantile representation, or sharpen the claim.
- An error_field that doesn't exist in the data (the spec validator
  catches that; the reviewer catches the *missing* error bar).

## After render — read the PDF before declaring done

The renderer never crashes on bad numbers; it just produces a chart that
silently misrepresents them. The figure-reviewer subagent must open the
PDF and confirm:

1. The axis labels match the claim's vocabulary.
2. The visible trend matches the claim's directional verb.
3. The chart's strongest visual statement IS the claim — not a
   different, weaker, or stronger version.

If any of those three fails, return to spec authoring.
