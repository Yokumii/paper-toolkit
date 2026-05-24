import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app
from paper_toolkit.models.compile_run import CompileRunResult, PageInfo


def _write_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "paper" / "compile_runs" / "r1"
    pages_dir = run_dir / "pages"
    pages_dir.mkdir(parents=True)
    result = CompileRunResult(
        id="r1",
        ok=True,
        pdf_path=None,
        log_path="paper/compile_runs/r1/main.log",
        errors=[],
        warnings=[],
        pages=[
            PageInfo(
                page_number=1, png_path="paper/compile_runs/r1/pages/page-001.png", elements=[]
            )
        ],
        attempt_index=1,
        duration_seconds=0.1,
    )
    (run_dir / "run.json").write_text(json.dumps(result.model_dump(mode="json")), encoding="utf-8")
    (pages_dir / "elements.json").write_text(
        json.dumps([p.model_dump(mode="json") for p in result.pages]), encoding="utf-8"
    )


def test_cli_page_count_and_elements(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )
    _write_run(tmp_path)

    count = runner.invoke(app, ["page", "count", "--run", "r1", "--workspace", str(tmp_path)])
    assert count.exit_code == 0
    assert json.loads(count.stdout)["result"]["page_count"] == 1

    elements = runner.invoke(
        app, ["page", "elements", "--run", "r1", "--page", "1", "--workspace", str(tmp_path)]
    )
    assert elements.exit_code == 0
    assert json.loads(elements.stdout)["result"]["page_number"] == 1


def test_cli_page_render_reports_missing_run(tmp_path: Path) -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )
    result = runner.invoke(app, ["page", "render", "--run", "r99", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "PAGE_RUN_NOT_FOUND"


def test_cli_page_render_emits_envelope_without_pdf(tmp_path: Path) -> None:
    """`paper page render` against a run without a PDF must still return an envelope."""
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)]).exit_code == 0
    )
    run_dir = tmp_path / "paper" / "compile_runs" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "main.aux").write_text("\\newlabel{fig:foo}{{1}{1}{\\relax}}\n", encoding="utf-8")

    result = runner.invoke(app, ["page", "render", "--run", "r1", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["action"] == "page.render"
    # Without a PDF, the aux-based fallback still surfaces page 1 with the label.
    assert payload["result"]["total_pages"] == 1
    assert payload["result"]["pages"][0]["elements"][0]["label"] == "fig:foo"
