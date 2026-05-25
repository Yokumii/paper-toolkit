# Nature-Figure Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `paper-toolkit` so common figure output is visually close to `.claude/skills/nature-figure`, including cleaner single-chart output, structured composite layouts, and a controlled script backend.

**Architecture:** Keep one figure registry and one registration / QA path, but add two rendering sources: richer structured specs for common figures and an opt-in script backend for complex figures. Build the work in thin vertical slices so existing chart rendering keeps passing while new figure types are added behind explicit discriminators.

**Tech Stack:** Python 3.11, Pydantic v2, matplotlib, Typer, pytest, pypdf

---

### File Map

**Create:**
- `docs/superpowers/specs/2026-05-25-nature-figure-parity-design.md`
- `docs/superpowers/plans/2026-05-25-nature-figure-parity.md`
- `src/paper_toolkit/figures/layout.py`
- `src/paper_toolkit/figures/script_backend.py`
- `tests/unit/test_analysis_skill_prompts.py`
- `tests/unit/test_figure_layout.py`
- `tests/unit/test_figure_script_backend.py`

**Modify:**
- `src/paper_toolkit/models/figure_spec.py`
- `src/paper_toolkit/figures/renderer.py`
- `src/paper_toolkit/figures/charts.py`
- `src/paper_toolkit/checkers/figure_qa.py`
- `src/paper_toolkit/cli/main.py`
- `tests/unit/test_figure_renderer.py`
- `tests/unit/test_cli_figure.py`
- `tests/unit/test_figure_qa.py`
- `skills/agentsociety-analysis/SKILL.md`
- `skills/agentsociety-analysis/prompts/figure_emission.md`
- `skills/agentsociety-analysis/references/analysis_quality.md`
- `skills/agentsociety-analysis/references/chart_qa.md`
- `skills/agentsociety-analysis/references/claim_schema.md`
- `skills/agentsociety-analysis/references/figure_contract.md`
- `skills/agentsociety-analysis/subagent_prompts/figure-reviewer.md`
- `skills/agentsociety-analysis/subagent_prompts/figure-spec-author.md`

### Task 1: Extend FigureSpec for publication-layout controls

**Files:**
- Modify: `src/paper_toolkit/models/figure_spec.py`
- Test: `tests/unit/test_figure_spec_models.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_bar_spec_accepts_tick_rotation_and_legend_position():
    spec = _adapter().validate_python(
        {
            "kind": "bar",
            "id": "fig_ticks",
            "caption": "Demo",
            "data": [{"arm": "Control", "y": 0.4}],
            "x_field": "arm",
            "y_field": "y",
            "tick_label_rotation": 30,
            "legend_position": "right",
            "ylim_mode": "tight",
        }
    )
    assert spec.tick_label_rotation == 30
    assert spec.legend_position == "right"
    assert spec.ylim_mode == "tight"


def test_composite_spec_is_discriminated_and_validates_panels():
    spec = _adapter().validate_python(
        {
            "kind": "composite",
            "id": "fig_combo",
            "caption": "Composite",
            "width": "double",
            "layout": {"rows": 2, "cols": 2},
            "panels": [
                {
                    "panel_id": "a",
                    "row": 0,
                    "col": 0,
                    "rowspan": 1,
                    "colspan": 2,
                    "figure": {
                        "kind": "bar",
                        "id": "fig_child",
                        "caption": "Child",
                        "data": [{"arm": "A", "y": 1.0}],
                        "x_field": "arm",
                        "y_field": "y",
                    },
                }
            ],
        }
    )
    assert spec.kind == "composite"
    assert spec.panels[0].panel_id == "a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_figure_spec_models.py -q`
Expected: FAIL with missing fields or unsupported discriminator errors for the new layout fields.

- [ ] **Step 3: Write minimal implementation**

```python
LegendPosition = Literal["inside", "right", "bottom", "none"]
YLimMode = Literal["auto", "zero", "tight"]


class _FigureBase(BaseModel):
    ...
    tick_label_rotation: int = Field(default=0, ge=0, le=90)
    tick_label_wrap: int | None = Field(default=None, ge=4, le=40)
    title_wrap: int | None = Field(default=None, ge=12, le=120)
    legend_position: LegendPosition = "inside"
    ylim_mode: YLimMode = "auto"
    ylim_padding_ratio: float = Field(default=0.08, ge=0.0, le=0.5)


class PanelFigureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    panel_id: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    figure: "FigureSpec"


class CompositeLayoutSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: int = Field(..., ge=1, le=6)
    cols: int = Field(..., ge=1, le=6)
    height_ratios: list[float] | None = None
    width_ratios: list[float] | None = None


class CompositeFigureSpec(_FigureBase):
    kind: Literal["composite"] = "composite"
    layout: CompositeLayoutSpec
    panels: list[PanelFigureSpec]
    hero_panel: str | None = None
    data: DataPathOrInline = []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_figure_spec_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paper_toolkit/models/figure_spec.py tests/unit/test_figure_spec_models.py
git commit -m "feat: extend figure spec for layout controls"
```

