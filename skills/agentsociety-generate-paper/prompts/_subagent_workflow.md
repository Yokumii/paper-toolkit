# Subagent-Driven Workflow (controller-side guide)

Use this workflow when drafting or revising a manuscript with paper-toolkit
and you want to:

- Keep the controller's context clean (drafter / reviewer / router each have
  isolated context).
- Run roles in parallel where possible (e.g., two independent sections after
  the evidence graph is stable).
- Enforce role separation: the drafter never reviews its own prose; the
  reviewer never sees the drafter's planning trace.

## When to Use This Mode vs. Direct Mode

| Situation | Use this (subagent-driven) | Use direct mode |
|---|---|---|
| Drafting ≥3 sections | yes | no |
| Drafting one tiny section, small fixes | no | yes |
| Skeptical review of an already-drafted manuscript | yes | only if you must |
| Single-paragraph revision after a `minor` finding | no (overkill) | yes |
| Researcher wants audit trail per role | yes | no |
| Cost is tightly bounded | no | yes |

Direct mode is what `SKILL.md` describes as the default loop. This file
adds the subagent-driven alternative; the controller picks per task.

## The Iron Law (workflow)

```
NO SUBAGENT INHERITS THE CONTROLLER'S CONTEXT.
NO ROLE REVIEWS ITS OWN OUTPUT.
NO PARALLEL DISPATCH OF CONFLICTING WRITERS.
```

- Every subagent gets exactly what it needs via the payload; no "you'll
  figure it out from context" hand-waves. If the drafter needs the
  evidence DAG, the controller pastes the topo order into the payload.
- The drafter that wrote `intro.tex` never reviews `intro.tex`. Always
  dispatch a fresh subagent for review.
- Two drafter subagents cannot edit the same section file in parallel.
  Sections that share state (e.g., abstract depends on results) must be
  drafted serially.

## The Four Roles

