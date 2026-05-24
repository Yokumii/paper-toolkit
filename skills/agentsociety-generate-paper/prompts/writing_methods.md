# Methods Writing Prompt

This prompt drives the Methods section. It is part of the paper-toolkit
skill. The shared discipline (verb ladder, paragraph roles, watch-list,
self-check) lives in `_writing_shared.md` — do not skip it. **Note**:
Methods optimizes for *reproducibility* over argumentative tension; the
verb-ladder applies but the reader is a skeptical replicator, not a
general reader.

## BEFORE drafting — required

1. Read `_writing_shared.md` (Iron Law, stance, BEFORE block).
2. Read `paper/research_pack.json` to see what the scanner found
   (replay databases, analysis reports, datasets).
3. Inspect the evidence graph:
   ```
   paper evidence topo-order --workspace <path>
   ```
   Every evidence node with `source.kind ∈ {figure, table, stat, qual}`
   should have its production method described in Methods. Every measure
   used in Results should have its operational definition here.
4. If `init_config.json` / `steps.yaml` exist in the workspace root, read
   them; Methods documents simulation setup *exactly*.
5. Inspect last-round findings:
   ```
   paper check style --section methods --workspace <path>
   paper check word-count --section methods --workspace <path>
   ```

## Section-Specific Discipline

Subsections follow the analytical pipeline:

1. **Setup** — population, environment, agents, parameters, random seeds.
2. **Intervention or condition** — what varied across conditions, exactly
   how.
3. **Measurement** — operational definitions for every measure used in
   Results: formulas where applicable, units, computation windows.
4. **Analysis** — statistical model(s), inclusion/exclusion criteria,
   missing-data handling, multiple-comparison treatment.
5. **Robustness** — alternative specifications and what they tested.
6. **Reproducibility** — code, data, replay database paths, software
   versions.

Each measure follows **Concept-before-Explanatory-Use** (Pattern 3):
define before use, inputs and outputs explicit, formula if applicable,
then a one-sentence motivation if it is not the standard formulation.

## Section-Specific Anti-Patterns

- No narrative claims in Methods. Methods records what was done; it does
  not interpret outcomes.
- No evidential verbs (`shows`, `supports`, ...) in Methods; use
  operational verbs (`compute`, `sample`, `assign`, `treat`, `aggregate`).
- No citations for ornamentation. Cite for published procedures or
  rejected alternatives, not for general topic awareness.
- No important methodological choices hidden in supplementary material
  when they affect interpretation of a main claim.
- No raw Unicode math (`×`, `≤`, `α`); use LaTeX equivalents (`\times`,
  `\leq`, `\alpha`). The style checker flags these via the unicode-character
  fixup hint.

## Pseudocode and Equations

For any non-standard procedure (loop, branching policy, update rule),
include pseudocode or a numbered equation. Pseudocode is preferred over
prose for procedures. Use `\begin{algorithm}` (requires `algorithm`
package; the toolkit's `paper compose assemble-latex` loads it on demand).

## AFTER drafting — required gate

```
paper check style --section methods --workspace <path>
paper check word-count --section methods --workspace <path>
paper check citations --workspace <path>
```

The style checker is gentler on Methods (procedural verbs are not
AI-tone), but `STYLE_BANNED_PUNCT` (em-dash) still applies. The unicode-
character hint in the log-parser will catch raw Unicode math characters
during compile.

## Cross-Section Consistency Check

Methods must align with Results. Verify by inspection:
- Every measure named in Results matches a measure name defined here.
- Every dataset/replay path referenced in evidence nodes
  (`source.ref`) appears in the Reproducibility subsection.
- Every quantitative anchor in Results (effect size, $p$-value, $n$) is
  derivable from the Analysis subsection here.

If any of those fails, the Methods is not done — even if the deterministic
checks pass.

## Done When

- All three envelopes above have no `severity: error` issues.
- A skeptical replicator can reproduce: the population and conditions, the
  randomization, every measure used in Results, the analysis model, the
  inclusion rules. They can locate the code, data, and replay database.

If any of these is unmet, return to the BEFORE block.
