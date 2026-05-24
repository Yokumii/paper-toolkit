# Stage 5 — Produce the report

You are drafting `analysis/<H>/<E>/report_zh.md` and
`analysis/<H>/<E>/report_en.md` (skip one if `config.yaml.language`
narrows the requirement). The reports are written FROM `claims.json` +
EDA artifacts + `report_context.md`, not from general knowledge.

## Pre-reads (required)

- `prompts/_writing_shared.md`
- `references/handoff_to_paper.md` — what the agentsociety-generate-paper skill expects to
  consume.
- `analysis/<H>/<E>/report_context.md` — built by
  `paper analysis build-report-context`. Run it first.

## What to do

1. `paper analysis build-report-context --hypothesis-id H
   --experiment-id E --workspace .`. This writes
   `report_context.md` (one section per claim with evidence + figure
   refs) and `evidence_index.json` (machine-readable index).

2. Open `report_context.md` and read it cover to cover. It is the
   producer's working brief.

3. Write `report_zh.md` (and `report_en.md` when the language config
   demands bilingual). Structure:

   ```markdown
   # Title — Hypothesis H, Experiment E

   ## Background (≤200 words)
   What question this experiment is answering, and why it matters
   given the hypothesis context.

   ## Method (≤300 words)
   What data we have (table names + sizes from list-tables / profiles).
   How we sliced it for each claim (slug names from eda/).

   ## Findings (most of the report)
   One subsection per claim. Quote the claim text verbatim. State the
   supporting numbers (with units). Reference the bound figure by
   `figure_id`. Use the verb the claim's `kind` + evidence earns; do
   NOT promote a "suggests" claim to "shows" in the report.

   ## Caveats
   Anything the claim quietly assumes. Anything the explore stage
   could not reach. Anything a future replication should test.
   ```

4. Save both languages.

5. `paper analysis check-release --hypothesis-id H --experiment-id E
   --workspace .` — passes only when required-language files exist and
   are non-empty.

6. **Dispatch the report-reviewer subagent** (see
   `subagent_prompts/report-reviewer.md`). The reviewer reads
   `claims.json`, EDA artifacts, AND the report; flags any sentence
   not earned by the artifacts. Revise. Repeat until the verdict is
   PASS.

## Quality bar

- Every claim from `claims.json` appears in the Findings section, in
  some order, with the verb it earned.
- Every number in the report has a provenance (claim id, slug name, or
  figure id).
- Bilingual versions agree on verb choice for each claim (no "shows" in
  English / "证明" in Chinese for the same claim).

## Anti-patterns

- Writing the report first, then trying to retrofit claims.
- Re-paraphrasing the report_context — it IS the brief, not the
  output.
- Hedging in the prose to dodge a missing evidence slug. Fix the slug.

## Done when

`paper analysis check-release` is clean AND the report-reviewer
subagent's most recent verdict is PASS.
