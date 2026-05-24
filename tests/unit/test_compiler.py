from pathlib import Path

from paper_toolkit.typeset.compiler import compile_once, next_run_id


def test_next_run_id_counts_existing_runs(tmp_path: Path) -> None:
    (tmp_path / "paper" / "compile_runs" / "r1").mkdir(parents=True)
    (tmp_path / "paper" / "compile_runs" / "r2").mkdir()

    assert next_run_id(workspace=tmp_path) == "r3"


def test_compile_once_records_missing_engine_as_structured_error(tmp_path: Path) -> None:
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}\n", encoding="utf-8"
    )

    result = compile_once(workspace=tmp_path, engine="definitely-missing-engine")

    assert result.id == "r1"
    assert result.ok is False
    assert result.errors[0].code == "missing-engine"
    assert (tmp_path / "paper" / "compile_runs" / "r1" / "run.json").exists()


def test_compile_once_with_fake_runner_writes_successful_run(tmp_path: Path) -> None:
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}\n", encoding="utf-8"
    )

    def fake_runner(command: list[str], cwd: Path) -> tuple[int, str, str]:
        if "-output-directory" in command:
            run_dir = Path(command[command.index("-output-directory") + 1])
        else:
            run_dir = tmp_path / "paper" / "compile_runs" / "r1"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "main.pdf").write_bytes(b"%PDF-1.4\n% fake\n")
        (run_dir / "main.log").write_text("", encoding="utf-8")
        return 0, "", ""

    result = compile_once(workspace=tmp_path, engine="pdflatex", runner=fake_runner)

    assert result.ok is True
    assert result.pdf_path == "paper/compile_runs/r1/main.pdf"
    assert result.log_path == "paper/compile_runs/r1/main.log"
