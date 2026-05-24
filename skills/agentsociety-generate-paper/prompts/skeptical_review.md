# Skeptical Review Prompt

Run this prompt against a draft section (or full manuscript) to attack it
as a rigorous, evidence-oriented top-journal reviewer would. This prompt is
part of the paper-toolkit skill; deterministic findings come from the
toolkit CLI and are the *floor* of the review.

## The Iron Law (review)

```
NO HUMAN-JUDGMENT REVIEW BEFORE `paper check all` HAS RUN ON THE CURRENT DRAFT.
NO ISSUE WITHOUT AN EVIDENCE-FROM-TEXT QUOTE OR POINTER.
```

If `paper check all` has not run since the last edit, the review will
re-derive findings the checkers already produced. Do not waste tokens on
that. Run the checks, ingest the envelopes, then spend tokens on what the
checkers cannot judge (Dimensions 1, 2, 4, 7).

If you cannot point to specific text (file path + paragraph N or exact
quote), the issue is too vague to be actionable; you have not earned the
right to flag it.

## BEFORE reviewing — required

1. Run the deterministic floor:
   ```
   paper check all --workspace <path>
   paper compile-once --workspace <path>     # if not already current
   ```
2. Read the latest compile output:
   ```
   paper page count --run r<N> --workspace <path>
   paper page overflow --run r<N> --workspace <path>
   ```
3. Read the target artifact: `paper/sections/<name>.tex` (or `main.tex`
   for a full-manuscript review).
4. Read the argument backbone: `paper/evidence_graph.json`.
5. Read prior reviews: `paper/reviews/skeptical-r*.md` — avoid re-raising
   issues already accepted or already resolved.
6. Read the rubric cheatsheet: `references/review_rubric.md`. Keep it
   open during the review.

## Stance

Critique the argument, not the author's intentions. Prefer specific
attacks over general impressions. Fluency is suspicious unless backed by
structure and evidence. You are assisting the researcher; they remain the
author of record and the final arbiter of `major` and `fatal` decisions.

Core rule: **do not reward writing for sounding strong; reward it only if
its language, structure, and implications are fully earned.**

## Internal Review Order

Run silently before writing the review:

1. What is the paper trying to claim?
2. What kind of contribution is it claiming to make?
3. Which claims are central, and which are decorative?
4. Which central claims are not fully supported?
5. Run Layer 1 review first (Dimensions 1–7).
6. If Layer 1 reveals `fatal` or clearly upstream problems, focus there;
   do not polish prose on top of a broken argument.
7. Only if the artifact is basically defensible at Layer 1, run Layer 2
   review (Dimensions 8–11), and *only* on issues the deterministic style
   checker did not already flag.
8. Distinguish *local* wording problems from problems requiring rerouting
   to framing, evidence, figure-plan, or section architecture.

## Layer 1 (judgment-heavy)

These dimensions are where the human-judgment review earns its keep. The
checkers cannot judge these.

For each, see `references/review_rubric.md` for the **Ask** and **Flag
when** entries:

- **Dimension 1 — Problem Framing**
- **Dimension 2 — Contribution Discipline**
- **Dimension 3 — Claim-Evidence Alignment**
  Floor: `paper check claim-coverage` (`EVD_CLAIM_UNSUPPORTED`),
  `paper check citations` (`CITE_MISSING_BIB_ENTRY`).
- **Dimension 4 — Alternative Explanations**
- **Dimension 5 — Figure-Argument Logic**
  Floor: `paper check figures` (`FIGURE_*`).
- **Dimension 6 — Section-Level Control**
  Floor: `paper check word-count`.
- **Dimension 7 — Significance Calibration**

## Layer 2 (checker-led)

For Layer 2, the deterministic style checker has already flagged:
em-dash, "in this paper we propose", "replacing the researcher", and 25
AI-tone phrases (warning severity). **Do not re-derive these.** Read the
`paper check style` envelope and treat each finding as a Dimension 8
candidate. The human-judgment portion of Layer 2 is:

