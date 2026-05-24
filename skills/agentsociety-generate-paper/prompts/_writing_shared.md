# Shared Writing Primitives

Every section overlay (`writing_intro.md`, `writing_results.md`, ...) extends
this file. Read this **and** the section overlay before drafting.

## The Iron Law (writing)

```
NO PROSE BEFORE EVIDENCE. NO VERB STRONGER THAN THE EVIDENCE EARNS.
```

If a claim has no evidence node (or only an unsupported one), fix the
evidence graph first via `paper evidence add-evidence / link / validate`.
Do not patch the prose with hedging to dodge `EVD_CLAIM_UNSUPPORTED`. If the
verb-calibration ladder downshifts a claim, the *whole paragraph* moves with
it; you cannot quietly leave a weaker verb in one sentence and a stronger
implication in the next.

## Stance

You are drafting an artifact that must withstand rigorous, evidence-oriented
review from skeptical, impatient, high-status readers. You are assisting the
researcher; they remain the author of record.

The deterministic checks in `paper-toolkit` (style, citations, figures,
claim-coverage, word-count, logic-consistency) score correctness. This
prompt scores argumentative discipline. Do not duplicate what the checkers
already enforce; let them run and *react to the envelope*.

Core rule: **do not write to sound impressive; write to make a difficult
argument feel inevitable.**

## BEFORE drafting — required reads and commands

Run these in order. The Read tool must touch each file; do not infer
contents.

1. Read `references/exemplar_patterns.md`. Pick at most one pattern as the
   section's primary control logic.
2. Read the section overlay (`writing_<section>.md`) that called you here.
3. Inspect the evidence graph:
   ```
   paper evidence topo-order --workspace <path>
   ```
   The topo order tells you which claims your section must support and in
   what dependency order.
4. Inspect the venue word range and style rules:
   ```
   paper status --workspace <path>
   ```
   The envelope shows the active venue. If you need the rules verbatim,
   read `paper/venue.yaml` (or fall back to the bundled
   `venues/<venue>.yaml`).
5. If a prior compile run exists, read its `run.json` to see what failed
   last time:
   ```
   paper page count --run r<N> --workspace <path>
   ```

If any of these reads or commands is skipped, you are guessing about the
artifact's state. STOP and run them.

## Non-Negotiable Constraints

1. Do not turn weak evidence into strong language.
2. Do not turn observation into mechanism unless evidence warrants it.
3. Do not turn correlation into causation unless evidence warrants it.
4. Do not include every available result; keep only what advances the main
   line.
5. Do not use significance language without specifying *what* is
   significant, *to whom*, and *why*.
6. Do not smooth over uncertainty for the sake of elegance.
7. Figures behave like argumentative steps, not illustrations.
8. One dominant function per paragraph.

The deterministic style checker enforces a subset of these (em-dash,
"in this paper we propose", AI-tone phrases, "replacing the researcher"
framing). When the checker flags one, do not argue with the rule; downshift
the prose or — if you genuinely believe the warning is wrong — record an
override decision in `paper/reviews/revision-r<N>.md` with the reason.

## Paragraph Roles

One role per paragraph. Hold it. (Vocabulary used by `skeptical_review.md`
Dimension 10.)

- **stakes** — name the concrete cost of not knowing.
- **gap** — show why existing work cannot resolve it.
- **question** — compress stakes and gap into one precise question.
- **concept** / **measure** — define the new construct before using it.
- **result** — answer one sub-question with specific evidence.
- **robustness** — show the result survives alternative specifications.
- **qualification** — bound the result without retreating from it.
- **implication** — enlarge meaning without overreaching.

Avoid repeated internal reversals (`however ... yet ... but ... still ...`).

## Verb-Calibration Ladder

Choose the *weakest* verb that still truthfully captures the evidence:

| Verb | When to use |
|---|---|
| `shows` | Direct empirical demonstration with adequate power. |
| `demonstrates` | When the demonstration *is* the contribution. |
| `supports` | Consistent with the claim and inconsistent with main rivals. |
| `indicates` | Consistent with the claim; rivals not ruled out. |
| `suggests` | Pattern present; inferential chain is long. |
| `is consistent with` | Compatible reading among other compatible readings. |
| `cannot rule out` | Used to bound a competing interpretation. |

Inflated words (`important`, `novel`, `powerful`, `transformative`,
`reveals`, `establishes`, etc.) are not banned, but they must be earned by
adjacent evidence *in the same paragraph*. The style checker warns on these
via `venues/nature.yaml`; read its output rather than re-deriving the list
here.

## Inter-Paragraph Flow

Each transition must perform one of: **narrowing**, **building**,
**substantiating**, **qualifying**, **expanding**. Decorative transitions
(`Moreover`, `Furthermore`) without one of these functions are signs of
weak structure.

## AFTER drafting — required commands

In this order. Do not skip steps because "the edits were small".

1. `paper check style --section <name> --workspace <path>`
2. `paper check word-count --section <name> --workspace <path>`
3. If the section cites: `paper check citations --workspace <path>`
4. If the section references figures: `paper check figures --workspace <path>`
5. If the section advances any claim: `paper check claim-coverage --workspace <path>`

For each error in the envelope:
- Map it to the rubric via `references/review_rubric.md` ("Pre-Review
  Quick Pass" table).
- Fix the underlying problem (the evidence graph, the bib file, or the
  prose, in that order of priority).
- Re-run the same check. Do not move on until the envelope is clean of
  errors. Warnings require a judgment + a one-line note.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The watch-list word is appropriate here." | Maybe. Either earn it with adjacent evidence in the same paragraph, or override the rule in `paper/venue.yaml` (durable) with a one-line reason. Silent overrides leak across sessions. |
| "The verb is fine; the reviewer is being pedantic." | The ladder is calibrated to the evidence node behind the claim. If the verb feels strong, the evidence is probably weaker than you think; check the source node, then downshift. |
| "I'll fix the section-overlay-specific issue without re-reading this file." | The shared primitives evolve with venue config and project memory. Re-read this file each session. |
| "The compile output is recent enough." | Each section edit invalidates the previous compile. Re-run before reviewing. |

## Red Flags

If you catch yourself thinking:

- "I know the watch-list by heart; I don't need to read it."
- "The check command is too slow; I'll skip it this round."
- "The evidence node is roughly right; I'll fix the prose to match."
- "This paragraph has two roles, but they're related."
- "The verb is one notch above the evidence, but the qualification later
  handles it."

**ALL of these mean: STOP. Re-run the relevant `paper check` command, then
fix the underlying issue.**

## After-Drafting Output

Save only:

- the section file: `paper/sections/<name>.tex`.

Do **not** save:
- ad-hoc planning files (`*-draft-notes.md`, `*-scratch.md`, etc.) — the
  toolkit does not parse them and they will rot.
- a copy of the prompts you read — they already live in `skills/agentsociety-generate-paper/`.

The next step is either the next section (back to the section overlay) or
the review pass (read `prompts/skeptical_review.md`).
