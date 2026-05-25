# Analysis quality — per-stage bar

For each stage, the bar is "what a skeptical reviewer would refuse to
let through." The deterministic `check-*` verbs do not measure these;
the agent must.

## Frame quality

- The plan's `research_question` is a single, falsifiable, scoped
  question. NOT "explore agent behavior."
- `must_inspect` lists every table whose absence would invalidate the
  question — not every table in the database.
- `expected_claim_count` is honest. If you expect 1, write 1, not 6 to
  look thorough.

## Explore quality

- Every column in a `*_profile.json` JSON-key summary is named in your
  intake notes or you should not have profiled the table.
- Every query you `paper analysis query`-ed has a slug under
  `eda/queries/` AND will be referenced by at least one claim.
- You stopped exploring when the data answered the plan's question, not
  when you ran out of patience.

## Claims quality

- Each claim text passes the verb-calibration check: the verb is the
  weakest one the evidence earns ("suggests" / "shows" / "establishes"
  ladder; default to weaker). The skeptical-review subagent enforces it.
- No claim is a paraphrase of another. Merge or split, do not duplicate.
- `evidence` points at a real artifact (the Refine checker enforces a
  spec/PDF but not the upstream profile slug — you do).

## Refine quality

- The figure-reviewer subagent OPENED the PDF and confirmed claim ↔
  chart fit before the chart was bound via `record-figure-contract`.
- The figure contract declares the archetype and, for multi-panel
  figures, makes the hero evidence vs supporting evidence hierarchy
  explicit.
- A comparative claim's chart includes every compared arm / condition
  needed to see the verdict. A prose-only comparison attached to a
  single-arm chart does not pass.
- The rationale field is informative — chart kind + why the kind is
  honest — not a restatement of the claim.
- `paper check figure-qa` is clean (or every warning has been judged).

## Produce quality

- The report's claims paragraph references every entry in `claims.json`,
  in some order, with the verb the claim earned — no more, no less.
- The report quotes specific numbers from the EDA artifacts. Numbers
  with no provenance lose readers.
- The bilingual versions agree on the verbs (no "shows" in English and
  "证明" in Chinese for the same claim).

## Synthesis quality

- Each synthesis claim has at least two `source_experiments` OR a
  rationale for being single-source (rare; usually means the synthesis
  stage is premature).
- `lifted_to` is set for every claim that the paper will use. Deferred
  claims are explicitly deferred with a one-line rationale in
  `report_zh.md` / `report_en.md` synthesis section — not silently
  abandoned.
