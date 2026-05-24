from pathlib import Path

from paper_toolkit.compose.latex_assembly import (
    _latex_escape,
    _read_abstract_body,
    copy_template_assets,
    discover_sections,
    render_main_tex,
    write_main_tex,
)


def test_discover_sections_returns_existing_tex_files_in_stable_order(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    (sections / "results.tex").write_text("\\section{Results}\n", encoding="utf-8")
    (sections / "intro.tex").write_text("\\section{Introduction}\n", encoding="utf-8")

    discovered = discover_sections(workspace=tmp_path)

    assert discovered == ["intro", "results"]


def test_render_main_tex_uses_sn_jnl_class_and_inputs_sections() -> None:
    rendered = render_main_tex(title="Demo", sections=["intro", "results"], include_bib=True)

    assert "\\documentclass[pdflatex,sn-nature]{sn-jnl}" in rendered
    assert "\\title{Demo}" in rendered
    assert "\\maketitle" in rendered
    assert "\\input{sections/intro.tex}" in rendered
    assert "\\input{sections/results.tex}" in rendered
    assert "\\bibliography{refs}" in rendered
    # sn-jnl picks the bst from the class option, so we do not emit an
    # explicit \bibliographystyle line.
    assert "\\bibliographystyle" not in rendered
    assert "markdown" not in rendered.lower()


def test_render_main_tex_emits_abstract_in_preamble_not_as_input() -> None:
    rendered = render_main_tex(
        title="Demo",
        sections=["abstract", "intro"],
        include_bib=False,
        abstract_body="A short summary.",
    )

    assert "\\abstract{A short summary.}" in rendered
    # abstract is consumed into the preamble; it must not be \input'd.
    assert "\\input{sections/abstract.tex}" not in rendered
    assert "\\input{sections/intro.tex}" in rendered


def test_render_main_tex_omits_abstract_block_when_body_missing() -> None:
    rendered = render_main_tex(
        title="Demo", sections=["intro"], include_bib=False, abstract_body=None
    )

    assert "\\abstract{" not in rendered


def test_read_abstract_body_extracts_inside_environment(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    (sections / "abstract.tex").write_text(
        "\\begin{abstract}\nSummary body.\n\\end{abstract}\n", encoding="utf-8"
    )

    body = _read_abstract_body(workspace=tmp_path)

    assert body == "Summary body."


def test_read_abstract_body_falls_back_to_whole_file_without_environment(
    tmp_path: Path,
) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    (sections / "abstract.tex").write_text("Plain summary.\n", encoding="utf-8")

    body = _read_abstract_body(workspace=tmp_path)

    assert body == "Plain summary."


def test_write_main_tex_writes_tex_and_copies_template_assets(tmp_path: Path) -> None:
    (tmp_path / "paper" / "sections").mkdir(parents=True)
    (tmp_path / "paper" / "sections" / "intro.tex").write_text(
        "\\section{Intro}\n", encoding="utf-8"
    )
    (tmp_path / "paper" / "sections" / "abstract.tex").write_text(
        "\\begin{abstract}\nShort body.\n\\end{abstract}\n", encoding="utf-8"
    )
    (tmp_path / "paper" / "refs.bib").write_text("@misc{x,\n  title={X}\n}\n", encoding="utf-8")

    out = write_main_tex(workspace=tmp_path, title="Demo")

    assert out == (tmp_path / "paper" / "main.tex").resolve()
    text = out.read_text(encoding="utf-8")
    assert "\\documentclass[pdflatex,sn-nature]{sn-jnl}" in text
    assert "\\abstract{Short body.}" in text
    assert "\\input{sections/intro.tex}" in text
    assert "\\bibliography{refs}" in text
    # Template assets must be copied alongside main.tex for pdflatex/bibtex.
    assert (tmp_path / "paper" / "sn-jnl.cls").is_file()
    assert (tmp_path / "paper" / "sn-nature.bst").is_file()


def test_copy_template_assets_is_idempotent(tmp_path: Path) -> None:
    first = copy_template_assets(workspace=tmp_path)
    sizes_first = {p.name: p.stat().st_size for p in first}
    second = copy_template_assets(workspace=tmp_path)
    sizes_second = {p.name: p.stat().st_size for p in second}

    assert sizes_first == sizes_second
    assert {p.name for p in second} == {"sn-jnl.cls", "sn-nature.bst"}


def test_latex_escape_handles_tilde_and_caret() -> None:
    # ~ and ^ are LaTeX active characters and must be escaped via text commands
    # (plain \~ / \^ are accent commands that swallow the next char).
    assert _latex_escape("a~b") == "a\\textasciitilde{}b"
    assert _latex_escape("a^b") == "a\\textasciicircum{}b"
    # Composite: escape order must not double-escape backslash from the new commands.
    out = _latex_escape("a&b~c^d")
    assert "\\&" in out
    assert "\\textasciitilde{}" in out
    assert "\\textasciicircum{}" in out
    # The text commands themselves should not have been re-escaped (no \\textbackslash inserted).
    assert "\\textbackslash" not in out
