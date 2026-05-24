"""Shared models for deterministic checker output."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["error", "warning", "info"]


class CheckIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity
    code: str
    message: str
    location: str | None = None
    fixup_hint: str | None = None


class CheckReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checker: str
    issues: list[CheckIssue] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    error_count: int = 0
    warning_count: int = 0
    ok: bool = True

    def model_post_init(self, __context: object) -> None:
        self.error_count = sum(1 for issue in self.issues if issue.severity == "error")
        self.warning_count = sum(1 for issue in self.issues if issue.severity == "warning")
        self.ok = self.error_count == 0


def merge_reports(*, checker: str, reports: list[CheckReport]) -> CheckReport:
    issues = [issue for report in reports for issue in report.issues]
    return CheckReport(
        checker=checker,
        issues=issues,
        result={"checkers": [report.checker for report in reports]},
    )
