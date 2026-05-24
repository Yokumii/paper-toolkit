# Subagent workflow — when to delegate

Single-agent execution is fine for one-experiment, one-hypothesis runs.
Subagent-driven mode is required when ANY of these apply:

- Three or more experiments under the same hypothesis.
- Multiple producers needed in parallel (e.g., bilingual reports + a
  separate synthesis brief).
- A review pass would benefit from role isolation (producer can't see
  reviewer's running context).

## Roles

| Role | Subagent prompt | Owns |
|---|---|---|
| Data explorer | `subagent_prompts/data-explorer.md` | profile-table + query loops in stage 2 |
| Claim extractor | `subagent_prompts/claim-extractor.md` | converting observations into typed claims (stage 3) |
| Figure spec author | `subagent_prompts/figure-spec-author.md` | authoring the FigureSpec JSON for one claim |
| Figure reviewer | `subagent_prompts/figure-reviewer.md` | reading the spec against `figure_publication_contract.md` BEFORE render |
| Report producer | `subagent_prompts/report-producer.md` | drafting `report_<lang>.md` for one language |
| Report reviewer | `subagent_prompts/report-reviewer.md` | skeptical pass over a produced report |
| Synthesis producer | `subagent_prompts/synthesis-producer.md` | writing the cross-experiment narrative |
| Synthesis reviewer | `subagent_prompts/synthesis-reviewer.md` | independent pass over the brief + narrative |

## Iron rules

1. **Producer + reviewer must be distinct subagents** at stage 5 and
   stage 6. The controller must NOT review its own producer's output.
2. **Figure reviewer runs BEFORE render.** Rendering the PDF first
   wastes the audit trail; the reviewer's verdict belongs in the spec
   review record, not in a "we already rendered, now what" loop.
3. **Subagent prompts open with the relevant references.** Each
   subagent_prompts/*.md file points at the references the role needs.
   The controller must NOT paste reference content into the dispatch
   payload; the subagent reads it itself.
4. **Do not switch modes mid-loop.** If you started a section's
   producer-reviewer cycle in subagent-driven mode, finish it that way.
   Falling back to "I'll just fix it directly" loses the audit trail.

## Dispatch payload shape

Always pass these to a subagent:

- `hypothesis_id`, `experiment_id` (when scoped to one experiment).
- The relevant artifact paths (e.g., `paper/figure_specs/<id>.json` for
  the figure reviewer).
- The required references the subagent must Read first.
- The single expected output artifact path (e.g., `paper/reviews/...`,
  `analysis/<H>/<E>/report_<lang>.md`).
- Termination condition (what "done" looks like, in one sentence).

Never pass:
- The controller's running notes / context.
- Premature opinions about the verdict.
- Cross-experiment information when the subagent's scope is one
  experiment.
