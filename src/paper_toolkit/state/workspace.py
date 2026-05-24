"""Workspace state operations: init / read / write / compute_state_summary.

`paper.json` is the source of truth. Plans 2-4 will populate fields that this
plan currently reports as zero/None (evidence graph counts, figure packed counts,
last compile, etc.).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from paper_toolkit.envelope import StateSummary
from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.paper_state import (
    ArtifactRef,
    Artifacts,
    CompileRunRef,
    CompileSummary,
    Language,
    PaperMeta,
    PaperState,
)
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state import evidence_graph as evidence_graph_state


class WorkspaceAlreadyInitialized(RuntimeError):
    """Raised by init_workspace when paper.json already exists."""


class WorkspaceNotInitialized(RuntimeError):
    """Raised by read_state when paper.json is missing."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _serialize_state(state: PaperState) -> str:
    return json.dumps(state.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def init_workspace(
    *,
    workspace: Path,
    title: str,
    venue: str,
    language: Language,
) -> PaperState:
    """Create paper/ subtree and write a fresh paper.json. Refuses if already initialized."""
    paths = WorkspacePaths(workspace=workspace)
    if paths.paper_state.exists():
        raise WorkspaceAlreadyInitialized(str(paths.paper_state))
    for d in (
        paths.paper_dir,
        paths.sections_dir,
        paths.figures_dir,
        paths.figure_specs_dir,
        paths.tables_dir,
        paths.table_specs_dir,
        paths.reviews_dir,
        paths.compile_runs_dir,
        paths.lit_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)

    state = PaperState(
        schema_version="1.0",
        meta=PaperMeta(
            title=title,
            venue=venue,
            language=language,
            created_at=_utcnow(),
            workspace_root=str(paths.workspace),
        ),
        artifacts=Artifacts(),
    )
    write_state(workspace=workspace, state=state)
    return state


def read_state(*, workspace: Path) -> PaperState:
    paths = WorkspacePaths(workspace=workspace)
    if not paths.paper_state.exists():
        raise WorkspaceNotInitialized(str(paths.paper_state))
    raw = paths.paper_state.read_text(encoding="utf-8")
    return PaperState.model_validate_json(raw)


def write_state(*, workspace: Path, state: PaperState) -> None:
    paths = WorkspacePaths(workspace=workspace)
    paths.paper_dir.mkdir(parents=True, exist_ok=True)
    write_atomic_text(paths.paper_state, _serialize_state(state))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_ref_for(paths: WorkspacePaths, path: Path) -> ArtifactRef:
    return ArtifactRef(
        path=paths.relative_to_workspace(path),
        updated_at=_utcnow(),
        checksum=_sha256_file(path),
    )


def refresh_artifact_ref(
    *,
    workspace: Path,
    state: PaperState,
    artifact: str | None = None,
    artifact_section: str | None = None,
) -> None:
    paths = WorkspacePaths(workspace=workspace)
    if artifact_section is not None:
        state.artifacts.sections[artifact_section] = _artifact_ref_for(
            paths, paths.sections_dir / f"{artifact_section}.tex"
        )
        return
    if artifact == "research_pack":
        state.artifacts.research_pack = _artifact_ref_for(paths, paths.research_pack)
        return
    if artifact == "evidence_graph":
        state.artifacts.evidence_graph = _artifact_ref_for(paths, paths.evidence_graph)
        return
    if artifact == "bib":
        state.artifacts.bib = _artifact_ref_for(paths, paths.refs_bib)
        return
    if artifact == "main_tex":
        state.artifacts.main_tex = _artifact_ref_for(paths, paths.main_tex)
        return
    raise ValueError(f"unsupported artifact ref {artifact!r}")


def append_compile_run_ref(*, state: PaperState, compile_run: CompileRunRef) -> None:
    state.artifacts.compile_runs = [
        run for run in state.artifacts.compile_runs if run.id != compile_run.id
    ]
    state.artifacts.compile_runs.append(compile_run)


def compute_state_summary(*, workspace: Path, state: PaperState) -> StateSummary:
    """Build the StateSummary returned in every envelope."""
    paths = WorkspacePaths(workspace=workspace)
    paper_json_text = (
        paths.paper_state.read_text(encoding="utf-8") if paths.paper_state.exists() else ""
    )

    claim_count = 0
    evidence_count = 0
    citation_count = 0
    graph_valid = True
    graph_issue_count = 0
    last_updated_artifact = None

    if paths.evidence_graph.exists():
        graph = evidence_graph_state.load(workspace=workspace)
        claim_count = sum(1 for node in graph.nodes if node.kind == "claim")
        evidence_count = sum(1 for node in graph.nodes if node.kind == "evidence")
        citation_count = sum(1 for node in graph.nodes if node.kind == "citation")
        refs_text = paths.refs_bib.read_text(encoding="utf-8") if paths.refs_bib.exists() else None
        graph_errors, _ = evidence_graph_state.validate_graph(graph=graph, refs_bib_text=refs_text)
        graph_issue_count = len(graph_errors)
        graph_valid = graph_issue_count == 0
        last_updated_artifact = paths.relative_to_workspace(paths.evidence_graph)
    elif paths.research_pack.exists():
        last_updated_artifact = paths.relative_to_workspace(paths.research_pack)

    last_compile = None
    if state.artifacts.compile_runs:
        last_run = state.artifacts.compile_runs[-1]
        last_compile = CompileSummary(
            id=last_run.id,
            ok=last_run.ok,
            error_count=last_run.error_count,
            ts=last_run.finished_at,
        )

    return StateSummary(
        section_count=len(state.artifacts.sections),
        claim_count=claim_count,
        evidence_count=evidence_count,
        citation_count=citation_count,
        figure_count=len(state.artifacts.figures),
        packed_figure_count=sum(
            1 for f in state.artifacts.figures if (paths.workspace / f.packed).exists()
        ),
        graph_valid=graph_valid,
        graph_issue_count=graph_issue_count,
        last_compile=last_compile,
        last_updated_artifact=last_updated_artifact,
        paper_json_checksum=_sha256_text(paper_json_text),
    )
