---
name: agentsociety-analysis
description: Use when an experiment run has produced a sqlite.db and the user wants a claim-driven analysis report plus publication-grade charts that the agentsociety-generate-paper skill can consume. Drives the deterministic `paper analysis` CLI while keeping all judgment (claims, narrative, review verdict) in the agent session.
---

# Analysis Toolkit Skill

`paper-toolkit` ships two skills. `agentsociety-generate-paper` writes the
paper. `agentsociety-analysis` produces the inputs the paper consumes: a
claims file, figure specs that render via the same publication-grade
pipeline the paper uses, and a bilingual report Markdown. The
deterministic CLI in this skill is the `paper analysis ...` subgroup;
**no LLM calls land in the toolkit**.

You own every judgment call (what counts as a claim, which evidence
supports it, which chart kind is honest, when the report is ready). The
researcher remains the author of record.

## The Iron Law (analysis)

```
NO CLAIM WITHOUT AN EVIDENCE ROW FROM
  `paper analysis query` OR `profile-table`.
NO FIGURE WITHOUT A FIGURESPEC THAT ROUND-TRIPPED THROUGH
  THE FIGURE-REVIEWER SUBAGENT.
NO RELEASE WITHOUT BILINGUAL FILES MATCHING THE WORKSPACE LANGUAGE.
```

If you cannot point at a profile entry, query result, or figure PDF for
every claim, you do not have evidence; fix the explore stage first. If a
FigureSpec has not been independently reviewed against
`references/figure_publication_contract.md`, do not run `paper figure render`
on it — burning the PDF first wastes the audit trail.

## No phase machine

The workflow has six stages, but they are NOT a flag in `state.yaml`.
Stage is derived from artifacts (see `references/workflow.md`).
`state.yaml` records facts only — claim_count, profiled_tables,
last_query_slug. Never invent fields; never edit it by hand.

## Read-These-First (per task)

| Task | MUST read before acting |
|---|---|
| First time invoking the skill | `references/tool_catalog.md` + `references/workflow.md` |
| Authoring an analysis plan | `references/workflow.md` + `prompts/intake.md` |
| Exploring sqlite tables | `prompts/explore.md` + `references/output_layout.md` |
| Extracting claims | `prompts/claim_extraction.md` + `references/claim_schema.md` |
| Authoring a figure spec | `prompts/figure_emission.md` + `references/figure_publication_contract.md` + `references/figure_contract.md` + `references/chart_qa.md` |
| Producing a report | `prompts/write_report.md` + `references/handoff_to_paper.md` |
| Reviewing a report or chart | `prompts/skeptical_review.md` + `references/analysis_quality.md` |
| Cross-experiment synthesis | `prompts/synthesis.md` |
| Multi-section / multi-experiment runs | `prompts/_subagent_workflow.md` |

Each file is a *required* read for the task it owns. The Read tool must
touch it; do not infer contents from this index.

**This applies mid-flow, not just at trigger time.** When you transition
from one stage to the next, re-Read the new stage's pre-reads even if you
read them an hour ago. The prompts encode the discipline the next step
needs; skimming from memory is how steps get skipped.

## Subagent dispatch — required, not optional

The Iron Law's *figure-reviewer* clause and the producer/reviewer split at
stages 5/6 are NOT suggestions. The following steps MUST be dispatched as
distinct subagents — running them in the controller session is a self-review
and counts as skipping the gate:

| Step | Producer subagent | Reviewer subagent |
|---|---|---|
| Stage 4 — figure spec authoring | `figure-spec-author` | `figure-reviewer` (BEFORE render) |
| Stage 5 — bilingual report | `report-producer` (one per language) | `report-reviewer` |
| Stage 6 — cross-experiment synthesis | `synthesis-producer` | `synthesis-reviewer` |

When dispatching, the controller's prompt to the subagent MUST include
the relevant `references/*.md` + `prompts/*.md` file paths from the
"Read-These-First" table — the subagent starts with empty context and
will not find them otherwise. See `prompts/_subagent_workflow.md` for the
dispatch payload template.

If you find yourself thinking "I'll just review my own draft to save a
round-trip" — STOP. That is the failure mode the producer/reviewer split
exists to prevent.

## Workflow shape (six derived stages)

```
intake -> explore -> claims -> refine -> produce -> synthesis
                                                       |
                                               lift-to-evidence
                                                       v
                                       (agentsociety-generate-paper consumes)
```

| Stage | Toolkit commands (run them; do not narrate them) |
|---|---|
| 1. Frame | `paper analysis init`, write `analysis_plan.yaml`, `paper analysis write-plan`, `paper analysis check-plan` |
| 2. Explore | `paper analysis list-tables`, `paper analysis profile-table`, `paper analysis query`, `paper analysis check-explore` |
| 3. Claims | `paper analysis record-claim` (×N), `paper analysis check-claims` |
| 4. Refine | author FigureSpec under `paper/figure_specs/<id>.json`, `paper figure render`, `paper figure register`, `paper analysis record-figure-contract`, `paper analysis check-refine` |
| 5. Produce | `paper analysis build-report-context`, write `report_zh.md` + `report_en.md`, `paper analysis check-release` |
| 6. Synthesis | `paper analysis build-synthesis-brief`, `paper analysis lift-to-evidence`, `paper analysis check-synthesis` |

`paper analysis status` shows the highest stage each experiment has
cleared. If a check fails, return to the stage it gates and fix the
artifact — do not silence the checker.

## Hard rules

1. **No prose-quality LLM logic in the CLI.** The `check-*` verbs are
   filesystem + schema only. If you find yourself wanting them to
   "evaluate" a claim or paragraph, the judgment belongs in this skill.
