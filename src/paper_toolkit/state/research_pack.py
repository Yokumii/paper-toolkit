"""Persistence helpers for paper/research_pack.json."""

from __future__ import annotations

import json
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.research_pack import ResearchPack
from paper_toolkit.paths import WorkspacePaths


def exists(*, workspace: Path) -> bool:
    return WorkspacePaths(workspace=workspace).research_pack.exists()


def load(*, workspace: Path) -> ResearchPack:
    path = WorkspacePaths(workspace=workspace).research_pack
    if not path.exists():
        raise FileNotFoundError(f"research_pack.json not found at {path}")
    return ResearchPack.model_validate_json(path.read_text(encoding="utf-8"))


def save(*, workspace: Path, pack: ResearchPack) -> None:
    path = WorkspacePaths(workspace=workspace).research_pack
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(
        path,
        json.dumps(pack.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
    )
