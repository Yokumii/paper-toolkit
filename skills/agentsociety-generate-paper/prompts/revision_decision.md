# Revision Decision Prompt

After a `skeptical_review.md` pass, after a `paper compile-once` run, or
after `paper check all`, this prompt turns findings into the next
concrete action(s). It is the router between *what is wrong* and *what
to do about it*. This prompt is part of the paper-toolkit skill; toolkit
commands referenced below are the real fix mechanism.

## The Iron Law (revision)

```
NO PROSE PATCH FOR AN EVIDENCE FAILURE.
NO BATCH FIX WITHOUT A PER-ISSUE ENTRY IN paper/reviews/revision-r<N>.md.
```

If a checker flagged the evidence graph (`EVD_CLAIM_UNSUPPORTED`,
`EVD_DAG_CYCLE`, `LOGIC_CONTRADICTORY_CLAIMS`), the prose is downstream;
fix the graph. If you make multiple fixes in one round without recording
each, the next reviewer cannot audit progress.

## BEFORE deciding — required

1. Read the latest review: `paper/reviews/skeptical-r<N>.md`.
2. Read the latest compile output: `paper/compile_runs/r<N>/run.json`.
3. Read every relevant check report. If none have been run since the
   review or compile, run:
   ```
   paper check all --workspace <path>
   ```
4. Read prior decisions: `paper/reviews/revision-r*.md`. Avoid undoing an
   intentional past choice.
5. If the action might touch evidence: read
   `paper/evidence_graph.json`.

## Stance

Decide the smallest revision that resolves the issues without weakening
evidence-backed claims. You are not patching prose to silence checkers;
you are choosing between *local edits*, *structural moves*, *conceptual
moves*, and *human-gate escalations*.

The researcher is the author of record and the final arbiter of `major`
and `fatal` decisions.

## Revision Classes (with explicit toolkit map)

### 1. Local revision
**Covers**: wording, paragraph logic, transitions, single figure captions,
citation key fixes, em-dash replacement.

**Triggered by**: `severity: minor` issues; `STYLE_BANNED_PUNCT`,
`STYLE_BANNED_PHRASE` (error severity), `CITE_MISSING_BIB_ENTRY` (fix is
just adding a known reference); compile errors with `code: syntax`.

**Toolkit map**:
- Edit `paper/sections/<name>.tex` directly.
- Re-run: `paper check style --section <name> --workspace <path>` (or
  `paper check citations --workspace <path>` if citation fix).
- If a citation needed adding: `paper evidence add-citation` →
  `paper compose write-bib`.

**Policy**: auto-execute. Record one line in
`paper/reviews/revision-r<N>.md`.

### 2. Structural revision
**Covers**: claim order, figure order, subsection reorganization,
paragraph splitting/merging, sentence-to-sentence flow inside a paragraph.

**Triggered by**: `severity: major` with reroute `paragraph` or `section`;
`FIGURE_DUPLICATE_ENV`; `WC_OUT_OF_RANGE` requiring cuts/expansion not
solvable by local edits; compile errors with `not in outer par mode` or
float-placement issues.

**Toolkit map**:
- Edit `paper/sections/<name>.tex` (move text between paragraphs/
  subsections).
- For figure ownership: edit `paper.json` figure list (or re-run
  `paper compose pack-figures` if source figures changed).
- Re-run: `paper check word-count`, `paper check figures`, `paper
  compile-once`.

**Policy**: auto-execute, but record the before/after structure in the
revision note for auditability.

### 3. Conceptual pivot
**Covers**: paper angle adjustment, contribution type restatement,
re-prioritization of which claim is `primary`, evidence-strategy change.

**Triggered by**: `severity: major` with reroute `evidence` or `framing`
that does not change the research question; Dimension 2 issues asserting
multiple unintegrated contributions; Dimension 7 issues with pervasive
overclaim; `EVD_DAG_CYCLE`; `LOGIC_CONTRADICTORY_CLAIMS`.

**Toolkit map**:
- For framing: edit `intro.tex` first; ripple to `abstract.tex` and
  `discussion.tex`.
- For evidence-strategy: run `paper evidence rm-node` / `add-claim` /
  `link` then `paper evidence validate`.
- For claim strength changes: re-create the claim with the new
  `--strength` (the schema validates).
- Re-run: `paper compose write-bib` (if citation set changed),
  `paper compose assemble-latex`, `paper compile-once`, `paper check all`.

**Policy**: auto-execute *but log explicitly*. Write the rationale and
the before/after of the contribution statement (or affected claim node)
into the revision note. The researcher may override.