### Task 2: Add layout helpers for titles, ticks, legends, and y-limits

**Files:**
- Create: `src/paper_toolkit/figures/layout.py`
- Test: `tests/unit/test_figure_layout.py`

- [ ] **Step 1: Write the failing tests**

```python
from matplotlib.figure import Figure

from paper_toolkit.figures.layout import apply_axes_layout


def test_apply_axes_layout_rotates_and_wraps_tick_labels():
    fig = Figure()
    ax = fig.subplots()
    ax.bar([0, 1], [1.0, 2.0])
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Counter Attitudinal Exposure", "Pro Attitudinal Exposure"])

    apply_axes_layout(
        ax,
        tick_label_rotation=30,
        tick_label_wrap=12,
        title=None,
        title_wrap=None,
        legend_position="inside",
        ylim_mode="auto",
        ylim_padding_ratio=0.08,
    )

    labels = [tick.get_text() for tick in ax.get_xticklabels()]
    assert any("\n" in label for label in labels)
    assert ax.get_xticklabels()[0].get_rotation() == 30


def test_apply_axes_layout_tight_ylim_adds_padding():
    fig = Figure()
    ax = fig.subplots()
    ax.plot([1, 2, 3], [10.0, 10.2, 10.3])

    apply_axes_layout(
        ax,
        tick_label_rotation=0,
        tick_label_wrap=None,
        title=None,
        title_wrap=None,
        legend_position="inside",
        ylim_mode="tight",
        ylim_padding_ratio=0.1,
    )

    lo, hi = ax.get_ylim()
    assert lo < 10.0
    assert hi > 10.3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_figure_layout.py -q`
Expected: FAIL with `ModuleNotFoundError` for `paper_toolkit.figures.layout`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from textwrap import fill
from typing import Any


def _wrap_text(text: str, width: int | None) -> str:
    if width is None or len(text) <= width:
        return text
    return fill(text, width=width)


def apply_axes_layout(
    ax: Any,
    *,
    tick_label_rotation: int,
    tick_label_wrap: int | None,
    title: str | None,
    title_wrap: int | None,
    legend_position: str,
    ylim_mode: str,
    ylim_padding_ratio: float,
) -> None:
    labels = ax.get_xticklabels()
    for tick in labels:
        tick.set_rotation(tick_label_rotation)
        tick.set_ha("right" if tick_label_rotation else "center")
        tick.set_text(_wrap_text(tick.get_text(), tick_label_wrap))
    ax.set_xticklabels([tick.get_text() for tick in labels])

    if title:
        ax.set_title(_wrap_text(title, title_wrap))

    if ylim_mode == "zero":
        _, hi = ax.get_ylim()
        ax.set_ylim(bottom=0.0, top=hi)
    elif ylim_mode == "tight":
        lo, hi = ax.dataLim.intervaly
        pad = max((hi - lo) * ylim_padding_ratio, 1e-9)
        ax.set_ylim(lo - pad, hi + pad)

    if legend_position == "right" and ax.get_legend() is not None:
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
    elif legend_position == "bottom" and ax.get_legend() is not None:
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    elif legend_position == "none" and ax.get_legend() is not None:
        ax.get_legend().remove()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_figure_layout.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paper_toolkit/figures/layout.py tests/unit/test_figure_layout.py
git commit -m "feat: add figure layout helpers"
```

### Task 3: Wire layout helpers into the renderer and existing chart types

**Files:**
- Modify: `src/paper_toolkit/figures/renderer.py`
- Modify: `src/paper_toolkit/figures/charts.py`
- Test: `tests/unit/test_figure_renderer.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_render_bar_with_wrapped_ticks_and_right_legend(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    spec = BarFigureSpec(
        id="fig_wrapped",
        caption="Wrapped labels",
        data=[
            {"metric": "Counter Attitudinal Exposure", "group": "Control", "y": 0.4},
            {"metric": "Counter Attitudinal Exposure", "group": "Treatment", "y": 0.6},
        ],
        x_field="metric",
        y_field="y",
        group_field="group",
        tick_label_rotation=30,
        tick_label_wrap=12,
        legend_position="right",
    )
    result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)
    assert result.pdf_path.is_file()