2. **Charts inherit the publication-grade renderer in `paper figure
   render`.**
   Author a FigureSpec, then `paper figure render`. Do not write
   matplotlib scripts. The renderer enforces Arial fallback, fonttype 42,
   89/183 mm, and the four built-in palettes — see
   `references/figure_publication_contract.md` for the audit.
3. **One chart per claim, one claim per chart.** A claim with no
   `figure_contract` is incomplete (the Refine stage checker catches it).
   A chart not bound to a claim is decoration; drop it.
4. **The toolkit owns `analysis/<H>/<E>/` and `paper/figure_specs/`.**
   Treat materials outside those as read-only input.
5. **Bilingual matters when the workspace says so.** `check-release`
   reads `config.yaml` (or falls back to `paper.json:meta.language`); do
   not invent a third language or skip one to "finish faster".
6. **Lift before declaring done.** Until you run
   `paper analysis lift-to-evidence`, `paper check claim-coverage` does
   not see the analysis-side claims. The synthesis check fails on
   un-lifted claims by design.

## Common rationalizations

| Excuse | Reality |
|---|---|
| "The chart looks fine; I'll skip the figure-reviewer subagent." | The reviewer enforces palette / column width / font / data-vs-claim alignment. Skipping it means a re-render later, possibly after the chart is in the paper draft. |
| "I'll re-read prompts only at the start of the skill; that's enough." | Each stage has its own pre-reads. Mid-flow Read tool calls are not optional — your context drifts between stages and the prompt encodes the next stage's discipline. |
| "I'll review my own draft to save a subagent round-trip." | Self-review is not review. Stage 4/5/6 reviewers MUST be dispatched as distinct subagents; the controller is not allowed to grade its own work. |
| "I'll write the report first, then backfill claims." | claims.json is the source of truth the report quotes from. Writing the report first invites unsupported assertions that survive the review. |
| "The English report is fine; I'll skip the Chinese version." | `check-release` reads `config.yaml`. If language is `bilingual`, the gate refuses your release. Change the config explicitly if a language really isn't needed. |
| "I don't need to run lift-to-evidence; the agentsociety-generate-paper skill can re-type the claims." | Re-typing is judgment leakage between two skills. The bridge is deterministic; use it. |
| "The query was simple; I didn't save it." | Without a query slug under `eda/queries/`, the claim's `evidence` field is a placeholder. Re-run with `--out` so the artifact exists. |

## Red flags (STOP if you catch yourself thinking)

- "I'll just paste a matplotlib snippet — quicker than authoring a spec."
- "This claim is obviously true; I don't need to query to back it."
- "The checker is being pedantic; I'll skip ahead."
- "I'll mark synthesis claims `deferred` to silence the gate."

ALL of these mean: stop and return to the relevant stage.

## Terminal verification checklist

- [ ] `paper analysis check-plan / check-explore / check-claims /
      check-refine / check-release / check-synthesis` all clean for the
      experiments you intend to release.
- [ ] `paper figure register --spec ...` ran for every registered
      figure (`paper.json:artifacts.figures[]` contains them).
- [ ] `paper analysis lift-to-evidence` ran for every experiment whose
      claims feed the paper.
- [ ] `paper check claim-coverage` is clean on the paper workspace.

Can't check all boxes? You skipped a stage. Return to it.

## Quick-start loop (concrete commands)

```text
paper init --title "..." --venue nature --workspace .
paper analysis init --hypothesis-id h1 --experiment-id e1 \
                    --db /path/to/sqlite.db --workspace .

# author analysis_plan.yaml from the intake prompt, then:
paper analysis write-plan --hypothesis-id h1 --experiment-id e1 \
                          --payload analysis_plan.yaml --workspace .
paper analysis check-plan --hypothesis-id h1 --experiment-id e1 --workspace .

paper analysis list-tables --db /path/to/sqlite.db --workspace .
paper analysis profile-table --db ... --table agent_status \
                             --hypothesis-id h1 --experiment-id e1 --workspace .
paper analysis query --db ... --sql "SELECT tick, AVG(x) FROM agent_status GROUP BY tick" \
                     --hypothesis-id h1 --experiment-id e1 --workspace .
paper analysis check-explore --hypothesis-id h1 --experiment-id e1 --workspace .

paper analysis record-claim --hypothesis-id h1 --experiment-id e1 \
                            --claim-id growth --text "..." \
                            --kind quantitative --evidence agent_status_profile \
                            --workspace .
paper analysis check-claims --hypothesis-id h1 --experiment-id e1 --workspace .

# author paper/figure_specs/fig_growth.json (figure-spec-author + figure-reviewer subagents)
paper figure render --spec paper/figure_specs/fig_growth.json --workspace .
paper figure register --spec paper/figure_specs/fig_growth.json --workspace .
paper analysis record-figure-contract --hypothesis-id h1 --experiment-id e1 \
                                      --claim-id growth --figure-id fig_growth \
                                      --rationale "comparison bar" --workspace .
paper analysis check-refine --hypothesis-id h1 --experiment-id e1 --workspace .

paper analysis build-report-context --hypothesis-id h1 --experiment-id e1 --workspace .
# author report_zh.md and report_en.md under analysis/h1/e1/
paper analysis check-release --hypothesis-id h1 --experiment-id e1 --workspace .

paper analysis build-synthesis-brief --hypothesis-id h1 --experiment-id e1 --workspace .
paper analysis lift-to-evidence --hypothesis-id h1 --experiment-id e1 --workspace .
paper analysis check-synthesis --hypothesis-id h1 --workspace .

paper check claim-coverage --workspace .
```
