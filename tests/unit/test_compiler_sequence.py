from pathlib import Path

from paper_toolkit.typeset.compiler import compile_once


def test_compile_once_runs_pdflatex_bibtex_pdflatex_pdflatex_sequence(tmp_path: Path) -> None:
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_runner(command: list[str], cwd: Path) -> tuple[int, str, str]:
        calls.append(command)
        if "-output-directory" in command:
            run_dir = Path(command[command.index("-output-directory") + 1])
        else:
            run_dir = tmp_path / "paper" / "compile_runs" / "r1"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "main.log").write_text("", encoding="utf-8")
        if len(calls) == 4:
            (run_dir / "main.pdf").write_bytes(b"%PDF-1.4\n")
        return 0, "", ""

    result = compile_once(workspace=tmp_path, engine="pdflatex", runner=fake_runner)

    assert result.ok is True
    assert [call[0] for call in calls] == ["pdflatex", "bibtex", "pdflatex", "pdflatex"]
    # bibtex must receive a path relative to paper/ (cwd) to satisfy
    # `openout_any = p` on default TeX Live installs.
    bibtex_call = next(call for call in calls if call[0] == "bibtex")
    assert bibtex_call[1] == "compile_runs/r1/main"


def test_compile_once_tolerates_bibtex_nonzero_exit(tmp_path: Path) -> None:
    """bibtex returning 2 (no \\cite{} in document) must not abort the run."""
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}\n",
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_runner(command: list[str], cwd: Path) -> tuple[int, str, str]:
        calls.append(command[0])
        if "-output-directory" in command:
            run_dir = Path(command[command.index("-output-directory") + 1])
        else:
            run_dir = tmp_path / "paper" / "compile_runs" / "r1"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "main.log").write_text("", encoding="utf-8")
        # Final pdflatex pass creates the PDF.
        if command[0] == "pdflatex" and calls.count("pdflatex") == 3:
            (run_dir / "main.pdf").write_bytes(b"%PDF-1.4\n")
        # bibtex fails with exit 2; sequence must continue.
        if command[0] == "bibtex":
            return 2, "", "I found no \\cite commands"
        return 0, "", ""

    result = compile_once(workspace=tmp_path, engine="pdflatex", runner=fake_runner)

    # All four steps must have run despite bibtex's non-zero exit.
    assert calls == ["pdflatex", "bibtex", "pdflatex", "pdflatex"]
    assert result.ok is True


def test_compile_once_aborts_on_pdflatex_failure(tmp_path: Path) -> None:
    """A non-zero pdflatex return code DOES stop the sequence (unlike bibtex)."""
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}\n",
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_runner(command: list[str], cwd: Path) -> tuple[int, str, str]:
        calls.append(command[0])
        if "-output-directory" in command:
            run_dir = Path(command[command.index("-output-directory") + 1])
        else:
            run_dir = tmp_path / "paper" / "compile_runs" / "r1"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "main.log").write_text("", encoding="utf-8")
        if command[0] == "pdflatex":
            return 1, "", ""
        return 0, "", ""

    result = compile_once(workspace=tmp_path, engine="pdflatex", runner=fake_runner)
    assert calls == ["pdflatex"]  # stopped after the first pdflatex failure
    assert result.ok is False
