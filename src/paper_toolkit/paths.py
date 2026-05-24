"""Workspace path resolution. All paths under <workspace>/paper/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolves canonical paths under a workspace's `paper/` directory."""

    workspace: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace", self.workspace.resolve())

    @property
    def paper_dir(self) -> Path:
        return (self.workspace / "paper").resolve()

    @property
    def paper_state(self) -> Path:
        return (self.paper_dir / "paper.json").resolve()

    @property
    def evidence_graph(self) -> Path:
        return (self.paper_dir / "evidence_graph.json").resolve()

    @property
    def research_pack(self) -> Path:
        return (self.paper_dir / "research_pack.json").resolve()

    @property
    def venue_yaml(self) -> Path:
        return (self.paper_dir / "venue.yaml").resolve()

    @property
    def sections_dir(self) -> Path:
        return (self.paper_dir / "sections").resolve()

    @property
    def figures_dir(self) -> Path:
        return (self.paper_dir / "figures").resolve()

    @property
    def figure_specs_dir(self) -> Path:
        return (self.paper_dir / "figure_specs").resolve()

    @property
    def tables_dir(self) -> Path:
        return (self.paper_dir / "tables").resolve()

    @property
    def table_specs_dir(self) -> Path:
        return (self.paper_dir / "table_specs").resolve()

    @property
    def reviews_dir(self) -> Path:
        return (self.paper_dir / "reviews").resolve()

    @property
    def lit_dir(self) -> Path:
        return (self.paper_dir / "lit").resolve()

    @property
    def compile_runs_dir(self) -> Path:
        return (self.paper_dir / "compile_runs").resolve()

    @property
    def refs_bib(self) -> Path:
        return (self.paper_dir / "refs.bib").resolve()

    @property
    def main_tex(self) -> Path:
        return (self.paper_dir / "main.tex").resolve()

    def relative_to_workspace(self, p: Path) -> str:
        return str(p.resolve().relative_to(self.workspace)).replace("\\", "/")

    def compile_run_dir(self, run_id: str) -> Path:
        return (self.compile_runs_dir / run_id).resolve()

    def compile_run_json(self, run_id: str) -> Path:
        return (self.compile_run_dir(run_id) / "run.json").resolve()

    def compile_run_pages_dir(self, run_id: str) -> Path:
        return (self.compile_run_dir(run_id) / "pages").resolve()

    def compile_run_elements(self, run_id: str) -> Path:
        return (self.compile_run_pages_dir(run_id) / "elements.json").resolve()

    # --- analysis pipeline (sibling tree to paper/) -------------------------

    @property
    def analysis_dir(self) -> Path:
        return (self.workspace / "analysis").resolve()

    @property
    def synthesis_dir(self) -> Path:
        return (self.analysis_dir / "synthesis").resolve()

    def experiment_dir(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return (self.analysis_dir / hypothesis_id / experiment_id).resolve()

    def analysis_state(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return (
            self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            / "state.yaml"
        )

    def analysis_config(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return (
            self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            / "config.yaml"
        )

    def analysis_plan(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return (
            self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            / "analysis_plan.yaml"
        )

    def claims_file(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return (
            self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            / "claims.json"
        )

    def eda_dir(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id) / "eda"

    def report_context_md(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return (
            self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            / "report_context.md"
        )

    def evidence_index(self, *, hypothesis_id: str, experiment_id: str) -> Path:
        return (
            self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            / "evidence_index.json"
        )

    def report_md(self, *, hypothesis_id: str, experiment_id: str, language: str) -> Path:
        return (
            self.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            / f"report_{language}.md"
        )

    def synthesis_brief(self, *, hypothesis_id: str) -> Path:
        return (self.synthesis_dir / hypothesis_id / "synthesis_brief.json").resolve()
