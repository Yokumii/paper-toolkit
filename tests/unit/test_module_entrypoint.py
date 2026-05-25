"""`python -m paper_toolkit` must invoke the same Typer app as the console script."""

from __future__ import annotations

import subprocess
import sys


def test_python_dash_m_paper_toolkit_runs_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "paper_toolkit", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "paper" in result.stdout.lower()
    assert "Deterministic CLI" in result.stdout


def test_python_dash_m_paper_toolkit_runs_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "paper_toolkit", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
