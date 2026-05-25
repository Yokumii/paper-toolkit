"""`paper init` command logic."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.models.paper_state import Language
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceAlreadyInitialized,
    compute_state_summary,
    init_workspace,
    read_state,
)

_VALID_LANGUAGES = set(get_args(Language))


def run(*, workspace: Path, title: str, venue: str, language: str) -> Envelope:
    paths = WorkspacePaths(workspace=workspace)

    if language not in _VALID_LANGUAGES:
        from paper_toolkit.envelope import StateSummary

        summary = StateSummary(
            section_count=0,
            claim_count=0,
            evidence_count=0,
            citation_count=0,
            figure_count=0,
            packed_figure_count=0,
            graph_valid=True,
            graph_issue_count=0,
            last_compile=None,
            last_updated_artifact=None,
            paper_json_checksum="0" * 64,
        )
        return build_envelope(
            action="init",
            result={},
            state_summary=summary,
            errors=[
                ErrorEntry(
                    code="INIT_BAD_LANGUAGE",
                    message=f"language must be one of {sorted(_VALID_LANGUAGES)}; got {language!r}",
                    fixup_hint="Pass --language en | zh | bilingual.",
                )
            ],
        )

    try:
        init_workspace(
            workspace=workspace,
            title=title,
            venue=venue,
            language=language,  # type: ignore[arg-type]
        )
    except WorkspaceAlreadyInitialized:
        state = read_state(workspace=workspace)
        summary = compute_state_summary(workspace=workspace, state=state)
        return build_envelope(
            action="init",
            result={"paper_state_path": str(paths.paper_state)},
            state_summary=summary,
            errors=[
                ErrorEntry(
                    code="WS_ALREADY_INITIALIZED",
                    message=f"paper/paper.json already exists at {paths.paper_state}",
                    fixup_hint="Edit it manually, or remove paper/ if you want a fresh init.",
                )
            ],
        )

    scaffolded_venue_yaml = False
    if venue != "nature" and not paths.venue_yaml.exists():
        paths.venue_yaml.parent.mkdir(parents=True, exist_ok=True)
        paths.venue_yaml.write_text(
            f"""# paper/venue.yaml — overrides for venue {venue!r}.
# This file is auto-merged on top of the built-in `nature` defaults; list only
# the keys you want to override. Delete this file to fall back to plain nature.
name: {venue}
""",
            encoding="utf-8",
        )
        scaffolded_venue_yaml = True

    state = read_state(workspace=workspace)
    summary = compute_state_summary(workspace=workspace, state=state)
    result: dict[str, object] = {
        "paper_state_path": str(paths.paper_state),
        "title": state.meta.title,
        "venue": state.meta.venue,
        "language": state.meta.language,
    }
    if scaffolded_venue_yaml:
        result["scaffolded_venue_yaml"] = str(paths.venue_yaml)
    return build_envelope(
        action="init",
        result=result,
        state_summary=summary,
    )
