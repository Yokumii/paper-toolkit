# Workflow — six stages, derived from artifacts

The pipeline has six stages, but `state.yaml` does NOT carry a `current_stage`
flag. Stages are *derived* from the artifacts on disk; the deterministic
`check-*` verbs are the only ground truth.

| Stage | Done when ... |
|---|---|
| 1. Frame | `analysis/<H>/<E>/analysis_plan.yaml` exists AND parses AND ids match. |
| 2. Explore | every `must_inspect` table in the plan has a `<table>_profile.json` under `analysis/<H>/<E>/eda/`. |
| 3. Claims | `analysis/<H>/<E>/claims.json` exists, non-empty, validates, has no duplicate `claim_id`. |
| 4. Refine | every claim has a `figure_contract`; matching FigureSpec exists under `paper/figure_specs/<figure_id>.json`; rendered PDF exists at `paper/figures/<figure_id>.pdf`. |
| 5. Produce | required language reports exist and are non-empty under `analysis/<H>/<E>/report_<lang>.md`. |
| 6. Synthesis | `analysis/synthesis/<H>/synthesis_brief.json` exists; every claim has `lifted_to` set OR `lifted_to_status == "deferred"`. |

`paper analysis status` runs the six checks in order and reports the
highest stage that cleared. If `check-refine` fails, you are still at
"Claims". Fix the failing artifact; do not advance.

## When a check fails

Each `check-*` verb returns an `Envelope` with `errors[].code`. The
codes map to the artifact you need to fix:

| Code | What's wrong | Where to look |
|---|---|---|
| `ANL_PLAN_MISSING` | no `analysis_plan.yaml` | author one, run `write-plan` |
| `ANL_PLAN_INVALID` | plan fails Pydantic | edit it and re-`write-plan` |
| `ANL_PLAN_ID_MISMATCH` | plan ids ≠ CLI args | one of the two is wrong; fix the source |
| `ANL_EDA_TABLE_MISSING` | a `must_inspect` table is unprofiled | run `profile-table` for it |
| `ANL_CLAIMS_MISSING` | no `claims.json` | run `record-claim` at least once |
| `ANL_CLAIMS_EMPTY` | file is `{... "claims": []}` | record claims |
| `ANL_CLAIMS_DUP` | duplicate `claim_id` | clean `claims.json` (or upsert correctly) |
| `ANL_REFINE_NO_CONTRACT` | a claim has no figure binding | `record-figure-contract` |
| `ANL_REFINE_SPEC_MISSING` | `paper/figure_specs/<id>.json` is absent | author it |
| `ANL_REFINE_PDF_MISSING` | `paper/figures/<id>.pdf` is absent | run `paper figure render` |
| `ANL_REPORT_MISSING` | a required-language report is absent | author it |
| `ANL_REPORT_EMPTY` | report file is zero bytes | write something |
| `ANL_SYNTHESIS_NOT_LIFTED` | a synthesis claim is neither lifted nor deferred | run `lift-to-evidence` |

The skill's job is to consume those codes and *act*, not to argue with
the checker.

## What about loops?

Real analyses loop. After `check-refine` lands a chart, you may discover
a claim is too strong → return to claim_extraction → re-record → re-check.
That's fine; the derived-stage model handles it. The only invariant: do
not declare a downstream stage complete while an upstream stage is
failing.
