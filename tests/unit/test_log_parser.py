from pathlib import Path

from paper_toolkit.typeset.log_parser import parse_latex_log

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_compile.log"


def test_parse_latex_log_extracts_structured_errors_and_warnings() -> None:
    parsed = parse_latex_log(FIXTURE.read_text(encoding="utf-8"))

    error_codes = [e.code for e in parsed.errors]
    assert "missing-citation" in error_codes
    assert "undefined-ref" in error_codes
    assert "missing-file" in error_codes
    assert "package" in error_codes
    assert "syntax" in error_codes

    warning_codes = [w.code for w in parsed.warnings]
    assert "overfull-hbox" in warning_codes
    assert "underfull-vbox" in warning_codes

    missing_citations = [e for e in parsed.errors if e.code == "missing-citation"]
    cite_keys = {e.message for e in missing_citations}
    assert any("smith2020" in m for m in cite_keys)
    # natbib emits "Package natbib Warning: Citation ..." instead of "LaTeX Warning:".
    assert any("levy2021" in m and "Package natbib Warning" in m for m in cite_keys)

    # The aggregate "There were undefined citations." summary must not be emitted
    # as a separate error — per-citation entries above already cover it.
    assert not any("There were undefined citations" in e.message for e in parsed.errors)

    smith = next(e for e in missing_citations if "smith2020" in e.message)
    assert smith.line == 12
    levy = next(e for e in missing_citations if "levy2021" in e.message)
    assert levy.line == 5

    ref = next(e for e in parsed.errors if e.code == "undefined-ref")
    assert ref.line == 30

    missing_files = [e for e in parsed.errors if e.code == "missing-file"]
    # Two distinct missing-file errors: missing .sty package and missing .bbl.
    messages = " | ".join(e.message for e in missing_files)
    assert "missing-package.sty" in messages
    assert "main.bbl" in messages
    bbl = next(e for e in missing_files if "main.bbl" in e.message)
    assert bbl.fixup_hint is not None and "bibtex" in bbl.fixup_hint.lower()


def test_parse_latex_log_unwraps_column_79_wrapped_warnings() -> None:
    # pdflatex hard-wraps long messages at column 79. The parser must reunite them.
    wrapped = (
        "LaTeX Warning: Citation `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0\n"
        "123456789' on page 1 undefined on input line 99.\n"
    )
    parsed = parse_latex_log(wrapped)
    assert len(parsed.errors) == 1
    assert parsed.errors[0].code == "missing-citation"
    assert parsed.errors[0].line == 99


def test_parse_latex_log_matches_package_prefixed_reference_warnings() -> None:
    # hyperref / cleveref emit "Package <name> Warning: Reference ..." variants.
    text = "Package hyperref Warning: Reference `eq:loss' on page 3 undefined on input line 77.\n"
    parsed = parse_latex_log(text)
    assert len(parsed.errors) == 1
    assert parsed.errors[0].code == "undefined-ref"
    assert parsed.errors[0].line == 77


def test_parse_latex_log_attributes_errors_to_current_tex_file() -> None:
    # pdflatex marks file opens with `(/path` and closes with `)`. The parser
    # should attribute errors that occur while a section file is open to that
    # file. The order of opens/closes on a single line matters.
    log = (
        "(./sections/abstract.tex)\n"
        "(./sections/intro.tex\n"
        "Package natbib Warning: Citation `levy2021' on page 1 undefined on input line 5.\n"
        ") (./sections/results.tex\n"
        "Package natbib Warning: Citation `levy2021' on page 1 undefined on input line 4.\n"
        ")\n"
    )
    parsed = parse_latex_log(log)
    cites = [e for e in parsed.errors if e.code == "missing-citation"]
    assert len(cites) == 2
    assert cites[0].file == "./sections/intro.tex"
    assert cites[1].file == "./sections/results.tex"


def test_parse_latex_log_paren_stack_survives_sty_opens_and_closes() -> None:
    # Sty/cls files (no .tex suffix) open and close just like .tex files.
    # The stack must stay balanced so the active .tex attribution survives.
    log = (
        "(./sections/intro.tex\n"
        "(/usr/local/texlive/2026/texmf-dist/tex/latex/base/article.cls\n"
        "Document Class: article\n"
        ")\n"
        "Package natbib Warning: Citation `key' on page 1 undefined on input line 9.\n"
        ")\n"
    )
    parsed = parse_latex_log(log)
    cites = [e for e in parsed.errors if e.code == "missing-citation"]
    assert len(cites) == 1
    assert cites[0].file == "./sections/intro.tex"


def test_parse_latex_log_uses_fixup_hint_table_for_generic_errors() -> None:
    log = "\n".join(
        [
            "! Misplaced alignment tab character &.",
            "! Package amsmath Error: Missing $ inserted.",  # intercepted by package matcher
            "! Undefined control sequence.",
            "! LaTeX Error: \\begin{figure} ended by \\end{document}.",
        ]
    )
    parsed = parse_latex_log(log)
    by_msg = {e.message: e for e in parsed.errors}

    align = next(e for e in parsed.errors if "alignment tab" in e.message)
    assert align.fixup_hint is not None and "\\&" in align.fixup_hint

    undef = next(e for e in parsed.errors if "Undefined control sequence" in e.message)
    assert undef.code == "syntax"
    assert undef.fixup_hint is not None and "package" in undef.fixup_hint.lower()

    ended = next(e for e in parsed.errors if "ended by" in e.message)
    assert ended.fixup_hint is not None and "\\begin" in ended.fixup_hint
    # Package errors still take their dedicated branch.
    pkg = next(e for e in parsed.errors if e.code == "package")
    assert "amsmath" in pkg.fixup_hint  # type: ignore[operator]
    # Suppress unused warning from by_msg helper (kept for future readability).
    assert by_msg


def test_parse_latex_log_classifies_unknown_tex_error_as_other() -> None:
    parsed = parse_latex_log("! This is an unfamiliar TeX failure.\n")
    assert len(parsed.errors) == 1
    assert parsed.errors[0].code == "other"


def test_parse_latex_log_ignores_blank_input() -> None:
    parsed = parse_latex_log("")
    assert parsed.errors == []
    assert parsed.warnings == []
