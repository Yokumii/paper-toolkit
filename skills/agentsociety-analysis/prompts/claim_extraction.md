# Stage 3 — Claim extraction

You are converting your explore notes into typed claims that the report
will quote and that the lift bridge will promote into the paper's
evidence DAG.

## Pre-reads (required)

- `prompts/_writing_shared.md` — the verb-calibration ladder.
- `references/claim_schema.md` — exact shape of each claim.
- `references/analysis_quality.md` — what disqualifies a claim.

## What to do

For each candidate answer in your explore notes:

1. Pick the strongest verb the evidence earns (default weaker, per the
   ladder).
2. Write the claim as ONE sentence in declarative form. No qualifiers
   beyond what the verb already carries.
3. Pick `kind`:
   - `quantitative` — supported by an aggregate / model / stat.
   - `comparative` — A vs B with a directional verdict.
   - `qualitative` — narrative pattern in concrete rows (use sparingly).
4. Set `evidence` to the slug of the supporting profile or query.
5. Run `paper analysis record-claim --hypothesis-id H --experiment-id E
   --claim-id <id> --text "..." --kind ... --evidence ...`.

Loop until you've recorded a claim per candidate answer.

## Quality bar

- Each claim text passes verb calibration. The skeptical reviewer
  enforces this — do not pre-emptively soften everything to dodge it;
  the right verb is the strongest one the evidence earns.
- No two claims are paraphrases. Merge or split.
- `evidence` points at a real eda/ artifact.

## Anti-patterns

- "All agents are interesting" — not falsifiable; not a claim.
- "The treatment works" — over-strong without a comparison + stat.
- Two claims sharing the same evidence slug with conflicting verbs.

## Done when

`paper analysis check-claims --hypothesis-id H --experiment-id E` is
clean AND every claim's verb is the strongest one the evidence honestly
earns.
