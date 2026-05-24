# Stage 1 — Intake

You are starting an analysis run for a specific experiment. The user
points at a `sqlite.db`, a hypothesis id, and an experiment id.

## Pre-reads (required)

- `references/workflow.md` — what each stage gates on.
- `references/output_layout.md` — what directory holds what.

## What to do

1. `paper analysis init --hypothesis-id H --experiment-id E --db PATH`.
   Confirm the envelope shows the right experiment directory and the
   language (read `paper.json:meta.language` first if a paper workspace
   exists; otherwise default `bilingual` is fine).

2. Examine the run context. Read (where they exist):
   - `<workspace>/<run-dir>/steps.yaml` if the experiment shipped one.
   - `<workspace>/<run-dir>/run.json` if the experiment shipped one.
   - The first `paper analysis list-tables --db PATH` output to see what
     shape the data is in.

3. Draft `analysis_plan.yaml`. The plan has exactly these fields (see
   `paper_toolkit.models.analysis.AnalysisPlan`):

   ```yaml
   schema_version: "1.0"
   hypothesis_id: h1
   experiment_id: e1
   research_question: <one falsifiable, scoped sentence>
   must_inspect:
     - agent_status
     - agent_profile
     # tables whose absence would invalidate the question
   expected_claim_count: 3
   notes: |
     Optional context the explore / claims stages will need.
   ```

4. `paper analysis write-plan --payload analysis_plan.yaml ...` then
   `paper analysis check-plan ...`. Loop until the check is clean.

## Quality bar (from `analysis_quality.md`)

- `research_question` is ONE falsifiable, scoped sentence. NOT "explore
  agent behavior."
- `must_inspect` lists every table whose absence would invalidate the
  question — not every table in the database. A typical run inspects
  2–4 tables.
- `expected_claim_count` is honest. If you expect 1, write 1.

## Done when

`paper analysis check-plan` is clean AND you can articulate the plan's
research question in one breath without consulting it.
