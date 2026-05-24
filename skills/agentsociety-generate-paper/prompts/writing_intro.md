# Introduction Writing Prompt

This prompt drives the Introduction section. It is part of the paper-toolkit
skill. The shared discipline (verb ladder, paragraph roles, watch-list,
self-check) lives in `_writing_shared.md` — do not skip it.

## BEFORE drafting — required

1. Read `_writing_shared.md` (Iron Law, stance, BEFORE block).
2. Read `references/exemplar_patterns.md`. Pick one pattern:
   - **Stakes-to-Gap** (default for empirical / measurement papers)
   - **Progress-to-Trade-off** (when refining or bounding a progress wave)
   - **Concept-before-Explanatory-Use** (when the gap is not legible
     without the new construct)
   Record the choice as a one-line comment at the top of `intro.tex`:
   ```latex
   % pattern: stakes-to-gap
   ```
3. Inspect the evidence graph for claims tied to the introduction:
   ```
   paper evidence topo-order --workspace <path>
   ```
   Identify the citation nodes that anchor the gap.
4. If `TOPIC.md` exists in the workspace, read it for the user's
   stakes-framing intent.
5. If a prior compile exists, inspect last-round findings:
   ```
   paper check style --section intro --workspace <path>
   paper check word-count --section intro --workspace <path>
   paper check citations --workspace <path>
   ```

## Section-Specific Discipline

The introduction does five things, in this order, with one paragraph each
(stakes may take two paragraphs; nothing else does):

1. **Stakes** — name the concrete cost of not knowing.
2. **Gap** — state why prevailing accounts cannot resolve the question.
3. **Question** — compress stakes and gap into one precise question.
4. **Approach** — name the specific move that makes the question
   decidable.
5. **Contribution** — state the contribution type (empirical pattern,
   mechanism, measure, method, implication) and the single main claim.

Build pressure, then narrow.

## Section-Specific Anti-Patterns

(Additions to the shared list.)

- No literature *review* in paragraph 1. Stakes come first; citations
  appear only where they pin down the gap.
- Each citation must do argumentative work in its paragraph. Read-the-
  references-and-find-where-they-fit drafting produces literature dumps.
- The contribution statement must name the contribution type. "We provide
  insights into ..." is not a contribution type.

## AFTER drafting — required gate

```
paper check style --section intro --workspace <path>
paper check word-count --section intro --workspace <path>
paper check citations --workspace <path>
```

If `CITE_MISSING_BIB_ENTRY` fires, either add the citation node via
`paper evidence add-citation` then `paper compose write-bib`, or fix the
citation key in prose. Do not silently delete `\cite{}` macros to silence
the checker.

## Done When

- All three envelopes above have no `severity: error` issues.
- A skeptical reader can state, after reading the introduction:
  - the stakes (one sentence),
  - the gap with at least one specific reason existing work fails (one
    sentence),
  - the question (one sentence),
  - the approach (one sentence),
  - the contribution type and the single main claim (one sentence).

If any of these is unmet, return to the BEFORE block. Do not advance to
Results until the introduction is done; results paragraphs that interpret
themselves are a sign of a half-built introduction.
