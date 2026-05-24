---
name: agentsociety-generate-paper
description: Use when a research workspace has analysis outputs and the user wants to write, revise, check, compile, or review an academic paper with paper-toolkit. Drives deterministic CLI tools while keeping all writing, judgment, review, and revision decisions in the agent session.
---

# Paper Toolkit Skill

`paper-toolkit` is a deterministic Python CLI (no LLM calls). This skill
directs Claude Code through writing, review, and revision while the CLI
handles all reproducible operations: workspace state, evidence DAG, figure
packing, BibTeX writing, LaTeX assembly, compile, and six checkers.

You own every judgment call (what to claim, which evidence supports it,
review severity, revision class). The researcher remains the author of
record; this skill assists them, it does not replace them.

## The Iron Law

```
NO PROSE PATCHES FOR EVIDENCE OR STRUCTURE FAILURES.
NO RELEASE CLAIM WITHOUT A FRESH `paper check all` AND `paper compile-once`.
```

If `paper check claim-coverage` or `paper check citations` is failing, fix
the evidence graph or refs.bib *before* touching section prose. If the
deterministic checks have not been re-run since the last edit, you cannot
claim the paper is ready. Skipping these steps is not a shortcut; it is a
lie about state.

## Read-These-First (per task)

Each prompt and reference is a *required* read for the task it owns, not a
"see also" link. Open them with the Read tool, do not infer their contents
from this index.

| Task | MUST read before acting |
|---|---|
| Drafting any section | `prompts/_writing_shared.md` + `prompts/writing_<section>.md` |
| Picking an opening pattern | `references/exemplar_patterns.md` |
| Authoring a figure or table spec | `references/figure_table_specs.md` |
| Searching arXiv / CrossRef / OpenAlex | `references/literature_search.md` |
| Skeptical review | `prompts/skeptical_review.md` + `references/review_rubric.md` |
| Revision decision | `prompts/revision_decision.md` |
| Running a multi-section / multi-round project | `prompts/_subagent_workflow.md` |
| First time using a command | `references/tool_catalog.md` |
| Inspecting an envelope | `references/envelope_schema.md` |
| Reading a `run.json` | `references/compile_run_schema.md` |
| Reading a `CheckReport` | `references/check_report_schema.md` |
| Inspecting the evidence DAG | `references/evidence_graph_schema.md` |

The Red Flags section below lists the "I don't need to read it" thoughts
that mean you do.

## Execution Modes

Two modes; the controller picks per task.

**Direct mode** (default for small tasks): the controller CC reads the
discipline prompts and drives the toolkit itself. Cheapest, least
ceremony. Right for single-section edits and small revision rounds.

**Subagent-driven mode** (recommended for full-paper runs and multi-
section drafting): the controller dispatches fresh subagents per role
(drafter, spec-reviewer, skeptical-reviewer, revision-decider) so each
role has isolated context. Right for ≥3 sections or any review round
where role separation matters. See `prompts/_subagent_workflow.md` for
the full role contracts, payload templates, parallelization rules, and
status handling.

Iron Law of mode selection: do not switch modes mid-loop. If you started
a section's draft → review → revise cycle in subagent-driven mode,
finish it in subagent-driven mode; do not let the controller "just fix
it directly" partway through (loses the audit trail).

## Workflow Shape (not a phase machine)

A *recommended sequence*. You may reorder when a section is already mature,
or when a review finding sends the work back to an earlier step.

```
intake -> framing -> evidence DAG -> drafting
                                        |
release <- revision <- skeptical review <- compile + checks
```

| Step | Toolkit commands (run these — do not narrate them) |
|---|---|
| 1. Intake | `paper init`, `paper scan` |
| 2. Framing | (judgment — produces no toolkit artifact yet) |
| 3. Evidence DAG | `paper evidence add-claim/add-evidence/add-citation/link/validate`, `paper evidence topo-order` |
| 4. Drafting | `paper template expand --section <name>`, then edit `paper/sections/<name>.tex` |
| 5. Compile + checks | `paper compose pack-figures`, `paper compose write-bib`, `paper compose assemble-latex`, `paper compile-once`, `paper check all` |
| 6. Skeptical review | (LLM judgment; output to `paper/reviews/skeptical-r<N>.md`) |
| 7. Revision decision | (LLM judgment; output to `paper/reviews/revision-r<N>.md`) |
| 8. Release | (LLM judgment, communicate to user) |

Loop 4 → 5 → 6 → 7 until verdict is `PASS` with only `minor` issues
remaining, or until the researcher closes the loop.

## The Deterministic Floor

These checks are the **floor** of review, not the ceiling. Run them and
treat each finding as an input to the human-judgment review, not as a
finding you re-derive.

| Command | Replaces what kind of judgment |
|---|---|
| `paper check style` | em-dash, "in this paper we propose", 25 AI-tone phrases (warning), "replacing the researcher" framing (error). Do not re-list these rules in prose; read the checker output. |
| `paper check citations` | every `\cite\|\citep\|\citet\|\citealt\|\citealp\|\citeauthor\|\citeyear` in sections vs. refs.bib. |
| `paper check figures` | unreferenced figures, redundant `Figure N.` caption prefix, bad float placement, duplicate `\label{}` across sections. |
| `paper check claim-coverage` | orphan evidence, unsupported primary claims. |
| `paper check word-count` | sections outside the venue word range. |
| `paper check logic-consistency` | contradicting claims linked by a `contradicts` edge. |
| `paper compile-once` | LaTeX errors and warnings, with `LatexError.file` attributed to the source `.tex`. |

