"""IO helpers for `claims.json`."""

from __future__ import annotations

import json
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.analysis import Claim, ClaimsFile, FigureContract
from paper_toolkit.paths import WorkspacePaths


class ClaimsFileNotFound(FileNotFoundError):
    """Raised when claims.json is expected but missing."""


def _serialize(claims_file: ClaimsFile) -> str:
    return json.dumps(claims_file.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def read_claims(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> ClaimsFile:
    paths = WorkspacePaths(workspace=workspace)
    path = paths.claims_file(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    if not path.exists():
        raise ClaimsFileNotFound(str(path))
    return ClaimsFile.model_validate_json(path.read_text(encoding="utf-8"))


def write_claims(
    *,
    workspace: Path,
    claims_file: ClaimsFile,
) -> None:
    paths = WorkspacePaths(workspace=workspace)
    out = paths.claims_file(
        hypothesis_id=claims_file.hypothesis_id, experiment_id=claims_file.experiment_id
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(out, _serialize(claims_file))


def load_or_empty(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> ClaimsFile:
    try:
        return read_claims(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        )
    except ClaimsFileNotFound:
        return ClaimsFile(hypothesis_id=hypothesis_id, experiment_id=experiment_id)


def upsert_claim(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    claim: Claim,
) -> ClaimsFile:
    """Insert claim if new, else replace the existing one with the same `claim_id`."""
    claims = load_or_empty(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    existing_ids = [c.claim_id for c in claims.claims]
    if claim.claim_id in existing_ids:
        claims.claims = [claim if c.claim_id == claim.claim_id else c for c in claims.claims]
    else:
        claims.claims.append(claim)
    write_claims(workspace=workspace, claims_file=claims)
    return claims


def attach_figure_contract(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    claim_id: str,
    figure_id: str,
    rationale: str,
) -> ClaimsFile:
    """Bind an existing claim to a figure spec."""
    claims = read_claims(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    found = False
    for claim in claims.claims:
        if claim.claim_id == claim_id:
            claim.figure_contract = FigureContract(figure_id=figure_id, rationale=rationale)
            found = True
            break
    if not found:
        raise ValueError(f"claim {claim_id!r} not found")
    write_claims(workspace=workspace, claims_file=claims)
    return claims
