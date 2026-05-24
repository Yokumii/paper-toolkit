from pathlib import Path

from paper_toolkit.template import expand_template, list_templates, render_slot_placeholder


def test_render_slot_placeholder_keeps_guidance_as_comment() -> None:
    rendered = render_slot_placeholder(
        '{{slot:hook | kind=prose, words=80-120, guidance="Open with a puzzle."}}'
    )

    assert "% slot: hook" in rendered
    assert "% kind: prose" in rendered
    assert "% words: 80-120" in rendered
    assert "% guidance: Open with a puzzle." in rendered
    assert "\\textbf{[hook]}" in rendered


def test_expand_builtin_intro_template_contains_guidance_comments(tmp_path: Path) -> None:
    out = expand_template(workspace=tmp_path, section="intro", target=None)

    assert out.path == (tmp_path / "paper" / "sections" / "intro.tex").resolve()
    text = out.path.read_text(encoding="utf-8")
    assert "\\section{Introduction}" in text
    assert "% slot: hook" in text
    assert "{{slot:" not in text


def test_workspace_template_overrides_builtin(tmp_path: Path) -> None:
    override = tmp_path / "paper" / "templates" / "sections"
    override.mkdir(parents=True)
    (override / "intro.tex").write_text(
        "\\section{Custom}\n{{slot:custom | kind=prose}}\n", encoding="utf-8"
    )

    out = expand_template(workspace=tmp_path, section="intro", target=None)

    assert "\\section{Custom}" in out.path.read_text(encoding="utf-8")
    assert "% slot: custom" in out.path.read_text(encoding="utf-8")


def test_list_templates_includes_builtin_and_workspace_override(tmp_path: Path) -> None:
    override = tmp_path / "paper" / "templates" / "sections"
    override.mkdir(parents=True)
    (override / "custom.tex").write_text("\\section{Custom}\n", encoding="utf-8")

    names = list_templates(workspace=tmp_path)

    assert "intro" in names
    assert "custom" in names
