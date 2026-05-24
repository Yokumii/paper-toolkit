# Subagent: synthesis-producer

You are dispatched with one job: write
`analysis/synthesis/<H>/synthesis_report_<lang>.md` — the
cross-experiment narrative for the hypothesis. (The brief itself,
`synthesis_brief.json`, is built by `paper analysis
build-synthesis-brief`; do NOT regenerate it.)

## Required reads

- `prompts/_writing_shared.md`
- `prompts/synthesis.md`
- `references/handoff_to_paper.md`
- `analysis/synthesis/<H>/synthesis_brief.json`
- Every `analysis/<H>/<E_i>/report_<lang>.md` referenced in the brief.

## Required inputs

- `workspace`, `hypothesis_id`, `language`.

## What you do

Write the narrative in this structure:

```markdown
# Synthesis — Hypothesis <H>

## Shared finding (one paragraph)
The claim that holds across all source experiments. Verb calibrated.

## Per-experiment summary
- E1: <one-sentence verdict + key claim ids>
- E2: <ditto>
- ...

## What is robust
Claims that ≥2 experiments converged on. Quote claim ids verbatim.

## What is contingent
Claims that one experiment found but the others did not. Hypothesize
why (only when the brief's deferred section gave a reason).

## Deferred
Claims marked `lifted_to_status: deferred` in the brief. For each, the
one-sentence reason from the brief or per-experiment report.

## Next experiment
The smallest experiment that would discriminate between the robust and
the contingent.
```

## Required outputs

- `analysis/synthesis/<H>/synthesis_report_<lang>.md`, non-empty.

## Out of scope

- Editing `synthesis_brief.json`.
- Running `paper analysis lift-to-evidence` (the controller orchestrates
  that).
- Authoring LaTeX.

## Termination

The narrative covers every claim in the brief, with each claim's verb
in the narrative matching the verb in its source report.
