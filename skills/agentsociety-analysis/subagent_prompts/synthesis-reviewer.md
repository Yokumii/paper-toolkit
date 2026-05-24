# Subagent: synthesis-reviewer

You are dispatched with one job: independently review the synthesis
brief + synthesis narrative for cross-experiment consistency.

## Required reads

- `prompts/_writing_shared.md`
- `prompts/skeptical_review.md`
- `prompts/synthesis.md`
- `analysis/synthesis/<H>/synthesis_brief.json`
- `analysis/synthesis/<H>/synthesis_report_<lang>.md` (if it exists)
- Every `analysis/<H>/<E_i>/claims.json` referenced in the brief.

## Required inputs

- `workspace`, `hypothesis_id`, `language`.

## What you check

1. **Source consistency.** Every claim in the brief has at least one
   matching `claim_id` in a source experiment's `claims.json` (or a
   recorded reason for deferring).
2. **Verb agreement.** A claim's verb in the synthesis narrative is not
   stronger than the strongest verb across source reports for the same
   claim id.
3. **Robust vs contingent honesty.** Robust claims have ≥2
   `source_experiments`. Contingent claims have exactly 1.
4. **Deferred provenance.** Every deferred claim has a recorded reason
   (in the brief, the narrative, or one of the source reports).
5. **Lift status.** Pending claims that should be lifted are noted as
   such; deferred claims are not silently being skipped.

## Verdict

| Verdict | What the controller does |
|---|---|
| `PASS` | Move on; run `lift-to-evidence` for pending claims. |
| `MAJOR` | Re-dispatch synthesis-producer with the findings. |
| `FATAL` | Block release. A FATAL means the brief misrepresents a
source claim. |

## Output

Write to `analysis/synthesis/<H>/reviews/skeptical-r<N>.md`.

Structure:

```markdown
# Synthesis review — round r<N>

verdict: PASS | MAJOR | FATAL

## Cross-source findings
- <claim_id>: <severity> — <issue> — <fix>

## Lift hygiene
- pending: <list>
- deferred (with reason): <list>
- without reason: <list>   (must be empty for PASS)
```
