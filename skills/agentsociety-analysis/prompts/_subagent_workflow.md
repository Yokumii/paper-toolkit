# Subagent workflow — when to delegate

Subagent dispatch is REQUIRED at the stages that need role separation
(stage 4 figure-reviewer, stage 5 report-reviewer, stage 6 synthesis-
reviewer). It is also strongly recommended for parallelizable producers
(bilingual report drafting, multi-experiment synthesis).

The controller may run the deterministic CLI verbs itself, but it must
NOT play producer and reviewer in the same session for any of the
review-gated stages. Self-review is the dominant failure mode this
workflow exists to prevent.

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

1. **Producer + reviewer must be distinct subagents** at stages 4, 5, 6
   (figure-reviewer before render, report-reviewer over each produced
   report, synthesis-reviewer over the brief). The controller running
   the producer and then "reviewing" the result in the same session is
   a self-review and counts as skipping the gate.
2. **Figure reviewer runs BEFORE render.** Rendering the PDF first
   wastes the audit trail; the reviewer's verdict belongs in the spec
   review record, not in a "we already rendered, now what" loop.
3. **The controller MUST list the subagent's required reads in the
   dispatch prompt.** Subagent sessions start with empty context;
   without the explicit list they will not Read the references and
   will fall back to generic intuition. Use the dispatch payload
   shape below — there are no exceptions.
4. **Do not switch modes mid-loop.** If you started a section's
   producer-reviewer cycle in subagent-driven mode, finish it that way.
   Falling back to "I'll just fix it directly" loses the audit trail.

## Dispatch payload shape

Always pass these to a subagent:

- `hypothesis_id`, `experiment_id` (when scoped to one experiment).
- The relevant artifact paths (e.g., `paper/figure_specs/<id>.json` for
  the figure reviewer).
- **An explicit "Required reads" block listing every `references/*.md`
  and `prompts/*.md` the subagent must Read first.** Paths only, not
  content — the subagent calls Read itself. Without this block, the
  subagent will not find the references; it does not inherit the
  controller's context.
- The single expected output artifact path (e.g., `paper/reviews/...`,
  `analysis/<H>/<E>/report_<lang>.md`).
- Termination condition (what "done" looks like, in one sentence).

### Template

```
Role: <figure-reviewer | report-producer | ...>

Required reads (call Read on each before producing output):
- skills/agentsociety-analysis/subagent_prompts/<role>.md
- skills/agentsociety-analysis/references/<doc>.md
- skills/agentsociety-analysis/references/<doc2>.md
- <relevant artifact paths, e.g. paper/figure_specs/fig_x.json>

Inputs:
- workspace = ...
- hypothesis_id = ..., experiment_id = ...
- <other scoped IDs>

Expected output:
- <artifact path or structured verdict>

Done when:
- <one-sentence termination criterion>
```

Never pass:
- The controller's running notes / context.
- Premature opinions about the verdict.
- Cross-experiment information when the subagent's scope is one
  experiment.
