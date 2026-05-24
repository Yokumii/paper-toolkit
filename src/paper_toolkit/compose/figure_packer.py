"""Copy selected figure files into paper/figures/."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from paper_toolkit.models.paper_state import FigureArtifact
from paper_toolkit.paths import WorkspacePaths

_NON_SLUG = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass(frozen=True)
class FigurePackItem:
    figure_id: str
    src: Path
    caption: str | None = None
    referenced_by: list[str] = field(default_factory=list)


def _safe_stem(figure_id: str) -> str:
    cleaned = figure_id.removeprefix("fig:")
    cleaned = _NON_SLUG.sub("_", cleaned).strip("_")
    return cleaned or "figure"


def pack_figures(*, workspace: Path, items: list[FigurePackItem]) -> list[FigureArtifact]:
    paths = WorkspacePaths(workspace=workspace)
    paths.figures_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[FigureArtifact] = []
    for item in items:
        src = item.src.expanduser().resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"figure source not found: {src}")
        dest = paths.figures_dir / f"{_safe_stem(item.figure_id)}{src.suffix.lower() or '.dat'}"
        shutil.copy2(src, dest)
        artifacts.append(
            FigureArtifact(
                id=item.figure_id,
                src=str(src),
                packed=paths.relative_to_workspace(dest),
                caption=item.caption,
                referenced_by=list(item.referenced_by),
            )
        )
    return artifacts
