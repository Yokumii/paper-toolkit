# Discussion Writing Prompt

This prompt drives the Discussion section. It is part of the paper-toolkit
skill. The shared discipline (verb ladder, paragraph roles, watch-list,
self-check) lives in `_writing_shared.md` — do not skip it.

## BEFORE drafting — required

1. Read `_writing_shared.md` (Iron Law, stance, BEFORE block).
2. Read the just-completed `paper/sections/results.tex` *and* any
   `paper/reviews/skeptical-r*.md` that reviewed results. Discussion
   builds on Results; it does not retell it.
3. Inspect the evidence graph:
   ```
   paper evidence topo-order --workspace <path>
   ```
   The Discussion may use claims of any `strength` but **must not** add a
   new central claim with no evidence support.
4. Read `references/exemplar_patterns.md`:
   - **Minimal-Mechanism-Compression** when bridging from observed pattern
     to mechanism.
   - **Progress-to-Trade-off** when positioning against an external
     progress narrative.
5. Inspect last-round findings:
   ```
   paper check logic-consistency --workspace <path>
   paper check word-count --section discussion --workspace <path>
   ```

## Section-Specific Discipline

Discussion has three moves, in this order:

1. **What was learned** — compressed claim statement naming the
   contribution type, with the strongest verb the evidence earns.
2. **What it means** — be **ambitious in implication** but **conservative
   in inference**. Do not slide from `supports` (Results) to `shows`
   (Discussion).
3. **What it does not yet mean** — limitations, bounded scope, and
   alternative interpretations a skeptical reviewer will raise.

A fourth move, "what is next", is optional and short. Only include it if
the next step is specific enough to be falsifiable.

## Section-Specific Anti-Patterns

- No retelling of Results. The Discussion integrates Results into a
  contribution claim; it does not summarize them paragraph by paragraph.
- No new findings. New findings belong in Results.
- No causal language unless Results carried the causal argument (design +
  evidence + alternatives ruled out).
- No vague "future work" as a soft place to park scope you cannot defend.
- No vague limitations. A vague limitation is unactionable for a reviewer.
  Each limitation must specify the scope-bound and the reason.

## The Inflation Trap

The Discussion is where overclaim is most attractive. Run the style
checker output before declaring the draft done; it will flag the AI-tone
watch-list as warnings. For each warning, either:
- earn the word with specific adjacent evidence in the same paragraph, or
- downshift to a verb-ladder-correct equivalent.

If you keep an inflated word, record the override in
`paper/reviews/revision-r<N>.md` with the one-line reason.

## AFTER drafting — required gate

```
paper check style --section discussion --workspace <path>
paper check word-count --section discussion --workspace <path>
paper check citations --workspace <path>
paper check logic-consistency --workspace <path>
```

A `LOGIC_CONTRADICTORY_CLAIMS` finding here is a strong signal: the
Discussion may be reversing a Results claim. Audit before accepting.

## Done When

- All four envelopes above have no `severity: error` issues.
- A skeptical reader can state, after reading the Discussion:
  - the contribution type and main claim with the verb-ladder-correct
    verb,
  - one bounded, falsifiable implication,
  - at least two specific limitations,
  - at least one specific alternative explanation with how the paper
    addresses it.

If any of these is unmet, return to the BEFORE block.
