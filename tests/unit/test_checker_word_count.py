from paper_toolkit.checkers.word_count import check_word_count
from paper_toolkit.models.venue import load_venue


def test_word_count_checker_reports_short_section(tmp_path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    (sections / "intro.tex").write_text("\\section{Intro}\nToo short.\n", encoding="utf-8")

    report = check_word_count(
        workspace=tmp_path,
        venue=load_venue(workspace=tmp_path, venue_name="nature"),
        section="intro",
    )

    assert report.ok is True
    assert report.issues[0].severity == "warning"
    assert report.issues[0].code == "WORD_COUNT_LOW"


def test_word_count_checker_passes_custom_range(tmp_path) -> None:
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "venue.yaml").write_text(
        "name: custom\nsections:\n  - { name: intro, word_range: [2, 5] }\n",
        encoding="utf-8",
    )
    sections = tmp_path / "paper" / "sections"
    sections.mkdir()
    (sections / "intro.tex").write_text("Two words.\n", encoding="utf-8")

    report = check_word_count(
        workspace=tmp_path,
        venue=load_venue(workspace=tmp_path, venue_name="nature"),
        section="intro",
    )

    assert report.ok is True
    assert report.issues == []