### 1. Drafter
**Inputs (paste into payload)**:
- Section name (`intro`, `results`, ...).
- Workspace path.
- Pattern choice from `references/exemplar_patterns.md`.
- Evidence DAG snapshot (output of `paper evidence topo-order`).
- Pinned constraints from the venue and from prior reviews (e.g., "do
  not change the contribution statement; the framing was fixed in r2").
- The path to the section overlay (e.g.,
  `skills/agentsociety-generate-paper/prompts/writing_intro.md`).

**Job**: read `_writing_shared.md` and the section overlay; draft
`paper/sections/<name>.tex`; run the AFTER checks; return a `DraftReport`.

**Return**:
```yaml
status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
section: <name>
artifact: paper/sections/<name>.tex
pattern_used: <stakes-to-gap | progress-to-trade-off | ...>
after_checks_run:
  - paper check style --section <name>: <error_count, warning_count>
  - paper check word-count --section <name>: <error_count, warning_count>
  - paper check ...
concerns: <list>
```

### 2. Spec Reviewer (Stage 1)
**Inputs**: section file path, section overlay path, the `DraftReport`,
all relevant `paper check ... --section <name>` envelopes.

**Job**: confirm the draft satisfies the overlay's discipline contract
(pressure curve, paragraph roles, declared pattern, "Done When"). This is
*not* a content critique; it is a structural-conformance check.

**Return**:
```yaml
verdict: SPEC_PASS | SPEC_FAIL
findings:
  - dimension: <pattern-conformance | move-coverage | done-when | paragraph-role>
    item: <which discipline item failed>
    evidence_from_text: <quote or paragraph N>
    required_fix: <concrete>
```

If `SPEC_FAIL`, the controller re-dispatches the **same drafter** with
the findings appended to its payload — never a new drafter (which would
lose pattern context).

### 3. Skeptical Reviewer (Stage 2)
**Only dispatch after `SPEC_PASS`.**

**Inputs**: section file path (or full `main.tex` for a full-manuscript
pass), evidence graph, all check envelopes, prior review notes
(`paper/reviews/skeptical-r*.md`).

**Job**: read `prompts/skeptical_review.md` and `references/review_rubric.md`;
run the 11-dimension rubric; return a `ReviewNote`.

**Return**: the `ReviewNote` schema from `skeptical_review.md` (verdict +
issues with all six per-issue fields). Save to
`paper/reviews/skeptical-r<N>.md`.

### 4. Revision Decider
**Dispatch after Stage 2 returns `REVISE` or `FATAL`.**

**Inputs**: the `ReviewNote`, all check envelopes, the latest
`run.json`, prior revision notes.

**Job**: read `prompts/revision_decision.md`; map each issue to a
revision class; emit a `RevisionPlan`.

**Return**:
```yaml
revision_plan:
  - issue_ref: skeptical-r<N>#issue-K
    class: local | structural | conceptual | major_human_gate
    reroute: wording | paragraph | section | figure-plan | evidence | framing
    action: <concrete instruction the next drafter or the controller will execute>
    verifier_command: paper check ...
human_gate_required: true | false
human_gate_note_path: paper/reviews/human-gate-r<N>.md   # if required
```

Save the plan to `paper/reviews/revision-r<N>.md`.

## Parallelization Rules

After the evidence DAG is stable (`paper evidence validate` clean) and
before the first compile, **two drafter subagents may run in parallel
when**:

- Their target sections do not share a `\input` or import dependency.
- Neither has been flagged by a prior review for cross-section consistency
  issues.

Typical parallel-safe sets:
- `methods` + `intro` after the DAG is built.
- `methods` + `results` (Methods describes the procedure, Results uses it;
  they coordinate only via Methods's measure definitions, which are pinned
  by the evidence graph).

**Never parallel**:
- `discussion` with anything (depends on Results being final).
- `abstract` with anything (depends on Results and Discussion being final).
- Any pair where one section's content can change a `\cite{}` or
  `\ref{fig:X}` the other section also uses.

When dispatching in parallel, send all the Agent tool calls in a single
message (per the platform's parallel-dispatch rule).

## The Per-Section Loop (one section, serial)

```
controller.dispatch(drafter, payload(intro)) ->
  DraftReport: DONE / SPEC_PASS pending

controller.dispatch(spec_reviewer, payload(intro)) ->
  verdict: SPEC_PASS | SPEC_FAIL

if SPEC_FAIL:
  controller.dispatch(drafter, payload(intro) + findings) -> retry
  ...

controller.dispatch(skeptical_reviewer, payload(intro)) ->
  ReviewNote saved to paper/reviews/skeptical-r1.md
  verdict: PASS | REVISE | FATAL

if REVISE or FATAL:
  controller.dispatch(revision_decider, payload(review_note)) ->
    RevisionPlan saved to paper/reviews/revision-r1.md
  for each entry in plan:
    if class in (local, structural):
      controller.dispatch(drafter, payload(intro) + action) -> apply fix
    elif class == conceptual:
      controller edits evidence_graph.json directly via `paper evidence ...`
    elif class == major_human_gate:
      controller writes human_gate note, tells user, STOPS

controller.runs: paper check all && paper compile-once
controller.repeats loop until verdict == PASS with only minor issues
```

## Status Handling

| Status | Controller action |
|---|---|
| `DONE` | Proceed to Stage 1 review. |
| `DONE_WITH_CONCERNS` | Read concerns. If they affect correctness, address before review. If they are observations ("this section is now near the upper word range"), note and proceed. |
| `NEEDS_CONTEXT` | The drafter needs information not in the payload. Provide it; re-dispatch. Common gap: missing evidence node detail, missing prior-review constraint. |
| `BLOCKED` | (a) Context problem: provide more, re-dispatch same model. (b) Reasoning problem: re-dispatch with a more capable model. (c) Task too large: split (e.g., one Results sub-question per dispatch). (d) Plan is wrong: escalate to the researcher. |

**Never** force the same model to retry an identical payload without a
change. If the drafter said it is stuck, something must change.

## Payload Templates (controller copies these)

### Drafter payload

```
Agent tool (general-purpose):
  description: "Draft <section> section"
  prompt: |
    You are the drafter subagent for paper-toolkit. Draft the <section>
    section of the manuscript.

    ## Workspace
    <absolute path>

    ## Section
    <section name, e.g., intro>

    ## Discipline (MUST READ before drafting)
    1. <workspace>/skills/agentsociety-generate-paper/prompts/_writing_shared.md
    2. <workspace>/skills/agentsociety-generate-paper/prompts/writing_<section>.md
    3. <workspace>/skills/agentsociety-generate-paper/references/exemplar_patterns.md (for pattern
       choice — read only if pattern is not pre-chosen below)

    ## Pattern (chosen by controller)
    <stakes-to-gap | progress-to-trade-off | concept-before-explanatory-use
     | minimal-mechanism-compression | none>

    ## Evidence DAG snapshot
    <paste output of `paper evidence topo-order --workspace <path>`>

    ## Pinned constraints
    <list any constraints from prior reviews; e.g., "framing fixed in r2;
     do not change contribution statement">

    ## Your Job
    1. Read the discipline files.
    2. Draft paper/sections/<section>.tex.
    3. Run the AFTER checks listed in writing_<section>.md.
    4. Return a DraftReport.

    Do NOT skip the BEFORE / AFTER blocks in the section overlay. Do NOT
    invent context that is not pasted above. If anything is missing,
    return NEEDS_CONTEXT.
```

### Spec-reviewer payload

```
Agent tool (general-purpose):
  description: "Spec-conformance review of <section>"
  prompt: |
    You are the spec-reviewer subagent for paper-toolkit. Confirm the
    draft satisfies its overlay's discipline contract.

    ## Workspace
    <absolute path>

    ## Section
    <section name>

    ## Inputs to read
    1. <workspace>/paper/sections/<section>.tex (the draft)
    2. <workspace>/skills/agentsociety-generate-paper/prompts/writing_<section>.md (the overlay)
    3. The check envelopes pasted below.

    ## Check envelopes (paste verbatim)
    <paste each `paper check ... --section <section>` envelope output>

    ## Your Job
    For each discipline item in the overlay's "Section-Specific Discipline"
    and "Done When" lists, verify the draft satisfies it. Report
    SPEC_PASS or SPEC_FAIL. If SPEC_FAIL, list each failing item with
    evidence_from_text + required_fix.

    Do NOT critique argument quality (that is Stage 2). Do NOT polish
    prose. You are checking conformance to the discipline contract only.
```

### Skeptical-reviewer payload

```
Agent tool (general-purpose):
  description: "Skeptical review of <section> (round N)"
  prompt: |
    You are the skeptical-reviewer subagent for paper-toolkit. Run the
    11-dimension rubric.

    ## Workspace
    <absolute path>

    ## Target artifact
    <workspace>/paper/sections/<section>.tex
    (or <workspace>/paper/main.tex for full-manuscript review)

    ## Discipline (MUST READ)
    1. <workspace>/skills/agentsociety-generate-paper/prompts/skeptical_review.md
    2. <workspace>/skills/agentsociety-generate-paper/references/review_rubric.md

    ## Inputs to read
    1. <workspace>/paper/evidence_graph.json
    2. The latest <workspace>/paper/compile_runs/r<N>/run.json
    3. All <workspace>/paper/reviews/skeptical-r*.md (prior reviews)
    4. The check envelopes pasted below

    ## Check envelopes (paste verbatim)
    <paste `paper check all` output>

    ## Your Job
    Run Internal Review Order. Emit a ReviewNote following the per-issue
    schema. Save to <workspace>/paper/reviews/skeptical-r<N>.md.

    Do NOT skip the deterministic floor. Do NOT raise an issue without
    evidence_from_text.
```

### Revision-decider payload

```
Agent tool (general-purpose):
  description: "Revision routing for round <N>"
  prompt: |
    You are the revision-decider subagent for paper-toolkit. Convert the
    review note into a RevisionPlan.

    ## Workspace
    <absolute path>

    ## Discipline (MUST READ)
    1. <workspace>/skills/agentsociety-generate-paper/prompts/revision_decision.md

    ## Inputs to read
    1. <workspace>/paper/reviews/skeptical-r<N>.md
    2. <workspace>/paper/compile_runs/r<N>/run.json
    3. All <workspace>/paper/reviews/revision-r*.md (prior decisions)
    4. <workspace>/paper/evidence_graph.json (if any reroute is `evidence`
       or `framing`)

    ## Your Job
    For each issue in the review note, classify the revision (local /
    structural / conceptual / major_human_gate), pick the smallest
    reroute, and name the action + verifier command. Save the plan to
    <workspace>/paper/reviews/revision-r<N>.md.

    Do NOT auto-execute conceptual or major_human_gate items. Those go
    back to the controller for explicit execution.
```

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The drafter just finished; I'll let it review its own work." | A drafter that just wrote `shows` will not flag itself for picking `shows` over `supports`. Dispatch a fresh subagent. |
| "The skeptical review is enough; I can skip spec-review." | Stage 1 catches "wrong pattern used" / "missing pressure-curve move" cheaply, before paying for a full rubric. Skip it and Stage 2 will surface the structural failure as a Dimension 6 issue, costing more tokens. |
| "I'll dispatch four drafters in parallel for all four sections." | Discussion depends on Results being final; abstract depends on both. Parallel only the genuinely independent pair. |
| "The controller can just read the section overlay itself." | Sometimes. But for ≥3 sections, role isolation outpays the overhead. |
| "Subagent dispatch is slower; I'll do it all in direct mode." | Slower per section, but the review verdicts are higher quality and the audit trail (review-r<N>.md, revision-r<N>.md) is automatic. For full-paper runs, the round-trip cost is smaller than re-drafting after a missed `fatal`. |

## Red Flags

- "I'll skip Stage 1 because the deterministic checks already ran."
- "The drafter's `DONE_WITH_CONCERNS` was minor; I'll ignore it."
- "Two drafters in parallel will figure it out via the toolkit."
- "The reviewer can read the controller's planning notes if it needs context."

**ALL of these mean: STOP. Construct an explicit payload; respect role
isolation; re-dispatch a fresh subagent.**

## Done When

The full-paper subagent-driven run is done when:

- Every section file has been drafted by a drafter and passed Stage 1.
- The most recent Stage 2 review has verdict `PASS` with only `minor`
  issues, OR the researcher has explicitly accepted residual `major`
  issues via a revision-r<N>.md entry.
- `paper check all` and `paper compile-once` have been re-run since the
  last edit; envelopes are clean.
- The Terminal Verification Checklist in `SKILL.md` passes.
