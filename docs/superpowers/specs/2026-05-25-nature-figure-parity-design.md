# Nature-Figure Parity Design

**Goal**

Bring `paper-toolkit` figure output close to `.claude/skills/nature-figure`
for common paper figures while preserving the toolkit's deterministic
registration, checking, and LaTeX assembly flow.

**Problem**

The current analysis skill now enforces claim-aligned comparisons, but the
rendering system still produces only simple single-axis charts. The visual gap
comes from three missing layers:

1. The spec model cannot express most layout or annotation decisions.
2. The renderer cannot produce multi-panel or legend-aware layouts.
3. Complex figures have no controlled escape hatch to a script backend.

`nature-figure` succeeds because it combines contract-first design, richer
layout patterns, and backend flexibility. `paper-toolkit` currently provides
only a narrow structured renderer.

**Non-Goals**

- Re-implement every pattern in `nature-figure`.
- Add arbitrary free-form plotting logic to the CLI.
- Add non-deterministic LLM behavior into toolkit commands.
- Replace the existing `FigureSpec` path for simple charts.

**Requirements**

1. Common comparative figures must render cleanly at publication width.
2. The system must support multi-panel layouts with one dominant panel and
   smaller supporting panels.
3. Complex figures must be able to use a controlled Python or R script backend
   while staying inside toolkit registration and QA.
4. QA must cover both deterministic PDF properties and basic rendered layout
   failures such as clipped titles and overlapping tick labels.
5. Analysis-side prompts must know when to use structured specs and when to use
   the script backend.

**Architecture**

The upgraded figure system will have two rendering paths behind one registry:

- `source = "spec"`: structured, deterministic charts powered by an expanded
  `FigureSpec` model and a richer renderer.
- `source = "script"`: controlled Python or R figure scripts that emit figure
  assets and a manifest consumed by the same registration and QA path.

Both paths still end in:

- figure asset files under `paper/figures/`
- wrapper `.tex` files
- `paper.json:artifacts.figures[]`
- `paper check figure-qa`

**Phase Plan**

### Phase 1: Structured single-chart improvements

Extend the current figure spec and renderer so ordinary bar / line / scatter /
forest figures can match basic publication-quality expectations:

- tick-label rotation and wrapping
- title wrapping
- legend placement choices
- y-axis range modes and padding
- optional direct labels / hatching / annotation modes

This phase addresses the current visible failures without changing the workflow.

### Phase 2: Composite structured figures

Add a new composite spec that can arrange multiple child panels into a shared
grid with:

- panel labels
- width and height ratios
- shared legends
- a designated hero panel

This phase is the structured equivalent of the most common
`nature-figure` layouts.

### Phase 3: Script backend

Add a controlled script-backed figure source for cases that exceed the
structured renderer. The script backend must:

- declare Python or R explicitly
- emit at least `pdf` and `svg`
- return a small manifest with figure id, label, caption, and produced files
- stay separate from registration and QA

This preserves auditability while allowing higher-fidelity figure generation.

### Phase 4: QA and skill integration

Extend `paper check figure-qa` and the analysis skill prompts to enforce:

- deterministic PDF checks
- basic rendered-layout checks
- correct choice between structured and script-backed figures

**Data Model Changes**

Add layout-level fields to `_FigureBase` and chart-specific fields where needed.
Introduce:

- `CompositeFigureSpec`
- `ScriptFigureSpec`
- `PanelSpec` child models for composite layouts

The discriminator remains a single entry point so the CLI can still parse specs
without ad hoc branching.

**Testing Strategy**

1. Unit tests for spec validation and model parsing.
2. Renderer tests for:
   - rotated / wrapped ticks
   - wrapped titles
   - grouped comparison charts
   - composite figure output
3. QA tests for:
   - layout-overlap findings
   - script manifest validation
4. CLI tests for:
   - new render modes
   - registration behavior
   - failure cases for malformed specs or missing script outputs
5. Prompt tests to keep skill guidance aligned with the new capability split.

**Risk Management**

- Keep the existing simple path working unchanged for current tests.
- Add new types rather than overloading old fields with ambiguous meanings.
- Treat script-backed rendering as opt-in so current users keep deterministic
  behavior by default.
- Keep registration and QA centralized to avoid divergence between backends.

**Acceptance**

The work is complete when:

1. Simple comparative figures render without the current clipping and overlap
   issues.
2. A structured composite figure can produce a hero panel plus supporting
   panels at final paper dimensions.
3. A script-backed figure can render, register, and pass through QA.
4. Analysis-side prompts steer figure generation toward the correct backend.
