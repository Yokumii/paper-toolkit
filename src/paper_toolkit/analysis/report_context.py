"""Build the report-stage handoff artifacts.

`build_report_context` walks the experiment's `claims.json` and emits:

- `report_context.md` — agent-facing brief: claims, evidence rows, figure
  contracts, all in one document the report-producer subagent can consume
  without re-reading claims.json or running queries.
- `evidence_index.json` — machine-facing index: maps each `claim_id` to
  `{ "evidence": str, "figure_id": str | None }` so downstream tools can
  resolve a claim quickly.

Pure stdlib + the existing `paper_toolkit.io.write_atomic_text`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from paper_toolkit.analysis import claims as claims_state
from paper_toolkit.io import write_atomic_text
from paper_toolkit.paths import WorkspacePaths


@dataclass(frozen=True)
class ReportContextResult:
    report_context_path: Path
    evidence_index_path: Path
    claim_count: int


def build_report_context(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> ReportContextResult:
    paths = WorkspacePaths(workspace=workspace)
    claims_file = claims_state.read_claims(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )

    md_lines: list[str] = [
        f"# Report context — {hypothesis_id} / {experiment_id}",
        "",
        f"Total claims: {len(claims_file.claims)}",
        "",
    ]
    index: dict[str, dict[str, str | None]] = {}
    for claim in claims_file.claims:
        md_lines.append(f"## {claim.claim_id} — {claim.kind}")
        md_lines.append("")
        md_lines.append(claim.text)
        md_lines.append("")
        md_lines.append(f"- evidence: {claim.evidence}")
        figure_id: str | None = None
        if claim.figure_contract is not None:
            figure_id = claim.figure_contract.figure_id
            md_lines.append(f"- figure: `{figure_id}` — {claim.figure_contract.rationale}")
        else:
            md_lines.append("- figure: _none registered_")
        md_lines.append("")
        index[claim.claim_id] = {
            "kind": claim.kind,
            "evidence": claim.evidence,
            "figure_id": figure_id,
        }

    md_path = paths.report_context_md(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(md_path, "\n".join(md_lines).rstrip() + "\n")

    index_path = paths.evidence_index(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    write_atomic_text(
        index_path,
        json.dumps(
            {
                "schema_version": "1.0",
                "hypothesis_id": hypothesis_id,
                "experiment_id": experiment_id,
                "claims": index,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return ReportContextResult(
        report_context_path=md_path,
        evidence_index_path=index_path,
        claim_count=len(claims_file.claims),
    )
