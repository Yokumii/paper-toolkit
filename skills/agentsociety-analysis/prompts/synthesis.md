# Stage 6 — Synthesis

You are aggregating claims across multiple experiments of the same
hypothesis into a single brief, lifting them into the paper's evidence
graph, and (optionally for v1) authoring a cross-experiment narrative.

## Pre-reads (REQUIRED — call Read on each before any synthesis tool call)

- `skills/agentsociety-analysis/references/workflow.md` — the synthesis gate definition.
- `skills/agentsociety-analysis/references/handoff_to_paper.md` — what the agentsociety-generate-paper skill consumes.

These must be Read in *this* stage, not just at skill trigger time.

## What to do

1. **Build the brief.** `paper analysis build-synthesis-brief
   --hypothesis-id H --experiment-id E1 --experiment-id E2 ... --workspace
   .` — aggregates `claims.json` files into
   `analysis/synthesis/<H>/synthesis_brief.json`. The toolkit
   deduplicates by `claim_id`; if two experiments use the same id, the
   brief's claim records both as `source_experiments`.

2. **Triage.** Walk the brief. For each `SynthesisClaim`:
   - If the claim is going into the paper, leave `lifted_to_status:
     pending` (it will become `lifted` after lift-to-evidence).
   - If the claim is NOT going into the paper, edit the brief by hand
     to set `lifted_to_status: deferred` and explain why in the
     synthesis report (`synthesis_report_<lang>.md`, optional v1).

3. **Lift.** For each experiment whose claims are pending, run
   `paper analysis lift-to-evidence --hypothesis-id H --experiment-id E
   --workspace .`. The lift bridge:
   - Adds `claim_<claim_id>` to `paper/evidence_graph.json` if not
     present.
   - Adds `ev_<figure_id>` evidence nodes and `supports` edges for
     every figure_contract.
   - Updates the synthesis brief's `lifted_to` / `lifted_to_status`
     fields automatically.

   The lift is idempotent — re-running only touches new rows.

4. **Verify.** `paper analysis check-synthesis --hypothesis-id H
   --workspace .` is clean only when every claim has `lifted_to` set
   OR `lifted_to_status: deferred`.

5. (Optional) Author `synthesis_report_zh.md` and
   `synthesis_report_en.md` under `analysis/synthesis/<H>/`. This is
   the cross-experiment narrative — what holds across the runs, what
   varies, what the next experiment should test. It is NOT a copy of
   any individual report. **Each language must be drafted by its own
   `synthesis-producer` subagent dispatch.**

6. **Dispatch the synthesis-reviewer subagent — MANDATORY whenever a
   synthesis report is authored.** Required-reads block:
   - `skills/agentsociety-analysis/subagent_prompts/synthesis-reviewer.md`
   - `skills/agentsociety-analysis/references/analysis_quality.md`
   - `analysis/synthesis/<H>/synthesis_brief.json`
   - `analysis/synthesis/<H>/synthesis_report_*.md`
   - per-experiment `analysis/<H>/<E>/claims.json` for every E in scope

   The reviewer compares the narrative against the brief's
   `source_experiments` evidence; any cross-experiment generalization
   not supported by ≥2 source experiments must be flagged. Do NOT
   review the synthesis report yourself.

## Quality bar

- Every claim with ≥2 `source_experiments` is the load-bearing kind
  for the paper. Claims with just one source are still allowed but
  usually mean the synthesis stage is premature.
- Deferred claims have a recorded reason — either as a one-line note
  in the synthesis report or, if you skipped the synthesis report,
  inline in the brief by appending a `note` field to the
  SynthesisClaim (then the model will fail validation; instead, write
  the reason somewhere durable that the agentsociety-generate-paper skill can see, e.g. a
  comment in the per-experiment report).

## Anti-patterns

- Forging cross-experiment agreement by listing the same experiment
  twice as `source_experiments`.
- Marking everything `deferred` to silence the gate.
- Editing `paper/evidence_graph.json` by hand instead of running lift.

## Done when

`paper analysis check-synthesis` is clean AND
`paper check claim-coverage --workspace .` reports no orphan claims.
