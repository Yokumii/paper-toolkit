"""Unit tests for the script-backed figure renderer."""

from __future__ import annotations

from pathlib import Path

import pytest

from paper_toolkit.figures.script_backend import run_script_backend
from paper_toolkit.models.figure_spec import ScriptFigureSpec


def _seed_workspace(tmp_path: Path) -> Path:
    (tmp_path / "paper" / "figures").mkdir(parents=True)
    (tmp_path / "paper" / "figure_specs").mkdir(parents=True)
    return tmp_path


def test_script_backend_runs_python_figure_script_and_validates_outputs(
    tmp_path: Path,
) -> None:
    workspace = _seed_workspace(tmp_path)
    script = tmp_path / "paper" / "figure_specs" / "emit_demo.py"
    script.write_text(
        """
from pathlib import Path
import sys

import matplotlib.pyplot as plt


def main(out_dir: str) -> None:
    out = Path(out_dir)
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    fig.savefig(out / "fig_script.pdf")
    fig.savefig(out / "fig_script.svg")
    plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
""".strip(),
        encoding="utf-8",
    )

    result = run_script_backend(
        script_path=script,
        backend="python",
        workspace=workspace,
        figure_id="fig_script",
        spec=ScriptFigureSpec(
            id="fig_script",
            caption="Script figure",
            backend="python",
            entrypoint="emit_demo.py",
            data=[],
        ),
    )

    assert result["pdf_path"].name == "fig_script.pdf"
    assert result["svg_path"].name == "fig_script.svg"
    assert result["pdf_path"].is_file()
    assert result["svg_path"].is_file()


def test_script_backend_exposes_figure_contract_env_vars(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    script = tmp_path / "paper" / "figure_specs" / "emit_env.py"
    script.write_text(
        """
from pathlib import Path
import json
import os
import sys

import matplotlib.pyplot as plt


def main(out_dir: str) -> None:
    out = Path(out_dir)
    payload = {
        "figure_id": os.environ["PAPER_FIGURE_ID"],
        "output_dir": os.environ["PAPER_FIGURE_OUTPUT_DIR"],
        "width": os.environ["PAPER_FIGURE_WIDTH"],
        "palette": os.environ["PAPER_FIGURE_PALETTE"],
        "caption": os.environ["PAPER_FIGURE_CAPTION"],
    }
    (out / "env.json").write_text(json.dumps(payload), encoding="utf-8")
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    fig.savefig(out / "fig_env.pdf")
    fig.savefig(out / "fig_env.svg")
    plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
""".strip(),
        encoding="utf-8",
    )

    run_script_backend(
        script_path=script,
        backend="python",
        workspace=workspace,
        figure_id="fig_env",
        spec=ScriptFigureSpec(
            id="fig_env",
            caption="Environment contract",
            backend="python",
            entrypoint="emit_env.py",
            width="double",
            palette="nature_material",
            data=[],
        ),
    )

    payload = (workspace / "paper" / "figures" / "env.json").read_text(encoding="utf-8")
    assert '"figure_id": "fig_env"' in payload
    assert '"width": "double"' in payload
    assert '"palette": "nature_material"' in payload


def test_script_backend_raises_when_outputs_missing(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    script = tmp_path / "paper" / "figure_specs" / "emit_broken.py"
    script.write_text(
        """
import sys


def main(out_dir: str) -> None:
    return None


if __name__ == "__main__":
    main(sys.argv[1])
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError):
        run_script_backend(
            script_path=script,
            backend="python",
            workspace=workspace,
            figure_id="fig_script",
            spec=ScriptFigureSpec(
                id="fig_script",
                caption="Broken script",
                backend="python",
                entrypoint="emit_broken.py",
                data=[],
            ),
        )
