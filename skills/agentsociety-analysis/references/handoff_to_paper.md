# Handoff to the `agentsociety-generate-paper` skill

The `agentsociety-analysis` skill produces three classes of artifact the
`agentsociety-generate-paper` skill consumes:

1. **Claims**, promoted into `paper/evidence_graph.json` via
   `paper analysis lift-to-evidence`. After lift, every analysis claim
   appears as `claim_<claim_id>` with an associated `ev_<figure_id>`
   evidence node and a `supports` edge. `paper check claim-coverage`
   then sees them.

2. **Figures**, rendered into `paper/figures/<id>.pdf` (+ `.tex`
   wrapper) and registered in `paper.json:artifacts.figures[]` via
   `paper figure register`. After registration, `paper compose
   pack-figures` and `paper check figures` both see them.

3. **Report context**, written to `analysis/<H>/<E>/report_zh.md` /
   `report_en.md`. The `agentsociety-generate-paper` skill's writing
   prompts (`writing_intro`, `writing_results`, `writing_discussion`,
   ...) read from these for narrative continuity, but the LaTeX section
   files (`paper/sections/<section>.tex`) are still authored under the
   paper-writing skill — there is no md→tex pipeline.

## Order of operations across the two skills

A typical full project goes:

```
agentsociety-analysis: intake -> explore -> claims -> refine
         |
         | (charts now exist + bound to claims)
         v
agentsociety-analysis: produce  (bilingual MD reports)
         v
agentsociety-analysis: build-synthesis-brief
         v
agentsociety-analysis: lift-to-evidence
         v
agentsociety-generate-paper: intake / scan
agentsociety-generate-paper: use existing claim nodes; add citations + extra evidence nodes
agentsociety-generate-paper: draft sections (reads analysis/<H>/<E>/report_*.md for prose anchors)
agentsociety-generate-paper: compile + checks + skeptical review
```

## What `agentsociety-generate-paper` does NOT inherit

- The analysis report's prose. The paper LaTeX is written fresh; the
  Markdown is *source material*, not a draft.
- Synthesis brief deferred claims. Anything tagged `deferred` does not
  appear in the paper unless the paper-side controller explicitly
  re-evaluates it.
- EDA profiles + query results. Those are work-product, not deliverable.
  Do not link to them from the paper.

## What you must NOT do

- Author LaTeX section files inside the `agentsociety-analysis` skill. That is the
  `agentsociety-generate-paper` skill's job.
- Edit `paper/evidence_graph.json` by hand after lift. Use the
  `agentsociety-generate-paper` skill's `evidence` verbs.
- Skip `lift-to-evidence` and hand-author the evidence DAG to "save
  steps." The lift is deterministic; bypassing it leaks judgment.

## Verifying the handoff

After both skills have run, the terminal verification:

```text
paper analysis status --workspace .
# every experiment should report stage = "synthesis"

paper analysis check-synthesis --hypothesis-id H --workspace .
# clean

paper check claim-coverage --workspace .
# clean — every lifted claim has an evidence edge

paper compose pack-figures --workspace .
# every registered figure copied / linked into paper/figures/

paper check figures --workspace .
# clean — no unreferenced figures, no duplicate labels
```