Map deterministic findings into the rubric using `references/review_rubric.md`
**before** spending tokens on Dimensions 1, 2, 4, 7 (which are pure judgment).

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "This section is short, I don't need an envelope after editing." | Every section edit must be followed by `paper check style --section X` and `paper check word-count --section X`. The envelope is the only record that the change was actually clean. |
| "The figure is obvious; I'll skip the evidence node." | A claim without an evidence node is invisible to `paper check claim-coverage`. The reviewer will catch it; the toolkit catches it first. |
| "The AI-tone warning is a false positive; I'll override." | Maybe. But override in the `paper/venue.yaml` (which is durable) or note it in the review file. Do not silently leave the warning unfixed and unjustified. |
| "The previous compile run is recent enough; I won't re-run." | If you edited a `.tex` file after `r<N>`, the previous run is stale. Re-run before claiming a verdict. |
| "I already read SKILL.md; I don't need to re-read the prompt." | SKILL.md is a router. The prompt files carry the discipline. Read them. |
| "The verb ladder is in my head; I don't need `_writing_shared.md`." | The ladder evolves with the venue config. Read the file each session. |
| "The review found one major issue; I'll batch the fix with three minor ones." | `paper/reviews/revision-r<N>.md` must record each fix separately for auditability. Batching is the enemy of monotonic progress. |
| "Citations are unused; I'll delete them from refs.bib." | An unused citation may belong to a deferred claim. Decide first, prune second; ask the researcher if unsure. |

## Red Flags (STOP if you catch yourself thinking)

- "I'll write the section first, then build the evidence graph."
- "The deterministic checker is too picky; I'll just keep going."
- "This review note is too detailed; I'll summarize and re-derive later."
- "The reviewer flagged it as `fatal`, but it's really just wording."
- "I don't need to re-run `paper check all`; my edits were small."
- "The watch-list is paranoid; this paper is meant to be ambitious."
- "I'll fix the prose to silence the checker."
- "The user did not ask for a review pass; the draft is good enough."

**ALL of these mean: STOP. Return to the relevant step in the Workflow Shape
table above.**

## Terminal Verification Checklist

Before reporting "the paper is ready" or "this section is done", confirm
every box. If you cannot, you skipped a step.

- [ ] `paper compile-once` has been re-run since the last edit; latest
      `run.json` shows `ok: true`.
- [ ] `paper check all` has been re-run since the last edit; report has
      no errors (warnings are explicitly judged and recorded).
- [ ] Every claim node with `strength: primary` has a supporting evidence
      node (verify with `paper check claim-coverage`).
- [ ] Every `\cite{}` key in every section exists in `refs.bib` (verify
      with `paper check citations`).
- [ ] Every figure referenced in prose has a packed file in
      `paper/figures/` and a `FigureArtifact` in `paper.json` (verify with
      `paper check figures`).
- [ ] The latest review note at `paper/reviews/skeptical-r<N>.md` has
      verdict `PASS` with only `minor` issues, or the researcher has
      explicitly accepted remaining `major` issues with a note in
      `paper/reviews/revision-r<N>.md`.
- [ ] Word counts for all sections are within the venue range (verify
      with `paper check word-count`).

Can't check all boxes? You skipped the deterministic floor. Return to step 5.

## Hard Rules

1. **No phase machine.** Read each command envelope's `state_summary`;
   decide next from artifacts + user intent + review notes.
2. **The toolkit owns `paper/`.** Materials outside `paper/` are read-only
   inputs.
3. **Evidence graph is the source of truth for claims.** If a checker
   flags an unsupported claim, fix the graph (add a node, add a link,
   weaken the claim's strength) before patching prose.
4. **Severity and verdict come from the review pass.** The revision step
   may not promote `major` to `fatal` for convenience or demote `fatal` to
   `major` to avoid a human gate.
5. **Frame the system as assisting, not replacing.** The style checker
   enforces this at error severity; do not argue with it.
6. **No em-dash (`---`) in prose.** The style checker enforces this.
7. **Communicate the loop to the user.** After each compile or review
   round, report the verdict, the highest-severity issue, and the chosen
   reroute target.

## Quick-Start Loop (concrete commands)

```text
paper init --title "..." --venue nature --workspace .
paper scan --workspace .

paper evidence add-claim --id c1 --label "..." --section intro --strength primary
paper evidence add-evidence --id e1 --label "..." --source-kind figure --source-ref fig1
paper evidence add-citation --id ref1 --cite-key levy2021 --label "..."
paper evidence link --src e1 --dst c1 --kind supports
paper evidence validate
paper evidence topo-order

# For each section the topo order suggests:
paper template expand --section intro --workspace .
# Read prompts/_writing_shared.md, then prompts/writing_intro.md.
# Edit paper/sections/intro.tex.
paper check style --section intro --workspace .
paper check word-count --section intro --workspace .

paper compose pack-figures --workspace .
paper compose write-bib --workspace .
paper compose assemble-latex --workspace .
paper compile-once --workspace .
paper check all --workspace .

# Read prompts/skeptical_review.md.
# Save review to paper/reviews/skeptical-r1.md.
# Read prompts/revision_decision.md.
# Save decisions to paper/reviews/revision-r1.md.
# Apply revisions and loop.
```
