"""IO helpers that survive crashes mid-write.

`write_atomic_text` writes to a sibling temp file and uses `os.replace` (atomic on
POSIX and Windows when on the same filesystem) so a crash during write never
leaves a half-truncated `paper.json` / `evidence_graph.json` / etc.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_atomic_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Atomically write `content` to `path`.

    Strategy: write to a temp file in the same directory, fsync, then `os.replace`.
    Same-filesystem rename is atomic across POSIX and Windows; this avoids the
    truncated-write window of `Path.write_text`.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
