# Abstract Writing Prompt

This prompt drives the Abstract section. It is part of the paper-toolkit
skill. The shared discipline (verb ladder, paragraph roles, watch-list,
self-check) lives in `_writing_shared.md` — do not skip it.

## BEFORE drafting — required

1. Read `_writing_shared.md` (Iron Law, stance, BEFORE block).
2. Read `paper/evidence_graph.json`. Identify which claims are
   `strength: primary` — the abstract's "what we find" beat must match
   one of them.
3. Read `paper/sections/results.tex` and `paper/sections/discussion.tex`
   if they exist. The abstract cannot promise what those sections do not
   deliver.
4. If a prior compile exists, inspect the last abstract pass:
   ```
   paper check style --section abstract --workspace <path>
   paper check word-count --section abstract --workspace <path>
   ```
   Fix the underlying issues that flagged last time before redrafting.

## Section-Specific Discipline

The abstract is a five-move pressure curve, in this order:

1. **Why this matters** — concrete stakes-bearing situation.
2. **What is not yet understood** — the gap.
3. **What we do** — the move (measurement, model, experiment, theory)
   that makes the gap decidable.
4. **What we find** — the result with calibrated verbs and one
   quantitative anchor when applicable.
5. **What follows from it** — one bounded implication.

Each move is one or two sentences. Compression *is* the discipline.

The exemplar patterns in `references/exemplar_patterns.md` (especially
Stakes-to-Gap and Concept-before-Explanatory-Use) inform moves 1→2 and 3→4
respectively, but they do not transfer wholesale; the abstract is too
compressed to hold a two-paragraph pattern.

## Section-Specific Anti-Patterns

These are *abstract-specific* additions to the shared `_writing_shared.md`
list:

- No citations in the abstract unless the venue requires them; default is
  no citations.
- No method jargon before the gap is named.
- No "future work" sentence in the implication beat; the implication is
  what *this* paper enables, not what *another* paper might.

## AFTER drafting — required gate

```
paper check style --section abstract --workspace <path>
paper check word-count --section abstract --workspace <path>
```

If either envelope has `severity: error` issues, fix them before declaring
the abstract done. Warnings (AI-tone phrases) require a one-line judgment
in `paper/reviews/skeptical-r<N>.md` if you keep them.

## Done When

- The envelope from `paper check style --section abstract` has no
  `severity: error` issues.
- The envelope from `paper check word-count --section abstract` reports
  the section within the venue range (Nature default: 150–200 words).
- A skeptical reader can state in one sentence each: the problem, the
  gap, the move, the result (with verb-ladder-correct strength), and
  one bounded implication.

If any of these is unmet, return to the BEFORE block.
