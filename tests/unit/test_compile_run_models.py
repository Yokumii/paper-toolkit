from paper_toolkit.models.compile_run import (
    CompileRunResult,
    LatexError,
    LatexWarning,
    PageElement,
    PageInfo,
)


def test_compile_run_result_roundtrip() -> None:
    result = CompileRunResult(
        id="r1",
        ok=False,
        pdf_path=None,
        log_path="paper/compile_runs/r1/main.log",
        errors=[
            LatexError(
                code="missing-citation",
                message="Citation `smith2020' undefined",
                file="paper/main.tex",
                line=12,
                fixup_hint="Add a citation node and rerun compose write-bib.",
            )
        ],
        warnings=[
            LatexWarning(code="overfull-hbox", message="Overfull hbox", file=None, line=None)
        ],
        pages=[
            PageInfo(
                page_number=1,
                png_path="paper/compile_runs/r1/pages/page-001.png",
                elements=[
                    PageElement(
                        kind="heading",
                        label=None,
                        bbox=(0.0, 0.0, 100.0, 20.0),
                        text_preview="Introduction",
                        overflow=False,
                    )
                ],
            )
        ],
        attempt_index=1,
        duration_seconds=0.25,
    )

    restored = CompileRunResult.model_validate(result.model_dump(mode="json"))

    assert restored == result
    assert restored.errors[0].code == "missing-citation"
    assert restored.pages[0].elements[0].bbox == (0.0, 0.0, 100.0, 20.0)
