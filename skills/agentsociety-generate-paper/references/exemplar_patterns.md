# Exemplar Patterns

Four named control patterns for opening, framing, and compression moves in a
high-impact manuscript. Use them as logic templates, not as surface style to
mimic. Each pattern has a short description, a compressed inline example, what
makes it work, and the anti-patterns to avoid.

The patterns are adapted from the paper-harness writing design and from
classic mobility / scientific-impact exemplars; they are deliberately
domain-neutral so they transfer.

---

## Pattern 1: Stakes-to-Gap

**Use when**: opening the Introduction; sometimes used as the first move of an
Abstract.

**Shape**:
- Paragraph 1 — **stakes**: name a concrete societal or scientific cost of
  not knowing the answer.
- Paragraph 2 — **gap**: state precisely why prevailing accounts cannot
  resolve the stakes-bearing question.

**Inline example** (compressed):

> P1 (stakes): "Human mobility shapes epidemics, cities, and infrastructure,
> yet prevailing stochastic accounts describe population dispersion more
> convincingly than individual regularity."
>
> P2 (gap): "We therefore ask whether individual trajectories are sufficiently
> structured to reveal reproducible behavioral laws."

**Why it works**:
- Starts broad, narrows fast — the reader feels the stakes before learning
  the technical question.
- The gap is *specific*: "describes dispersion more than regularity", not
  "more work is needed".
- The transition (`yet`) does logical work: it splits what is known from what
  is not.

**Anti-patterns** (do not use):
- "X has attracted considerable attention" — establishes interest, not stakes.
- "Much remains unknown about X" — gap without specificity.
- "In this paper, we propose ..." as the second move — bypasses the gap.
- Opening with the method, dataset, or model name before motivating it.

**Quality bar**: a reader who closes the paper after the second paragraph
should already be able to state the question and why it matters.

---

## Pattern 2: Progress-to-Trade-off

**Use when**: framing work that responds to a wave of recent advances; useful
in Introduction and Discussion to position the contribution against an
otherwise-optimistic narrative.

**Shape**:
- Paragraph 1 — **progress**: name what recent work has plausibly achieved.
- Paragraph 2 — **trade-off**: surface a cost or tension that the progress
  story has not yet priced in.
- Pivot — name the measurement, experiment, or theoretical move that
  separates the gain from the cost.

**Inline example** (compressed):

> P1 (progress): "AI tools appear to broaden scientific capability by
> accelerating prediction and publication."
>
> P2 (trade-off): "Yet those same tools may concentrate collective attention
> on the problems richest in data."
>
> Pivot: "We therefore separate individual gains from collective narrowing."

**Why it works**:
- Frames a *tension*, not a flat result; the paper has a reason to exist
  beyond piling on additional evidence.
- The pivot sentence promises the analytical move that makes the tension
  decidable, not a generic "we investigate".
- Avoids dismissing prior work: the trade-off is a refinement, not a refutation.

**Anti-patterns**:
- Setting up a strawman ("prior work has ignored X") when prior work has
  treated X partially or differently.
- A tension paragraph that ends without naming the move that resolves it.
- Using `however` to introduce a tension that is not actually present in the
  cited literature.

**Quality bar**: by the end of the pivot, the reader can state which two
quantities you will separate, even if they do not yet know the metric.

---

## Pattern 3: Concept-before-Explanatory-Use

**Use when**: the paper introduces a new measure, construct, or operationalization
and then uses it to compare or explain. Almost always belongs in Methods or
the early Results; sometimes in late Introduction.

**Shape**:
- Step 1 — **conceptual need**: explain why an existing measure is
  insufficient *for this particular argument*.
- Step 2 — **definition**: introduce the new construct precisely, with its
  inputs and what it returns.
- Step 3 — **only then**: use it to compare, predict, or explain.

**Inline example** (compressed):

> Step 1 (need): "Citation counts capture visibility but not the character of
> contribution."
>
> Step 2 (definition): "We therefore distinguish work that redirects later
> attention from work that consolidates existing lines, and operationalize that
> distinction as a normalized disruption index over the first $k$ citing
> works."
>
> Step 3 (use): "Using this index, we compare teams of different sizes."

**Why it works**:
- Prevents *metric arbitrariness*: the reader sees why a new measure is
  needed before being asked to trust it.
- Defines the measure in one sentence so the explanatory use can be terse.
- Keeps the conceptual move separable from the empirical move, so reviewers
  can attack one without attacking the other.

**Anti-patterns**:
- Inventing a metric in the middle of a Results paragraph.
- Defining a measure with examples instead of inputs/outputs.
- Reusing a name from prior literature with a modified definition without
  flagging the modification.

**Quality bar**: a skeptical reader can write down the formula or the
operational rule for the measure from the definition step alone.

---

## Pattern 4: Minimal-Mechanism-Compression

**Use when**: bridging from observed heterogeneity or scaling pattern to a
proposed mechanism; almost always in Discussion or late Results, occasionally
in late Introduction.

**Shape**:
- Step 1 — **acknowledge the pattern**: state the empirical regularity without
  yet calling it explained.
- Step 2 — **reject descriptive overload**: refuse the temptation to list
  every plausible contributor.
- Step 3 — **compress to minimal mechanism**: ask which smallest set of
  mechanisms is *necessary* to reproduce the pattern.

**Inline example** (compressed):

> Step 1: "The observed heterogeneity across users is striking and reproducible."
>
> Step 2: "It is not, by itself, an explanation."
>
> Step 3: "The productive question is which minimal set of mechanisms is
> necessary to reproduce the pattern without importing the full complexity
> of the system."

**Why it works**:
- Refuses descriptive overload — explicitly distinguishes pattern from
  explanation.
- Compresses *toward* mechanism, signalling the move from phenomenon to model.
- Creates a clean bridge that a downstream paragraph can fill with the
  candidate mechanism set.

**Anti-patterns**:
- Listing every potentially relevant variable as if listing were the same as
  modeling.
- Claiming mechanism when the evidence supports only co-occurrence.
- Using "mechanism" rhetorically without specifying what reproduces what.

**Quality bar**: after the compression step, the reader expects a specific
minimal set; the next paragraph (or section) should deliver exactly that set.

---

## How the Section Prompts Use These Patterns

- `writing_intro.md` — recommends Pattern 1 for the open, Pattern 2 as an
  alternative when the field is in an active progress wave, Pattern 3 if the
  Introduction must define a new construct before the gap is legible.
- `writing_results.md` — recommends Pattern 3 when a new measure precedes its
  empirical use; Pattern 4 when a results subsection bridges to mechanism.
- `writing_discussion.md` — recommends Pattern 4 when consolidating findings
  into mechanism; Pattern 2 when positioning against an external progress
  narrative.
- `writing_abstract.md` — does not adopt these patterns wholesale; the
  pressure curve is more constrained. The patterns can inform the choice of
  what to put in the "what is not yet understood" beat.

When using a pattern, name it explicitly in a one-line comment at the top of
the section file so reviewers can check whether the pattern's quality bar was
met. Example:

```latex
% pattern: stakes-to-gap (paragraph 1 stakes, paragraph 2 gap, pivot in para 3)
\section{Introduction}
...
```
