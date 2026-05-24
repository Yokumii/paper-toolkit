import shutil
from pathlib import Path

from paper_toolkit.checkers.style import check_style
from paper_toolkit.models.venue import load_venue

FIXTURES = Path(__file__).parents[1] / "fixtures" / "checker_sections"


def test_style_checker_passes_clean_section(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    shutil.copy2(FIXTURES / "intro_clean.tex", sections / "intro.tex")

    report = check_style(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )

    assert report.ok is True
    assert report.issues == []


def test_style_checker_catches_banned_punct_and_phrases(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    shutil.copy2(FIXTURES / "intro_bad_style.tex", sections / "intro.tex")

    report = check_style(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )

    codes = [issue.code for issue in report.issues]
    assert "STYLE_BANNED_PUNCT" in codes
    assert "STYLE_BANNED_PHRASE" in codes
    assert report.ok is False


def test_style_checker_emits_warning_severity_for_ai_tone(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    # AI-tone phrases should fire at warning severity, not error.
    (sections / "intro.tex").write_text(
        "We delve into the tapestry of multifaceted findings.\n", encoding="utf-8"
    )

    report = check_style(
        workspace=tmp_path, venue=load_venue(workspace=tmp_path, venue_name="nature")
    )

    ai_tone_issues = [i for i in report.issues if i.code == "STYLE_BANNED_PHRASE"]
    assert len(ai_tone_issues) >= 3  # delve, tapestry, multifaceted
    assert all(i.severity == "warning" for i in ai_tone_issues)
    # Warnings should not flip ok=False on their own.
    assert report.ok is True
    assert report.warning_count >= 3
