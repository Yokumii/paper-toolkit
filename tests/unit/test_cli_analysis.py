"""CLI integration tests for `paper analysis ...`.

These walk the full 6-stage pipeline using the tiny SQLite fixture, so the
test asserts both the contracts of each verb AND that the stages compose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

pytest.importorskip("matplotlib")

from paper_toolkit.cli.main import app
from tests.unit._analysis_fixture import build_tiny_sqlite


def _run(args: list[str]) -> tuple[int, dict]:
    runner = CliRunner()
    result = runner.invoke(app, args)
    try:
        return result.exit_code, json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.exit_code, {"_raw": result.stdout, "_stderr": result.stderr}


def _init_paper(tmp_path: Path) -> None:
    code, _ = _run(["init", "--title", "Demo", "--workspace", str(tmp_path)])
    assert code == 0


def test_analysis_list_tables_reports_three_tables(tmp_path: Path) -> None:
    _init_paper(tmp_path)
    db = build_tiny_sqlite(tmp_path / "demo.db")
    code, payload = _run(["analysis", "list-tables", "--db", str(db), "--workspace", str(tmp_path)])
    assert code == 0, payload
    names = {t["name"] for t in payload["result"]["tables"]}
    assert names == {"agent_profile", "agent_status", "agent_dialog"}


def test_analysis_full_pipeline_walks_stage_gates(tmp_path: Path) -> None:
    _init_paper(tmp_path)
    db = build_tiny_sqlite(tmp_path / "demo.db")

    # init / plan / check-plan
    assert (
        _run(
            [
                "analysis",
                "init",
                "--hypothesis-id",
                "h1",
                "--experiment-id",
                "e1",
                "--db",
                str(db),
                "--workspace",
                str(tmp_path),
            ]
        )[0]
        == 0
    )
    plan_payload = tmp_path / "plan.yaml"
    plan_payload.write_text(
        yaml.safe_dump(
            {
                "research_question": "Do agents differ on x?",
                "must_inspect": ["agent_status"],
                "expected_claim_count": 1,
            }
        ),
        encoding="utf-8",
    )
    assert (
        _run(
            [
                "analysis",
                "write-plan",
                "--hypothesis-id",
                "h1",
                "--experiment-id",
                "e1",
                "--payload",
                str(plan_payload),
                "--workspace",
                str(tmp_path),
            ]
        )[0]
        == 0
    )
    code, _ = _run(
        [
            "analysis",
            "check-plan",
            "--hypothesis-id",
            "h1",
            "--experiment-id",
            "e1",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 0

    # profile a table (workspace-bound) -> check-explore should pass
    code, payload = _run(
        [
            "analysis",
            "profile-table",
            "--db",
            str(db),
            "--table",
            "agent_status",
            "--hypothesis-id",
            "h1",
            "--experiment-id",
            "e1",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 0
    assert "out_path" in payload["result"]
    code, _ = _run(
        [
            "analysis",
            "check-explore",
            "--hypothesis-id",
            "h1",
            "--experiment-id",
            "e1",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 0

    # record-claim / check-claims
    assert (
        _run(
            [
                "analysis",
                "record-claim",
                "--hypothesis-id",
                "h1",
                "--experiment-id",
                "e1",
                "--claim-id",
                "growth",
                "--text",
                "Agents drift outward over time.",
                "--kind",
                "quantitative",
                "--evidence",
                "agent_status_profile",
                "--workspace",
                str(tmp_path),
            ]
        )[0]
        == 0
    )
    assert (
        _run(
            [
                "analysis",
                "check-claims",
                "--hypothesis-id",
                "h1",
                "--experiment-id",
                "e1",
                "--workspace",
                str(tmp_path),
            ]
        )[0]
        == 0
    )

    # author a tiny figure spec and render + register
    spec_path = tmp_path / "paper" / "figure_specs" / "fig_growth.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "kind": "bar",
                "id": "fig_growth",
                "caption": "Demo growth",
                "x_field": "arm",
                "y_field": "y",
                "data": [{"arm": "A", "y": 0.3}, {"arm": "B", "y": 0.7}],
            }
        ),
        encoding="utf-8",
    )
    assert (
        _run(["figure", "render", "--spec", str(spec_path), "--workspace", str(tmp_path)])[0] == 0
    )
    assert (
        _run(["figure", "register", "--spec", str(spec_path), "--workspace", str(tmp_path)])[0] == 0
    )
    assert (
        _run(
            [
                "analysis",
                "record-figure-contract",
                "--hypothesis-id",
                "h1",
                "--experiment-id",
                "e1",
                "--claim-id",
                "growth",
                "--figure-id",
                "fig_growth",
                "--rationale",
                "comparison bar",
                "--workspace",
                str(tmp_path),
            ]
        )[0]
        == 0
    )
    code, _ = _run(
        [
            "analysis",
            "check-refine",
            "--hypothesis-id",
            "h1",
            "--experiment-id",
            "e1",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 0

    # build report context + author both reports + check-release
    code, _ = _run(
        [
            "analysis",
            "build-report-context",
            "--hypothesis-id",
            "h1",
            "--experiment-id",
            "e1",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 0
    base = tmp_path / "analysis" / "h1" / "e1"
    assert (base / "report_context.md").exists()
    assert (base / "evidence_index.json").exists()
    (base / "report_zh.md").write_text("# 中文报告\n", encoding="utf-8")
    (base / "report_en.md").write_text("# English report\n", encoding="utf-8")
    code, _ = _run(
        [
            "analysis",
            "check-release",
            "--hypothesis-id",
            "h1",
            "--experiment-id",
            "e1",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 0

    # synthesis: brief + check-synthesis (deferred), then lift, then re-check passes
    assert (
        _run(
            [
                "analysis",
                "build-synthesis-brief",
                "--hypothesis-id",
                "h1",
                "--experiment-id",
                "e1",
                "--workspace",
                str(tmp_path),
            ]
        )[0]
        == 0
    )
    code, _ = _run(
        [
            "analysis",
            "check-synthesis",
            "--hypothesis-id",
            "h1",
            "--workspace",
            str(tmp_path),
        ]
    )
    # not yet lifted -> still fails
    assert code == 1
    assert (
        _run(
            [
                "analysis",
                "lift-to-evidence",
                "--hypothesis-id",
                "h1",
                "--experiment-id",
                "e1",
                "--workspace",
                str(tmp_path),
            ]
        )[0]
        == 0
    )
    code, _ = _run(
        [
            "analysis",
            "check-synthesis",
            "--hypothesis-id",
            "h1",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 0

    # paper check claim-coverage must see the lifted claim
    code, payload = _run(["check", "claim-coverage", "--workspace", str(tmp_path)])
    assert code == 0, payload
    # status reflects the final stage
    code, payload = _run(
        ["analysis", "status", "--hypothesis-id", "h1", "--workspace", str(tmp_path)]
    )
    assert code == 0
    assert payload["result"]["experiments"][0]["stage"] == "synthesis"


def test_query_refuses_select_star(tmp_path: Path) -> None:
    _init_paper(tmp_path)
    db = build_tiny_sqlite(tmp_path / "demo.db")
    code, payload = _run(
        [
            "analysis",
            "query",
            "--db",
            str(db),
            "--sql",
            "SELECT * FROM agent_status",
            "--workspace",
            str(tmp_path),
        ]
    )
    assert code == 1
    assert payload["errors"][0]["code"] == "ANL_QUERY_REFUSED"