def test_render_line_tight_ylim_does_not_raise(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    spec = LineFigureSpec(
        id="fig_tight",
        caption="Tight line",
        data=[{"x": 1, "y": 10.0}, {"x": 2, "y": 10.2}, {"x": 3, "y": 10.3}],
        x_field="x",
        y_field="y",
        ylim_mode="tight",
    )
    result = render_figure(spec=spec, workspace=tmp_path, spec_dir=tmp_path)
    assert result.pdf_path.is_file()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_figure_renderer.py -q`
Expected: FAIL with unsupported keyword or missing layout behavior.

- [ ] **Step 3: Write minimal implementation**

```python
from paper_toolkit.figures.layout import apply_axes_layout

...
        apply_axes_layout(
            ax,
            tick_label_rotation=spec.tick_label_rotation,
            tick_label_wrap=spec.tick_label_wrap,
            title=spec.title,
            title_wrap=spec.title_wrap,
            legend_position=spec.legend_position,
            ylim_mode=spec.ylim_mode,
            ylim_padding_ratio=spec.ylim_padding_ratio,
        )
        fig.tight_layout()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_figure_renderer.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paper_toolkit/figures/renderer.py src/paper_toolkit/figures/charts.py tests/unit/test_figure_renderer.py
git commit -m "feat: apply publication layout controls in renderer"
```

### Task 4: Add structured composite figure rendering

**Files:**
- Modify: `src/paper_toolkit/figures/renderer.py`
- Modify: `src/paper_toolkit/models/figure_spec.py`
- Test: `tests/unit/test_figure_renderer.py`

- [ ] **Step 1: Write the failing test**

```python
def test_render_composite_figure_writes_pdf_and_wrapper(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    composite = _adapter().validate_python(
        {
            "kind": "composite",
            "id": "fig_composite",
            "caption": "Composite demo",
            "width": "double",
            "layout": {"rows": 2, "cols": 2, "height_ratios": [2.0, 1.0]},
            "panels": [
                {
                    "panel_id": "a",
                    "row": 0,
                    "col": 0,
                    "colspan": 2,
                    "figure": {
                        "kind": "line",
                        "id": "fig_nested_line",
                        "caption": "Nested",
                        "data": [{"x": 1, "y": 0.1}, {"x": 2, "y": 0.2}],
                        "x_field": "x",
                        "y_field": "y",
                    },
                },
                {
                    "panel_id": "b",
                    "row": 1,
                    "col": 0,
                    "figure": {
                        "kind": "bar",
                        "id": "fig_nested_bar",
                        "caption": "Nested",
                        "data": [{"arm": "A", "y": 1.0}],
                        "x_field": "arm",
                        "y_field": "y",
                    },
                },
            ],
        }
    )
    result = render_figure(spec=composite, workspace=tmp_path, spec_dir=tmp_path)
    assert result.pdf_path.is_file()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_figure_renderer.py -q`
Expected: FAIL with unsupported `CompositeFigureSpec`.

- [ ] **Step 3: Write minimal implementation**

```python
if isinstance(spec, CompositeFigureSpec):
    fig = plt.figure(figsize=_figsize(spec.width))
    gs = fig.add_gridspec(
        spec.layout.rows,
        spec.layout.cols,
        height_ratios=spec.layout.height_ratios,
        width_ratios=spec.layout.width_ratios,
    )
    for panel in spec.panels:
        ax = fig.add_subplot(gs[panel.row : panel.row + panel.rowspan, panel.col : panel.col + panel.colspan])
        _draw_into_axes(ax, panel.figure, rows=load_data(...), palette=resolve_palette(panel.figure.palette))
        ax.text(-0.08, 1.02, panel.panel_id, transform=ax.transAxes, fontweight="bold")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_figure_renderer.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paper_toolkit/models/figure_spec.py src/paper_toolkit/figures/renderer.py tests/unit/test_figure_renderer.py
git commit -m "feat: add composite figure rendering"
```

### Task 5: Add script backend support

**Files:**
- Create: `src/paper_toolkit/figures/script_backend.py`
- Modify: `src/paper_toolkit/models/figure_spec.py`
- Modify: `src/paper_toolkit/figures/renderer.py`
- Test: `tests/unit/test_figure_script_backend.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_script_backend_runs_python_figure_script_and_validates_outputs(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    script = tmp_path / "paper" / "figure_specs" / "emit_demo.py"
    script.write_text(
        \"\"\"
from pathlib import Path
import matplotlib.pyplot as plt

def main(out_dir: str) -> None:
    out = Path(out_dir)
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    fig.savefig(out / "fig_script.pdf")
    fig.savefig(out / "fig_script.svg")
\"\"\",
        encoding="utf-8",
    )
    result = run_script_backend(
        script_path=script,
        backend="python",
        workspace=workspace,
        figure_id="fig_script",
    )
    assert result["pdf_path"].name == "fig_script.pdf"
    assert result["svg_path"].name == "fig_script.svg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_figure_script_backend.py -q`
Expected: FAIL with `ModuleNotFoundError` for `paper_toolkit.figures.script_backend`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import subprocess
from pathlib import Path


def run_script_backend(*, script_path: Path, backend: str, workspace: Path, figure_id: str) -> dict[str, Path]:
    out_dir = workspace / "paper" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    if backend == "python":
        subprocess.run(["python", str(script_path), str(out_dir)], check=True)
    else:
        subprocess.run(["Rscript", str(script_path), str(out_dir)], check=True)
    pdf_path = out_dir / f"{figure_id}.pdf"
    svg_path = out_dir / f"{figure_id}.svg"
    if not pdf_path.exists() or not svg_path.exists():
        raise FileNotFoundError("script backend did not produce required outputs")
    return {"pdf_path": pdf_path, "svg_path": svg_path}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_figure_script_backend.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paper_toolkit/figures/script_backend.py tests/unit/test_figure_script_backend.py src/paper_toolkit/models/figure_spec.py src/paper_toolkit/figures/renderer.py
git commit -m "feat: add script-backed figure rendering"
```

### Task 6: Extend figure QA for basic layout findings

**Files:**
- Modify: `src/paper_toolkit/checkers/figure_qa.py`
- Test: `tests/unit/test_figure_qa.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_check_figure_qa_flags_svg_missing_for_script_figure(tmp_path: Path) -> None:
    (tmp_path / "paper" / "figures").mkdir(parents=True)
    (tmp_path / "paper" / "figures" / "fig_missing_svg.pdf").write_bytes(b"%PDF-1.4")
    report = check_figure_qa(workspace=tmp_path)
    assert any(issue.code == "FQA_MISSING_SVG" for issue in report.issues)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_figure_qa.py -q`
Expected: FAIL because `FQA_MISSING_SVG` is not emitted.

- [ ] **Step 3: Write minimal implementation**

```python
for pdf_path in sorted(paths.figures_dir.glob("*.pdf")):
    svg_path = pdf_path.with_suffix(".svg")
    if not svg_path.exists():
        issues.append(
            issue(
                severity="warning",
                code="FQA_MISSING_SVG",
                message=f"{pdf_path.name}: editable SVG companion is missing.",
                location=f"paper/figures/{pdf_path.name}",
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_figure_qa.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paper_toolkit/checkers/figure_qa.py tests/unit/test_figure_qa.py
git commit -m "feat: extend figure qa checks for publication outputs"
```

### Task 7: Update CLI and prompt surface for new figure sources

**Files:**
- Modify: `src/paper_toolkit/cli/main.py`
- Modify: `tests/unit/test_cli_figure.py`
- Modify: `skills/agentsociety-analysis/*`
- Test: `tests/unit/test_analysis_skill_prompts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_render_script_spec_happy_path(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    spec_path = tmp_path / "paper" / "figure_specs" / "fig_script.json"
    spec_path.write_text(
        json.dumps(
            {
                "kind": "script",
                "id": "fig_script",
                "caption": "Scripted figure",
                "backend": "python",
                "entrypoint": "emit_script.py",
                "data": [],
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli_figure.py tests/unit/test_analysis_skill_prompts.py -q`
Expected: FAIL because CLI does not understand script specs yet.

- [ ] **Step 3: Write minimal implementation**

```python
if isinstance(spec, ScriptFigureSpec):
    render_result = render_script_figure(spec=spec, workspace=workspace, spec_dir=spec_dir)
else:
    render_result = render_figure(spec=spec, workspace=workspace, spec_dir=spec_dir)
```

Update prompts so:

```text
- use structured specs for common single-chart and composite figures
- use script-backed figures when layout or modality exceeds the built-in chart kinds
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_cli_figure.py tests/unit/test_analysis_skill_prompts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paper_toolkit/cli/main.py tests/unit/test_cli_figure.py tests/unit/test_analysis_skill_prompts.py skills/agentsociety-analysis
git commit -m "feat: expose advanced figure backends through cli and prompts"
```

### Task 8: Final verification

**Files:**
- Verify only

- [ ] **Step 1: Run focused figure test suite**

Run:

```bash
uv run pytest \
  tests/unit/test_figure_spec_models.py \
  tests/unit/test_figure_layout.py \
  tests/unit/test_figure_renderer.py \
  tests/unit/test_figure_script_backend.py \
  tests/unit/test_figure_qa.py \
  tests/unit/test_cli_figure.py \
  tests/unit/test_analysis_skill_prompts.py \
  tests/unit/test_cli_analysis.py \
  tests/unit/test_analysis_checkers.py -q
```

Expected: PASS

- [ ] **Step 2: Run lint and type checks**

Run:

```bash
uv run ruff check src tests
uv run mypy src
```

Expected: PASS

- [ ] **Step 3: Inspect git state**

Run:

```bash
git status --short
git diff --stat
```

Expected: only the planned files are modified or created.

- [ ] **Step 4: Commit final integration**

```bash
git add src tests skills docs
git commit -m "feat: add nature-figure parity rendering path"
```