### 4. Major conceptual pivot — human gate
**Covers**: research-question rewrite, hypothesis rewrite, major new
experimental direction, abandoning a main claim.

**Triggered by**: `Verdict: FATAL`; any `severity: fatal` issue with
reroute `framing` or `evidence` that requires new data or invalidates a
prior main claim; the reviewer's "Human gate recommended: YES" line.

**Toolkit map**:
- *Do not edit any section file or evidence node until the researcher
  has decided.*
- Write `paper/reviews/human-gate-r<N>.md` containing:
  - What the reviewer found.
  - Which option(s) the researcher could take.
  - The minimum information you need from the researcher to proceed.
- Tell the user explicitly. Stop.

**Policy**: **do not auto-execute.**

## Priority Order

When the review surfaces multiple issues, address them in this order:

1. `fatal` issues that require a human gate (write the gate note and stop).
2. `fatal` issues that do not require a human gate (return to evidence
   graph or framing; do not edit downstream sections yet).
3. `major` `evidence` reroutes (the DAG must stabilize before any
   downstream prose).
4. `major` `framing` reroutes that you can resolve without new data.
5. `major` `section` and `paragraph` reroutes.
6. `major` `figure-plan` reroutes.
7. `major` `wording` reroutes (rare; usually wording is `minor`).
8. All `minor` issues, in any order.

Within each tier, issues that block other issues come first. A claim
that fails Dimension 3 (Claim-Evidence Alignment) often makes a
Dimension 7 (Significance Calibration) issue moot; fix Dimension 3 first.

## Decision Output

Append one line per resolved issue to `paper/reviews/revision-r<N>.md`:

```
- [issue ref] -> [revision class] -> [reroute] -> [what was changed] -> [verifier command]
```

Example:
```
- skeptical-r1#issue-3 -> local revise -> wording -> downshifted "shows" to "supports" in results.tex paragraph 4 -> paper check style --section results
- skeptical-r1#issue-1 -> conceptual pivot -> framing -> restated contribution from "new mechanism" to "new measure" in intro.tex paragraphs 4-5 -> paper compose assemble-latex && paper compile-once
- skeptical-r1#issue-5 -> human gate -> evidence -> see paper/reviews/human-gate-r1.md (Wave 2 replication needed)
```

The `verifier command` is the toolkit command that confirms the fix; if
you cannot name one, the fix is not done.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll fix all 6 minor issues in one edit." | Fine, but the revision note still needs one entry per issue. Auditability is what makes the loop reviewable. |
| "Promoting this `major` to `fatal` triggers a human gate I don't need." | Severity comes from the review pass, not from convenience. If the human gate is unnecessary, the rubric will produce `major`, not `fatal`. |
| "The checker will catch it next round; I'll move on." | The checker may catch the same issue with a different `code`. Fix it now or record an explicit deferral. |
| "The evidence graph is `fine enough`; I'll patch the prose." | Iron Law. If a checker flagged the evidence, the prose patch is rearranging deck chairs. |
| "I already know the priority order; I'll skip the rubric." | The rubric is calibrated to the rubric reroutes. Skipping it means inventing your own priorities, which the next reviewer cannot audit. |
| "Auto-execute this conceptual pivot without logging — the change is small." | Conceptual pivots without logs are how research drift looks like progress. Log every one. |

## Red Flags

If you catch yourself thinking:

- "The issue says `evidence`, but a quick prose edit fixes it."
- "The reviewer was too strict; I'll demote this to `minor`."
- "Both these issues hit the same paragraph; I'll merge the entries."
- "I'll skip the verifier command this once."
- "The human-gate option seems like overkill; I'll auto-execute."

**ALL of these mean: STOP. Re-read the review's `severity` and `suggested_
reroute` fields. The rubric verdict overrides convenience.**

## Loop Termination

Stop the revision loop when:
- All `fatal` issues are either resolved or gated to the human.
- Every `major` issue has an explicit revision entry (auto-executed or
  gated).
- `minor` issues are either addressed or deferred (one-line deferral note
  with reason).

Then re-run the deterministic floor:

```
paper check all --workspace <path>
paper compile-once --workspace <path>
```

If a new round of issues appears, repeat the review → revision-decision
cycle. The toolkit does not enforce a maximum loop count; the researcher
decides when the manuscript is done.

## Done When

- The revision note at `paper/reviews/revision-r<N>.md` has one line per
  issue from the review note, each with a `verifier command`.
- The verifier commands have been run and their envelopes show no new
  `severity: error` issues introduced by the fixes.
- Any human-gate notes (if applicable) are written and the user has been
  told explicitly.

If any of these is unmet, the revision pass is not done.
