# Results Writing Prompt

This prompt drives the Results section. It is part of the paper-toolkit
skill. The shared discipline (verb ladder, paragraph roles, watch-list,
self-check) lives in `_writing_shared.md` — do not skip it.

## BEFORE drafting — required

1. Read `_writing_shared.md` (Iron Law, stance, BEFORE block).
2. Inspect the evidence graph and get the suggested write order:
   ```
   paper evidence topo-order --workspace <path>
   ```
3. List the figures already registered in the workspace:
   ```
   paper status --workspace <path>
   ```
   Cross-reference with `paper/paper.json` `artifacts.figures`. If a
   needed figure or table is missing, author a spec under
   `paper/figure_specs/<id>.json` or `paper/table_specs/<id>.json`
   (schema: `references/figure_table_specs.md`), then:
   ```
   paper figure render --spec paper/figure_specs/<id>.json --workspace <path>
   paper table render --spec paper/table_specs/<id>.json --workspace <path>
   paper compose pack-figures --workspace <path>
   ```
   The renderers write `paper/figures/<id>.{pdf,tex}` and
   `paper/tables/<id>.tex`; pull them into a section with
   `\input{figures/<id>.tex}` / `\input{tables/<id>.tex}`.
4. Read `references/exemplar_patterns.md`:
   - **Concept-before-Explanatory-Use** when a subsection introduces a new
     measure.
   - **Minimal-Mechanism-Compression** when a subsection bridges from
     pattern to mechanism.
5. If a prior compile exists, inspect findings:
   ```
   paper check figures --workspace <path>
   paper check claim-coverage --workspace <path>
   paper check word-count --section results --workspace <path>
   ```

## Section-Specific Discipline

Results is an argumentative spine, not a chronological lab notebook. Each
`\subsection{...}` should answer **one sub-question** and follow this
internal structure:

1. **Sub-question** — name it. The reader must not have to infer it.
2. **Concept or measure** — if introducing a new construct, define it
   before using it (Pattern 3).
3. **Result paragraph** — calibrated verb, one quantitative anchor
   (effect size, $p$-value, magnitude, sample size) when applicable.
4. **Robustness paragraph** — alternative specifications a reviewer will
   demand.
5. **Qualification paragraph** — bound without retreating.

Subsection order must serve the main claim, not workflow chronology.

## Figure Discipline

Each `\ref{fig:X}` must resolve to a `FigureArtifact` registered in
`paper.json`. The toolkit enforces this; do not maintain a parallel mental
list.

When a figure environment appears in a subsection:
- Caption answers "what does this figure let me conclude?", not "what is
  plotted".
- Float placement: `[tbp]` or `[htbp]`. The figures checker flags `[h!]`
  and `[t]` as `FIGURE_BAD_FLOAT_PLACEMENT`.
- Caption body must not start with "Figure N." — that prefix is rendered
  automatically by LaTeX; `FIGURE_REDUNDANT_CAPTION_PREFIX` will fire.

## Section-Specific Anti-Patterns

- No interpretation. Results state *what happened*; the Discussion states
  *what it means*. Mixing them is a Dimension 6 (Section-Level Control)
  failure.
- No promoted robustness checks. A robustness paragraph stabilizes a
  claim; it does not replace one.
- No "for brevity, we omit ..." for a robustness check the result depends
  on. If it is load-bearing, write it.
- No subsection heading like "Additional analyses" / "Further results";
  the heading must name the question or the result.

## AFTER drafting — required gate

```
paper check style --section results --workspace <path>
paper check word-count --section results --workspace <path>
paper check figures --workspace <path>
paper check citations --workspace <path>
paper check claim-coverage --workspace <path>
```

If `EVD_CLAIM_UNSUPPORTED` fires, go back to the evidence graph:
```
paper evidence add-evidence --id e<N> --source-kind <kind> --source-ref <ref>
paper evidence link --src e<N> --dst c<M> --kind supports
paper evidence validate
```
Do not weaken the prose alone to silence the checker.

## Done When

- All five envelopes above have no `severity: error` issues.
- A skeptical reader can list, after reading Results:
  - every main claim,
  - the figure or statistic that anchors each claim,
  - the robustness specifications each claim has survived,
  - the qualifications each claim carries.

If any of these is unmet, return to the BEFORE block.
