"""Default scanner for AgentSociety-style research workspaces."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from paper_toolkit.models.research_pack import (
    CandidateFigure,
    CandidateTable,
    HypothesisEntry,
    ReplayDbEntry,
    ReportEntry,
    ResearchPack,
)

_FIG_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".svg"}
_TABLE_EXTS = {".csv", ".tsv", ".xlsx", ".xls"}


def _read_text(path: Path, limit: int = 8000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except UnicodeDecodeError:
        return ""


def _first_heading(markdown: str) -> str | None:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def _title_from_filename(path: Path) -> str:
    words = re.sub(r"[_-]+", " ", path.stem).strip()
    return words[:1].upper() + words[1:] if words else path.stem


def _hypothesis_dirs(workspace: Path) -> list[Path]:
    if not workspace.exists():
        return []
    return sorted(
        p
        for p in workspace.iterdir()
        if p.is_dir()
        and p.name.startswith("hypothesis_")
        and p.name[len("hypothesis_") :].isdigit()
    )


def _experiment_dirs(hypothesis_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in hypothesis_dir.iterdir()
        if p.is_dir()
        and p.name.startswith("experiment_")
        and p.name[len("experiment_") :].isdigit()
    )


class AgentSocietyScanner:
    """Default scanner for AgentSociety-style research workspaces.

    Concrete; not part of an abstract hierarchy. If a second scanner is ever
    needed, refactor a Protocol then.
    """

    name = "agentsociety"

    def scan(self, workspace: Path) -> ResearchPack:
        root = workspace.expanduser().resolve()
        notes: list[str] = []
        hypotheses: list[HypothesisEntry] = []
        reports: list[ReportEntry] = []
        figures: list[CandidateFigure] = []
        tables: list[CandidateTable] = []
        replay_dbs: list[ReplayDbEntry] = []

        h_dirs = _hypothesis_dirs(root)
        if not h_dirs:
            notes.append("No hypothesis_* directories found.")

        figure_index = 1
        table_index = 1
        for h_dir in h_dirs:
            exp_dirs = _experiment_dirs(h_dir)
            h_text = _read_text(h_dir / "HYPOTHESIS.md")
            hypotheses.append(
                HypothesisEntry(
                    id=h_dir.name,
                    path=str((h_dir / "HYPOTHESIS.md").resolve()),
                    text=h_text,
                    experiments=[p.name for p in exp_dirs],
                )
            )

            for exp_dir in exp_dirs:
                for db in sorted((exp_dir / "run").glob("*.sqlite")):
                    replay_dbs.append(
                        ReplayDbEntry(path=str(db.resolve()), experiment_id=exp_dir.name)
                    )

            presentation_dir = root / "presentation" / h_dir.name
            report_path = next(
                (
                    p
                    for p in [
                        presentation_dir / "report.md",
                        presentation_dir / "report_en.md",
                        presentation_dir / "report_zh.md",
                    ]
                    if p.exists()
                ),
                None,
            )
            report_id = f"report_{h_dir.name}"
            report_text = _read_text(report_path) if report_path is not None else ""
            if report_path is not None:
                reports.append(
                    ReportEntry(
                        id=report_id,
                        path=str(report_path.resolve()),
                        title=_first_heading(report_text),
                        summary=report_text,
                    )
                )

            assets_dir = presentation_dir / "assets"
            for fig in sorted(
                p for p in assets_dir.rglob("*") if p.is_file() and p.suffix.lower() in _FIG_EXTS
            ):
                figures.append(
                    CandidateFigure(
                        src=str(fig.resolve()),
                        suggested_id=f"fig{figure_index}",
                        suggested_caption=_title_from_filename(fig),
                        referenced_in_reports=[report_id] if report_path is not None else [],
                    )
                )
                figure_index += 1

            data_dir = presentation_dir / "data"
            for table in sorted(
                p for p in data_dir.rglob("*") if p.is_file() and p.suffix.lower() in _TABLE_EXTS
            ):
                tables.append(
                    CandidateTable(
                        src=str(table.resolve()),
                        suggested_id=f"tab{table_index}",
                        suggested_caption=_title_from_filename(table),
                        referenced_in_reports=[report_id] if report_path is not None else [],
                    )
                )
                table_index += 1

        return ResearchPack(
            schema_version="1.0",
            workspace_root=str(root),
            scanned_at=datetime.now(UTC),
            hypotheses=hypotheses,
            analysis_reports=reports,
            candidate_figures=figures,
            candidate_tables=tables,
            replay_dbs=replay_dbs,
            notes=notes,
            metadata={"scanner": self.name},
        )
