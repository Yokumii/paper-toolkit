# `claims.json` schema

Stored at `analysis/<H>/<E>/claims.json`. The toolkit Pydantic model is
`paper_toolkit.models.analysis.ClaimsFile` — read it if anything below
seems ambiguous.

```json
{
  "schema_version": "1.0",
  "hypothesis_id": "h1",
  "experiment_id": "e1",
  "claims": [
    {
      "claim_id": "growth",
      "text": "Agents in arm B drift outward at twice the rate of arm A.",
      "kind": "comparative",
      "evidence": "agent_status_profile",
      "figure_contract": {
        "figure_id": "fig_growth",
        "rationale": "Bar chart of mean displacement at tick 100 per arm."
      }
    }
  ]
}
```

## Field rules

- `claim_id` — `^[a-z][a-z0-9_]*$`. Stable across reruns; the lift
  bridge derives the paper-side node id as `claim_<claim_id>`.
- `text` — the claim itself, written as a single sentence in declarative
  form. No hedging that the evidence doesn't actually earn (the
  skeptical-review prompt enforces verb calibration).
- `kind`:
  - `quantitative` — supported by a stat / aggregate / model.
  - `comparative` — A vs B with a directional verdict.
  - `qualitative` — supported by a narrative pattern in a sampled record
    set (use sparingly; require concrete row references in `evidence`).
- `comparative` claims often need figure data drawn from more than the
  current experiment's local summary. If the verdict is treatment vs
  control, pro- vs counter-attitudinal, or any other A vs B contrast,
  the figure should usually show both sides on the same axes.
- `evidence` — the slug of the supporting profile or query, e.g.
  `agent_status_profile` or `tick_avg_x_by_arm`. Must point at an
  existing artifact under `eda/`; if it doesn't, the claim is not
  evidenced and the skeptical review will catch it.
- `figure_contract.figure_id` — `^[A-Za-z0-9_-]+$`. Matches a FigureSpec
  filename stem under `paper/figure_specs/`.
- `figure_contract.rationale` — one sentence: which chart kind + why it
  is the honest read of the data. Do NOT restate the claim here.

## What is NOT allowed

- A claim without `evidence`. Even qualitative claims must point at a
  query result.
- A `figure_contract` with `figure_id` pointing at a spec that doesn't
  exist (the Refine stage checker fails).
- Free-form fields. `extra="forbid"` — any typo means the file fails to
  load.

## Strength mapping (used by the lift bridge)

When `paper analysis lift-to-evidence` promotes a claim into
`paper/evidence_graph.json`, it derives `ClaimStrength` from `kind`:

| analysis `kind` | paper `strength` |
|---|---|
| `quantitative` | `primary` |
| `comparative` | `primary` |
| `qualitative` | `supporting` |

If you want a claim to land as `supporting` in the paper graph but it is
quantitative, tag it as such in the `agentsociety-generate-paper` skill *after* lift (
`paper evidence rm-node` + re-`add-claim` with explicit `--strength`).
Do not lie in `claims.json`.
