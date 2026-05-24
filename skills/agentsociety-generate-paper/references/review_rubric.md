# Review Rubric Cheatsheet

Compact reference card for the 11-dimension review rubric. Use this during a
review pass to make sure no dimension is skipped; the full prompt and per-issue
schema live in `prompts/skeptical_review.md`.

Two-layer model: **Layer 1 first** (argument and evidence). Run Layer 2
(language and flow) only if Layer 1 is basically defensible.

## Layer 1 — Argument and Evidence (7 dimensions)

| # | Dimension | Ask | Flag when |
|---|---|---|---|
| 1 | Problem Framing | Is there a real high-stakes question with a sharply defined gap? | introduction stays broad too long; gap is generic; question is diffuse; paper sounds important without specifying why |
| 2 | Contribution Discipline | What is the actual contribution type? Single or multiple? | novelty asserted but not specified; contribution shifts across sections; claims mechanism when only pattern; implication > finding |
| 3 | Claim-Evidence Alignment | Does each main claim have adequate support? Verbs calibrated? | strong verbs exceed support; caveats missing/delayed/buried; robustness absent where the claim depends on it |
| 4 | Alternative Explanations | What would a skeptical reader say instead? | manuscript behaves as if one interpretation is self-evident; obvious alternatives ignored; interpretive space closed too early |
| 5 | Figure-Argument Logic | Does each figure earn its place in the argument? | figures feel decorative; order reflects workflow not persuasion; a later figure does work an earlier figure should have done |
| 6 | Section-Level Control | Does this section do what it is supposed to do? | introduction reads like a literature dump; results reads like a chronological lab notebook; discussion introduces unearned claims |
| 7 | Significance Calibration | Underclaiming, overclaiming, or correctly calibrated? | significance is generic; jumps to policy/field meaning too quickly; timid where the paper has earned a strong implication |

## Layer 2 — Language and Flow (4 dimensions)

| # | Dimension | Ask | Flag when |
|---|---|---|---|
| 8 | Word-Level Precision | Are verbs and qualifiers calibrated to the evidence? | inflated words (`important`, `novel`, `powerful`, `transformative`, `reveals`, `demonstrates`, `establishes`) used without earning them |
| 9 | Sentence-to-Sentence Logic | Does each sentence follow from the last? | hidden leap from result to implication; adjacent sentences without a clear argumentative relation; ornamental transitions |
| 10 | Paragraph Logic and Flow | One dominant function and direction? | paragraph starts as context and ends as interpretation; multiple major turns (`however ... yet ... but ...`); reader must reconstruct the function after the fact |
| 11 | Local Readability | Readable under its density? | technically correct but hard to traverse; local repetition dulls momentum; abstract phrasing could be replaced with a precise formulation |

## Severity Tiers

| Severity | Definition | Typical handling |
|---|---|---|
| `minor` | Local wording, transition, paragraph-cleanup. | Author edits in place; no rerouting. |
| `major` | Weakens interpretation, structure, or support. | Reroute to the responsible layer; may auto-execute. |
| `fatal` | Breaks the paper angle, invalidates a major claim, or requires returning to an earlier phase. | Reroute upstream; may require human gate. |

## Verdict States

- `PASS` — artifact basically defensible; only `minor` issues remain.
- `REVISE` — at least one `major` issue, or many `minor` ones; revision required
  before the next compile cycle.
- `FATAL` — at least one `fatal` issue; do not patch around it.

## Reroute Targets

Pick the *smallest* reroute that addresses the issue. Do not send wording
problems back to framing; do not mask framing problems as wording problems.

- `wording` — local phrase or verb replacement; same paragraph stays.
- `paragraph` — restructure or split a paragraph; section stays.
- `section` — reorder or rewrite a section; overall narrative stays.
- `figure-plan` — change figure assignments, order, or design.
- `evidence` — add, replace, or strengthen evidence in the DAG before redrafting.
- `framing` — reconsider stakes, gap, contribution type, or paper angle.

## Per-Issue Schema

Each issue in a review note must contain all five fields:

```yaml
issue:
  dimension: <one of 1-11>
  severity: <minor | major | fatal>
  why_it_matters: <one or two sentences>
  evidence_from_text: <exact quote or precise pointer>
  required_action: <concrete change to make>
  suggested_reroute: <one of wording | paragraph | section | figure-plan | evidence | framing>
```

The `evidence_from_text` field is mandatory — vague criticism is unactionable
and breaks the rubric's contract.

## Inflated-Vocabulary Watch-List

Flag in Dimension 8 unless the surrounding evidence earns the word:

`important`, `novel`, `powerful`, `transformative`, `reveals`, `demonstrates`,
`establishes`, `groundbreaking`, `paradigm shift`, `unprecedented`, `crucial`,
`pivotal`.

Note: the deterministic style checker already warns on many of these via
`venues/nature.yaml`. The review pass adds the per-paragraph judgment of
whether adjacent evidence earns the word.

## Pre-Review Quick Pass

Before the human-readable review, run the deterministic checks and treat their
output as the floor, not the ceiling:

```
paper check all --workspace <path>
```

Map deterministic findings into the rubric:

| Checker code | Maps to dimension |
|---|---|
| `CITE_MISSING_BIB_ENTRY`, `CITE_UNUSED_BIB_ENTRY` | 3 (Claim-Evidence Alignment) |
| `FIGURE_UNREFERENCED`, `FIGURE_UNRESOLVED_REF`, `FIGURE_DUPLICATE_ENV` | 5 (Figure-Argument Logic) |
| `FIGURE_REDUNDANT_CAPTION_PREFIX`, `FIGURE_BAD_FLOAT_PLACEMENT` | 5 + 11 |
| `STYLE_BANNED_PUNCT`, `STYLE_BANNED_PHRASE` (severity: error) | 8 (Word-Level Precision) |
| `STYLE_BANNED_PHRASE` (severity: warning, AI-tone) | 8 (Word-Level Precision) |
| `WC_OUT_OF_RANGE` (section too long/short) | 6 (Section-Level Control) |
| `EVD_CLAIM_UNSUPPORTED` | 3 + 7 |

Reviewer judgment is still required for every dimension; the checks just front-
load the mechanical findings so the human-judgment portion of the review can
focus on the argumentative dimensions.
