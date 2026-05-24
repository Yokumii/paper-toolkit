from pathlib import Path

import pytest

from paper_toolkit.compose.figure_packer import FigurePackItem, pack_figures
from paper_toolkit.models.paper_state import FigureArtifact


def test_pack_figures_copies_sources_and_returns_artifacts(tmp_path: Path) -> None:
    src = tmp_path / "source" / "alpha.png"
    src.parent.mkdir()
    src.write_text("fake image", encoding="utf-8")

    copied = pack_figures(
        workspace=tmp_path,
        items=[
            FigurePackItem(
                figure_id="fig1",
                src=src,
                caption="Adaptation gap.",
                referenced_by=["results"],
            )
        ],
    )

    assert copied == [
        FigureArtifact(
            id="fig1",
            src=str(src.resolve()),
            packed="paper/figures/fig1.png",
            caption="Adaptation gap.",
            referenced_by=["results"],
        )
    ]
    assert (tmp_path / "paper" / "figures" / "fig1.png").read_text(encoding="utf-8") == "fake image"


def test_pack_figures_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="figure source not found"):
        pack_figures(
            workspace=tmp_path,
            items=[FigurePackItem(figure_id="fig1", src=tmp_path / "missing.png")],
        )
