"""IO helpers for `analysis/synthesis/<hypothesis-id>/synthesis_brief.json`."""

from __future__ import annotations

import json
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.analysis import SynthesisBrief, SynthesisClaim
from paper_toolkit.paths import WorkspacePaths


class SynthesisBriefNotFound(FileNotFoundError):
    """Raised when synthesis_brief.json is missing."""


def _serialize(brief: SynthesisBrief) -> str:
    return json.dumps(brief.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def read_brief(*, workspace: Path, hypothesis_id: str) -> SynthesisBrief:
    paths = WorkspacePaths(workspace=workspace)
    path = paths.synthesis_brief(hypothesis_id=hypothesis_id)
    if not path.exists():
        raise SynthesisBriefNotFound(str(path))
    return SynthesisBrief.model_validate_json(path.read_text(encoding="utf-8"))


def write_brief(*, workspace: Path, brief: SynthesisBrief) -> None:
    paths = WorkspacePaths(workspace=workspace)
    out = paths.synthesis_brief(hypothesis_id=brief.hypothesis_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(out, _serialize(brief))


def upsert_synthesis_claim(
    *,
    workspace: Path,
    hypothesis_id: str,
    claim: SynthesisClaim,
) -> SynthesisBrief:
    """Insert or replace `claim` inside the brief. Brief is created if missing."""
    try:
        brief = read_brief(workspace=workspace, hypothesis_id=hypothesis_id)
    except SynthesisBriefNotFound:
        brief = SynthesisBrief(
            hypothesis_id=hypothesis_id,
            experiments=list(claim.source_experiments),
        )
    existing_ids = [c.claim_id for c in brief.claims]
    if claim.claim_id in existing_ids:
        brief.claims = [claim if c.claim_id == claim.claim_id else c for c in brief.claims]
    else:
        brief.claims.append(claim)
    # Refresh the experiments list — union of all referenced experiments.
    experiments: list[str] = []
    seen: set[str] = set()
    for c in brief.claims:
        for exp in c.source_experiments:
            if exp not in seen:
                seen.add(exp)
                experiments.append(exp)
    brief.experiments = experiments or list(claim.source_experiments)
    write_brief(workspace=workspace, brief=brief)
    return brief
