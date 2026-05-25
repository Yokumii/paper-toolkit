# Stage 4 — Figure emission (Refine)

You are authoring a `paper/figure_specs/<id>.json` for each recorded
claim, rendering it via `paper figure render`, registering it via
`paper figure register`, and binding it to the claim via `paper
analysis record-figure-contract`.

## Pre-reads (REQUIRED — call Read on each before any tool call in this stage)

- `skills/agentsociety-analysis/references/figure_publication_contract.md` — the hard rules baked into the renderer.
- `skills/agentsociety-analysis/references/figure_contract.md` — one chart per claim discipline.
- `skills/agentsociety-analysis/references/chart_qa.md` — chart-kind chooser + encoding ladder.

If you cannot point at three fresh Read tool calls covering these
files, you have NOT done the pre-reads. Do them before touching the
spec JSON.

## What to do, per claim

1. **Pick the honest chart kind** from `chart_qa.md`. If three kinds
   would all work, the data is not shaped to support a sharp claim —
   sharpen the claim or restructure the data before authoring the
   spec.

2. **Author the spec** at `paper/figure_specs/<figure_id>.json`. The
   FigureSpec discriminator + per-kind required fields are in
   `paper_toolkit/models/figure_spec.py`. Minimum example:

   ```json
   {
     "kind": "bar",
     "id": "fig_growth",
     "caption": "Mean displacement at tick 100, per arm.",
     "palette": "nmi_pastel",
     "width": "single",
     "xlabel": "Arm",
     "ylabel": "Displacement (a.u.)",
     "x_field": "arm",
     "y_field": "y",
     "error_field": "se",
     "data": [
       {"arm": "Control", "y": 0.42, "se": 0.04},
       {"arm": "Treatment", "y": 0.78, "se": 0.05}
     ]
   }
   ```

   Inline `data` is fine for ≤50 rows; for larger data, point `data` at
   a CSV path (resolved spec-dir → workspace).

3. **Dispatch the figure-reviewer subagent — MANDATORY, BEFORE render.**
   Use the dispatch payload shape from `prompts/_subagent_workflow.md`.
   The required-reads block in the dispatch prompt MUST list:
   - `skills/agentsociety-analysis/subagent_prompts/figure-reviewer.md`
   - `skills/agentsociety-analysis/references/figure_publication_contract.md`
   - `skills/agentsociety-analysis/references/chart_qa.md`
   - `skills/agentsociety-analysis/references/figure_contract.md`
   - `paper/figure_specs/<figure_id>.json`
   - the bound claim's record in `analysis/<H>/<E>/claims.json`

   Only render after the reviewer's verdict is `PASS`. Do NOT review
   the spec yourself "to save a round-trip" — that defeats the gate.

4. `paper figure render --spec paper/figure_specs/<id>.json --workspace
   .` → produces `paper/figures/<id>.pdf` + wrapper `.tex`.

5. `paper figure register --spec paper/figure_specs/<id>.json
   --workspace .` → inserts/updates `paper.json:artifacts.figures[]`.

6. `paper analysis record-figure-contract --hypothesis-id H
   --experiment-id E --claim-id <id> --figure-id <fid>
   --rationale "<one sentence>" --workspace .` — binds claim ↔ spec.

7. `paper check figure-qa --workspace .` — deterministic font / width
   / embedding lint over every PDF. Each warning is an input; fix the
   spec and re-render.

8. `paper analysis check-refine --hypothesis-id H --experiment-id E
   --workspace .` — passes only when every claim has contract + spec +
   PDF.

## Anti-patterns

- Authoring a matplotlib script instead of a spec. The renderer is the
  audit surface.
- Picking `line` for a comparison between two arms (use `bar`).
- Encoding the load-bearing contrast in color (use position).
- Skipping the figure-reviewer subagent because "the spec looks fine."

## Done when

`paper analysis check-refine` and `paper check figure-qa` are both clean.
