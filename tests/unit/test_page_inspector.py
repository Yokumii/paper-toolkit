import json
from pathlib import Path

from paper_toolkit.models.compile_run import CompileRunResult, PageElement, PageInfo
from paper_toolkit.typeset.page_inspector import (
    count_pages,
    load_page_elements,
    overflow_elements,
    parse_aux,
    parse_page_range,
    render_compile_pages,
)


def _write_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "paper" / "compile_runs" / "r1"
    pages_dir = run_dir / "pages"
    pages_dir.mkdir(parents=True)
    result = CompileRunResult(
        id="r1",
        ok=True,
        pdf_path="paper/compile_runs/r1/main.pdf",
        log_path="paper/compile_runs/r1/main.log",
        errors=[],
        warnings=[],
        pages=[
            PageInfo(
                page_number=1,
                png_path="paper/compile_runs/r1/pages/page-001.png",
                elements=[
                    PageElement(
                        kind="figure",
                        label="fig1",
                        bbox=(0, 0, 100, 100),
                        text_preview="Fig 1",
                        overflow=True,
                    )
                ],
            ),
            PageInfo(
                page_number=2,
                png_path="paper/compile_runs/r1/pages/page-002.png",
                elements=[],
            ),
        ],
        attempt_index=1,
        duration_seconds=0.1,
    )
    (run_dir / "run.json").write_text(json.dumps(result.model_dump(mode="json")), encoding="utf-8")
    (pages_dir / "elements.json").write_text(
        json.dumps([p.model_dump(mode="json") for p in result.pages]), encoding="utf-8"
    )


def test_page_inspector_reads_elements_count_and_overflow(tmp_path: Path) -> None:
    _write_run(tmp_path)

    assert count_pages(workspace=tmp_path, run_id="r1") == 2
    assert load_page_elements(workspace=tmp_path, run_id="r1", page=1)[0].label == "fig1"
    assert overflow_elements(workspace=tmp_path, run_id="r1")[0].label == "fig1"


def test_parse_aux_extracts_labels_and_writefiles() -> None:
    aux = (
        "\\relax\n"
        "\\newlabel{fig:foo}{{1}{1}{\\relax}}\n"
        "\\newlabel{sec:intro}{{1}{1}{\\relax}}\n"
        "\\newlabel{eq:loss}{{2}{3}{\\relax}}\n"
        "\\@writefile{toc}{\\contentsline {section}"
        "{\\numberline {1}Introduction}{1}{}}\n"
        "\\@writefile{lof}{\\contentsline {figure}"
        "{\\numberline {1}{\\ignorespaces An example figure.}}{2}{}}\n"
        "\\@writefile{lot}{\\contentsline {table}"
        "{\\numberline {1}{\\ignorespaces A table.}}{4}{}}\n"
    )
    by_page = parse_aux(aux)
    page1_kinds = {e.kind for e in by_page[1]}
    assert "figure" in page1_kinds
    assert "heading" in page1_kinds
    assert any(e.kind == "equation" for e in by_page[3])
    assert any(e.kind == "table" for e in by_page[4])


def test_parse_page_range_handles_lists_and_ranges() -> None:
    assert parse_page_range("1-3", total=5) == [1, 2, 3]
    assert parse_page_range("1,3,5", total=5) == [1, 3, 5]
    assert parse_page_range("2-4,1", total=5) == [1, 2, 3, 4]
    assert parse_page_range("10", total=5) == []  # out of range filtered
    assert parse_page_range(None, total=3) == [1, 2, 3]


def test_render_compile_pages_writes_elements_json_even_without_pdf(tmp_path: Path) -> None:
    # Synthesize a paper/compile_runs/r1 with .aux but no PDF (pdf2image will be skipped).
    run_dir = tmp_path / "paper" / "compile_runs" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "main.aux").write_text("\\newlabel{fig:foo}{{1}{1}{\\relax}}\n", encoding="utf-8")
    pages = render_compile_pages(run_id="r1", run_dir=run_dir, pdf_path=None)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].elements[0].label == "fig:foo"
    elements_json = run_dir / "pages" / "elements.json"
    assert elements_json.exists()
    payload = json.loads(elements_json.read_text(encoding="utf-8"))
    assert payload[0]["page_number"] == 1


def test_render_compile_pages_handles_missing_aux_gracefully(tmp_path: Path) -> None:
    run_dir = tmp_path / "paper" / "compile_runs" / "r1"
    run_dir.mkdir(parents=True)
    pages = render_compile_pages(run_id="r1", run_dir=run_dir, pdf_path=None)
    assert pages == []
    # elements.json is still written so consumers don't trip on missing file.
    assert (run_dir / "pages" / "elements.json").exists()
