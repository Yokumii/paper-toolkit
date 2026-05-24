from paper_toolkit.models.check_report import CheckIssue, CheckReport, Severity, merge_reports


def test_check_report_ok_is_false_when_errors_exist() -> None:
    report = CheckReport(
        checker="style",
        issues=[
            CheckIssue(
                severity="error",
                code="STYLE_BANNED_PHRASE",
                message="Banned phrase found.",
                location="paper/sections/intro.tex:1",
                fixup_hint="Replace the phrase.",
            )
        ],
    )

    assert report.ok is False
    assert report.error_count == 1
    assert report.warning_count == 0


def test_check_report_ok_is_true_with_warnings_only() -> None:
    report = CheckReport(
        checker="word-count",
        issues=[CheckIssue(severity="warning", code="WORD_COUNT_LOW", message="Too short.")],
    )

    assert report.ok is True
    assert report.error_count == 0
    assert report.warning_count == 1


def test_merge_reports_combines_issues() -> None:
    merged = merge_reports(
        checker="all",
        reports=[
            CheckReport(checker="style"),
            CheckReport(
                checker="citations",
                issues=[CheckIssue(severity="error", code="CITE_MISSING", message="Missing.")],
            ),
        ],
    )

    assert merged.checker == "all"
    assert merged.ok is False
    assert merged.error_count == 1
    assert merged.result["checkers"] == ["style", "citations"]


def test_severity_literal_alias() -> None:
    value: Severity = "warning"
    assert value == "warning"