- **Dimension 8 — Word-Level Precision**: judge whether each AI-tone
  warning is earned by adjacent evidence in the same paragraph. If yes,
  record an override in the review note; if no, mark `required_action:
  downshift`.
- **Dimension 9 — Sentence-to-Sentence Logic**
- **Dimension 10 — Paragraph Logic and Flow** (paragraph-role failures
  the toolkit cannot detect)
- **Dimension 11 — Local Readability**

## Severity, Verdict, Reroute

(Verbatim from `references/review_rubric.md`.)

Severity: `minor` | `major` | `fatal`.
Verdict: `PASS` | `REVISE` | `FATAL`.
Reroute: `wording` | `paragraph` | `section` | `figure-plan` | `evidence`
| `framing`.

Pick the *smallest* reroute that addresses the issue. Do not send a
wording problem back to framing.

## Per-Issue Schema (mandatory)

Each issue **must** carry all six fields, or the issue is dropped.

```yaml
- dimension: <1-11>
  severity: <minor | major | fatal>
  why_it_matters: <one or two sentences>
  evidence_from_text: <exact quote or file:line / paragraph N pointer>
  required_action: <concrete change>
  suggested_reroute: <wording | paragraph | section | figure-plan | evidence | framing>
```

The `evidence_from_text` field is the gate. If you cannot quote or point,
do not raise the issue.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I already know what `paper check style` will say." | Then reading the envelope costs nothing. Read it; it may have changed. |
| "The deterministic floor is paranoid; I'll skip running it." | Skipping is how false-positive judgments get baked in. The floor is the floor for a reason. |
| "I can describe the issue without quoting." | Then the author cannot find it. Quote or do not raise. |
| "This is a `major` issue but escalation costs energy." | Severity comes from the rubric, not from convenience. Promote it; the revision step will decide auto-execute vs. human gate. |
| "Layer 2 issues are easy; I'll bundle them at the end." | Each Layer 2 issue needs a `required_action` and a reroute; bundling loses the per-issue map. |

## Red Flags

If you catch yourself thinking:

- "The check command output is too long; I'll skim."
- "The issue is obvious; I don't need to quote."
- "This looks like overclaim, but I can't put my finger on why."
- "Layer 1 is fine; let me start polishing prose."
- "The previous reviewer raised this; I'll skip it."
- "Verdict `PASS` even though one `major` issue remains — the researcher
  will catch it next round."

**ALL of these mean: STOP. Re-run the relevant `paper check` command and
read its output before raising the issue.**

## Output Format

Save the review as `paper/reviews/skeptical-r<N>.md` where `<N>` matches
the compile-run index of the artifact under review.

```
# Skeptical Review (round N) — <artifact>

- Review order applied: Layer 1 only | Layer 1 then Layer 2
- Verdict: PASS | REVISE | FATAL
- Highest severity: minor | major | fatal
- Most-frequent reroute: <target>
- Deterministic floor read: <paths to envelopes/run.json consulted>

## Summary
<one short paragraph>

## Issues
- Issue 1: <one-line title>
  - dimension: ...
  - severity: ...
  - why_it_matters: ...
  - evidence_from_text: ...
  - required_action: ...
  - suggested_reroute: ...
- Issue 2: ...

## Strengths worth preserving
- Strength 1
- Strength 2

## Human gate recommended: YES | NO
Rationale (if yes): ...

## Unresolved risks
- Risk 1
- Risk 2
```

## Done When

- Every issue has all six schema fields filled.
- Every `severity: fatal` issue has either a reroute or a human-gate flag.
- The verdict matches the issues: `PASS` only with `minor` issues;
  `REVISE` if any `major` issue remains; `FATAL` if any `fatal` issue
  remains.
- The review note is saved to `paper/reviews/skeptical-r<N>.md`.

Then hand off to `prompts/revision_decision.md`.
