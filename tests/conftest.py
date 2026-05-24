from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Fresh workspace directory (no paper/ inside yet)."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws
