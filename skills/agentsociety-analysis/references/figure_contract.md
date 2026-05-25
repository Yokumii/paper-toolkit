# Figure contract — one chart per claim, one claim per chart

This is the analysis-side equivalent of the `agentsociety-generate-paper`
skill's evidence discipline. Every chart we render exists to support
exactly one claim; every claim that is concrete enough to land in the
paper has exactly one chart bound to it.

## Why

- Charts without claims are decoration. Reviewers ignore them; readers
  argue over them.
- Claims without charts cannot be verified at a glance. The chart is the
  reader's shortest path to "I see what you mean."
- A chart that tries to support two claims always ends up doing neither
  justice — and the second claim escapes into the prose without an
  anchor.

## The contract steps

1. **Claim first.** Recorded via `paper analysis record-claim` with a
   pointer to the supporting profile / query slug.
2. **Write the figure contract.** Before authoring the spec, record the
   core conclusion, figure archetype, hero evidence, supporting
   evidence, panel map, and the statistics / source-data /
   image-integrity notes a reviewer will ask for. The chart exists to
   serve the claim's scientific logic, not to maximize panel count.
3. **Pick the honest chart kind.** Use the chooser in
   `references/chart_qa.md`. If three kinds would all work, the data is
   not yet shaped to support a sharp claim — return to explore.
4. **Author the spec.** Filename = `<figure_id>.json` under
   `paper/figure_specs/`. The figure-spec-author subagent owns this
   step; the figure-reviewer subagent reads the spec against
   `references/figure_publication_contract.md` before any render runs.
5. **Render + register.** `paper figure render --spec ...` then
   `paper figure register --spec ...`. The PDF is the audit artifact;
   the SVG is the editable companion; the `paper.json` row is the
   discovery handle.
6. **Bind.** `paper analysis record-figure-contract --claim-id ...
   --figure-id ... --rationale ...`. The rationale is ONE sentence: chart
   kind + why this is the honest read. Do not restate the claim.
7. **Verify.** `paper analysis check-refine` + `paper check figure-qa`
   together close the loop.

For comparative claims, the chart must carry the comparison on its own
axes. A comparative claim is disqualified if its chart omits one side of
the comparison and leaves the actual contrast to prose. Use rows from
sibling experiments when that is what the claim compares; a
single-experiment summary is acceptable only for quantitative claims
whose verdict does not depend on a second arm / condition.

For multi-panel figures, use a declared hierarchy. `quantitative grid`
is appropriate when panels share one numerical grammar. `schematic-led
composite`, `image plate + quant`, and `asymmetric mixed-modality
figure` are appropriate when one hero panel must lead and supporting
panels defend it. Equal-sized panels are acceptable only when the
evidence is genuinely equal in weight.

## What disqualifies a chart

- It shows N curves where N-1 are not referenced by any claim.
- It uses a chart kind whose strongest visual statement is something the
  claim does NOT make (e.g., a stacked area chart implying "proportions
  sum to 1" when the claim is about absolute values).
- It encodes the only meaningful contrast in color where the contrast
  could have been encoded in axis position. Color is the weakest channel
  on the perceptual ladder.
- It has no declared hero panel or panel hierarchy even though the
  figure is mixed-modality and clearly contains primary vs supporting
  evidence.
- A comparative claim is disqualified if its chart omits one side of the
  comparison, or if the figure is only a single-experiment summary while
  the verdict lives in prose.
- Two distinct claims point at the same figure_id with different
  rationales. Split into two charts; do not have one chart claim two
  things.
