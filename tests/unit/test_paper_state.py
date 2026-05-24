from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from paper_toolkit.models.paper_state import (
    ArtifactRef,
    Artifacts,
    CompileRunRef,
    FigureArtifact,
    PaperMeta,
    PaperState,
)


def _now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_paper_state_minimal_roundtrip() -> None:
    state = PaperState(
        schema_version="1.0",
        meta=PaperMeta(
            title="Demo",
            venue="nature",
            language="en",
            created_at=_now(),
            workspace_root="/tmp/demo",
        ),
        artifacts=Artifacts(),
    )
    data = state.model_dump(mode="json")
    restored = PaperState.model_validate(data)
    assert restored == state


def test_paper_state_with_artifacts() -> None:
    state = PaperState(
        schema_version="1.0",
        meta=PaperMeta(
            title="Demo",
            venue="nature",
            language="en",
            created_at=_now(),
            workspace_root="/tmp/demo",
        ),
        artifacts=Artifacts(
            sections={
                "intro": ArtifactRef(
                    path="paper/sections/intro.tex",
                    updated_at=_now(),
                    checksum="a" * 64,
                ),
            },
            figures=[
                FigureArtifact(
                    id="fig1",
                    src="/tmp/demo/figures4papers/raw.png",
                    packed="paper/figures/fig1.pdf",
                    caption="An example figure.",
                    referenced_by=["intro"],
                ),
            ],
            compile_runs=[
                CompileRunRef(
                    id="r1",
                    ok=True,
                    error_count=0,
                    warning_count=1,
                    pdf="paper/compile_runs/r1/main.pdf",
                    started_at=_now(),
                    finished_at=_now(),
                ),
            ],
        ),
    )
    data = state.model_dump(mode="json")
    restored = PaperState.model_validate(data)
    assert restored.artifacts.sections["intro"].path == "paper/sections/intro.tex"
    assert restored.artifacts.figures[0].id == "fig1"
    assert restored.artifacts.compile_runs[0].ok is True


def test_paper_state_rejects_bad_schema_version() -> None:
    with pytest.raises(ValidationError):
        PaperState(
            schema_version="2.0",  # type: ignore[arg-type]
            meta=PaperMeta(
                title="Demo",
                venue="nature",
                language="en",
                created_at=_now(),
                workspace_root="/tmp/demo",
            ),
            artifacts=Artifacts(),
        )


def test_paper_meta_rejects_unknown_language() -> None:
    with pytest.raises(ValidationError):
        PaperMeta(
            title="Demo",
            venue="nature",
            language="fr",  # type: ignore[arg-type]
            created_at=_now(),
            workspace_root="/tmp/demo",
        )
