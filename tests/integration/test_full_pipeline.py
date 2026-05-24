from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app
from paper_toolkit.typeset.compiler import compile_once


def test_full_pipeline_with_fake_compile_runner(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )
    assert (
        runner.invoke(
            app,
            ["template", "expand", "--section", "intro", "--workspace", str(tmp_path)],
        ).exit_code
        == 0
    )
    section = tmp_path / "paper" / "sections" / "intro.tex"
    section.write_text("\\section{Intro}\nText \\cite{smith2020}.\n", encoding="utf-8")
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "add-citation",
                "--id",
                "ref1",
                "--cite-key",
                "smith2020",
                "--label",
                "Smith Study",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "add-claim",
                "--id",
                "c1",
                "--label",
                "Supported claim",
                "--section",
                "intro",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "add-evidence",
                "--id",
                "e1",
                "--label",
                "Evidence",
                "--source-kind",
                "stat",
                "--source-ref",
                "s1",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "link",
                "--src",
                "e1",
                "--dst",
                "c1",
                "--kind",
                "supports",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["compose", "write-bib", "--workspace", str(tmp_path)]).exit_code == 0
    assert (
        runner.invoke(app, ["compose", "assemble-latex", "--workspace", str(tmp_path)]).exit_code
        == 0
    )
    assert runner.invoke(app, ["check", "citations", "--workspace", str(tmp_path)]).exit_code == 0

    def fake_runner(command: list[str], cwd: Path) -> tuple[int, str, str]:
        if "-output-directory" in command:
            run_dir = Path(command[command.index("-output-directory") + 1])
        else:
            run_dir = tmp_path / "paper" / "compile_runs" / "r1"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "main.log").write_text("", encoding="utf-8")
        if command[0] == "pdflatex":
            (run_dir / "main.pdf").write_bytes(b"%PDF-1.4\n")
        return 0, "", ""

    result = compile_once(workspace=tmp_path, runner=fake_runner)

    assert result.ok is True
    assert (tmp_path / "paper" / "compile_runs" / "r1" / "main.pdf").exists()
