"""Helpers for script-backed figure generation."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_script_backend(
    *, script_path: Path, backend: str, workspace: Path, figure_id: str
) -> dict[str, Path]:
    """Run a Python or R figure script and verify publication outputs exist."""

    out_dir = workspace / "paper" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    if backend == "python":
        cmd = ["python", str(script_path), str(out_dir)]
    elif backend == "r":
        cmd = ["Rscript", str(script_path), str(out_dir)]
    else:
        raise ValueError(f"unsupported script backend: {backend}")

    subprocess.run(cmd, check=True)

    pdf_path = out_dir / f"{figure_id}.pdf"
    svg_path = out_dir / f"{figure_id}.svg"
    if not pdf_path.exists() or not svg_path.exists():
        raise FileNotFoundError(
            f"script backend did not produce required outputs for {figure_id}: "
            f"{pdf_path.name}, {svg_path.name}"
        )

    return {"pdf_path": pdf_path, "svg_path": svg_path}
