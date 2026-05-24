# Skeptical review — the analysis-side review pass

You are reading either a candidate `claims.json` or a candidate
`report_<lang>.md`, looking for ways the evidence does NOT actually
earn what's claimed.

## Pre-reads (required)

- `references/analysis_quality.md` — the per-stage bar.
- `references/claim_schema.md` (when reviewing claims).
- `prompts/_writing_shared.md` — the verb-calibration ladder.

## What to do

For each claim (and for each claim-bearing paragraph in a report),
answer five questions in writing:

1. **Verb calibration.** Is the verb the strongest the evidence earns
   (from the ladder)? If not, what's the right verb?
2. **Evidence provenance.** Does the cited slug actually exist under
   `eda/`? Does its content support the claim's directional verdict, or
   does it merely fail to contradict it?
3. **Confounds.** What confound, if real, would make this claim wrong?
   Is that confound visible in any other slug?
4. **Sample / scope.** Is the claim scoped to the data we have? A
   claim about "agents" generally is suspect when the data is one run
   of N=50.
5. **Misalignment.** Is there a chart, table, or paragraph elsewhere
   that contradicts this claim's verb? If yes, the contradiction must
   be resolved before release.

## Severity

| Class | What it means |
|---|---|
| `fatal` | The claim is wrong (data refutes it) OR there is no evidence at all. Block release. |
| `major` | The claim's verb is one level stronger than earned. Block release until downshifted. |
| `minor` | Phrasing, hedging language, missing unit. Defer if needed; record in the review note. |

## Output

Write the review to:
- `analysis/<H>/<E>/reviews/skeptical-r<N>.md` for report reviews.
- Inline notes in your reply for spec / claim reviews (the controller
  acts on them immediately).

Each finding has: `claim_id` (or section heading), severity, the
exact issue, the suggested fix. No prose padding.

## What you are NOT doing

- Re-running the deterministic checkers. They already ran.
- Re-deriving the claim from raw EDA. Trust the slug, read what's at
  that slug, then judge fit.
- Suggesting prose polish. Other passes do that.
