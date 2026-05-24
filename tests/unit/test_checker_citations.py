from pathlib import Path

from paper_toolkit.checkers.citations import check_citations


def test_citations_checker_reports_missing_and_unused_keys(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    (sections / "intro.tex").write_text("Text \\cite{smith2020,missing2022}.\n", encoding="utf-8")
    (tmp_path / "paper" / "refs.bib").write_text(
        "@misc{smith2020,\n  title={Smith}\n}\n\n@misc{unused2021,\n  title={Unused}\n}\n",
        encoding="utf-8",
    )

    report = check_citations(workspace=tmp_path)

    assert "CITE_MISSING_BIB_ENTRY" in [issue.code for issue in report.issues]
    assert "CITE_UNUSED_BIB_ENTRY" in [issue.code for issue in report.issues]
    assert report.ok is False


def test_citations_checker_passes_matched_keys(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    (sections / "intro.tex").write_text("Text \\cite{smith2020}.\n", encoding="utf-8")
    (tmp_path / "paper" / "refs.bib").write_text(
        "@misc{smith2020,\n  title={Smith}\n}\n", encoding="utf-8"
    )

    report = check_citations(workspace=tmp_path)

    assert report.ok is True
    assert report.issues == []


def test_citations_checker_matches_natbib_variants(tmp_path: Path) -> None:
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True)
    # natbib emits citep/citet/citealt/citealp/citeauthor/citeyear; the bib only
    # has smith2020, so each variant should surface as CITE_MISSING_BIB_ENTRY
    # except the matched one.
    (sections / "intro.tex").write_text(
        "\n".join(
            [
                "\\citep{smith2020}.",
                "\\citet{jones2021}.",
                "\\citealt{lee2022}.",
                "\\citealp{kim2023}.",
                "\\citeauthor{park2024}.",
                "\\citeyear{wang2025}.",
                "\\citet*{starred2026}.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "paper" / "refs.bib").write_text(
        "@misc{smith2020,\n  title={Smith}\n}\n", encoding="utf-8"
    )

    report = check_citations(workspace=tmp_path)
    missing = [issue.message for issue in report.issues if issue.code == "CITE_MISSING_BIB_ENTRY"]
    for key in ("jones2021", "lee2022", "kim2023", "park2024", "wang2025", "starred2026"):
        assert any(key in m for m in missing), f"missing detection for {key}"
