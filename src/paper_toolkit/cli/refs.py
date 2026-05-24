"""`paper refs ...` command logic."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.envelope import Envelope, ErrorEntry, StateSummary, build_envelope
from paper_toolkit.io import write_atomic_text
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.refs import (
    apply_dedup,
    find_duplicates,
    parse_bibtex,
    serialize_entries,
)
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
    refresh_artifact_ref,
    write_state,
)


def _zero_summary() -> StateSummary:
    from paper_toolkit.cli.main import _zero_summary as zero

    return zero()


def _state_summary(workspace: Path) -> StateSummary:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _zero_summary()
    return compute_state_summary(workspace=workspace, state=state)


def _missing_workspace_envelope(*, workspace: Path, action: str) -> Envelope:
    paths = WorkspacePaths(workspace=workspace)
    return build_envelope(
        action=action,
        result={"workspace": str(paths.workspace)},
        state_summary=_zero_summary(),
        errors=[
            ErrorEntry(
                code="WS_NOT_INITIALIZED",
                message=f"no paper.json found at {paths.paper_state}",
            )
        ],
    )


def dedup_cmd(*, workspace: Path, apply: bool) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="refs.dedup")

    paths = WorkspacePaths(workspace=workspace)
    if not paths.refs_bib.exists():
        return build_envelope(
            action="refs.dedup",
            result={"bib_path": str(paths.refs_bib), "entry_count": 0, "groups": []},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="REFS_BIB_MISSING",
                    message=f"refs.bib not found at {paths.refs_bib}",
                    fixup_hint="Run paper compose write-bib or paper lit merge-bib first.",
                )
            ],
        )

    text = paths.refs_bib.read_text(encoding="utf-8")
    entries = parse_bibtex(text)
    groups = find_duplicates(entries)
    payload_groups = [
        {
            "reason": g.reason,
            "keeper": g.keeper_cite_key,
            "absorbed": list(g.absorbed_cite_keys),
        }
        for g in groups
    ]

    result: dict[str, object] = {
        "bib_path": str(paths.refs_bib),
        "entry_count": len(entries),
        "duplicate_count": sum(len(g.absorbed_cite_keys) for g in groups),
        "group_count": len(groups),
        "groups": payload_groups,
        "applied": False,
    }

    if apply and groups:
        deduped = apply_dedup(entries, groups)
        new_text = serialize_entries(deduped)
        write_atomic_text(paths.refs_bib, new_text)
        refresh_artifact_ref(workspace=workspace, state=state, artifact="bib")
        write_state(workspace=workspace, state=state)
        result["applied"] = True
        result["entry_count_after"] = len(deduped)

    return build_envelope(
        action="refs.dedup",
        result=result,
        state_summary=_state_summary(workspace),
    )
