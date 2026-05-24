import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app


def _init_workspace(runner: CliRunner, workspace: Path) -> None:
    result = runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(workspace)])
    assert result.exit_code == 0


def _payload(result) -> dict:
    return json.loads(result.stdout)


def test_cli_evidence_add_validate_topo_and_mermaid(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)

    claim = runner.invoke(
        app,
        [
            "evidence",
            "add-claim",
            "--id",
            "c1",
            "--label",
            "Heterogeneity improves adaptation.",
            "--section",
            "results",
            "--strength",
            "primary",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert claim.exit_code == 0
    assert _payload(claim)["state_summary"]["claim_count"] == 1

    evidence = runner.invoke(
        app,
        [
            "evidence",
            "add-evidence",
            "--id",
            "e1",
            "--label",
            "Adaptation gap statistic.",
            "--source-kind",
            "stat",
            "--source-ref",
            "adaptation_delta",
            "--source-detail",
            "delta=0.08",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert evidence.exit_code == 0
    assert _payload(evidence)["state_summary"]["evidence_count"] == 1

    link = runner.invoke(
        app,
        [
            "evidence",
            "link",
            "--src",
            "e1",
            "--dst",
            "c1",
            "--kind",
            "supports",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert link.exit_code == 0

    validate = runner.invoke(app, ["evidence", "validate", "--workspace", str(tmp_path)])
    assert validate.exit_code == 0
    assert _payload(validate)["ok"] is True
    assert _payload(validate)["state_summary"]["graph_valid"] is True

    topo = runner.invoke(app, ["evidence", "topo-order", "--workspace", str(tmp_path)])
    assert topo.exit_code == 0
    assert _payload(topo)["result"]["order"] == ["c1"]

    mermaid = runner.invoke(app, ["evidence", "render-mermaid", "--workspace", str(tmp_path)])
    assert mermaid.exit_code == 0
    assert "graph TD" in _payload(mermaid)["result"]["mermaid_text"]


def test_cli_evidence_duplicate_node_returns_envelope_error(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    first = runner.invoke(
        app,
        ["evidence", "add-claim", "--id", "c1", "--label", "Claim", "--workspace", str(tmp_path)],
    )
    assert first.exit_code == 0
    second = runner.invoke(
        app,
        ["evidence", "add-claim", "--id", "c1", "--label", "Again", "--workspace", str(tmp_path)],
    )
    assert second.exit_code == 1
    assert _payload(second)["errors"][0]["code"] == "EVD_NODE_EXISTS"


def test_cli_evidence_remove_node_and_edge(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "add-claim",
                "--id",
                "c1",
                "--label",
                "Claim",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "add-evidence",
                "--id",
                "e1",
                "--label",
                "Evidence",
                "--source-kind",
                "stat",
                "--source-ref",
                "s1",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "evidence",
                "link",
                "--src",
                "e1",
                "--dst",
                "c1",
                "--kind",
                "supports",
                "--workspace",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )

    rm_edge = runner.invoke(
        app,
        [
            "evidence",
            "rm-edge",
            "--src",
            "e1",
            "--dst",
            "c1",
            "--kind",
            "supports",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert rm_edge.exit_code == 0
    assert _payload(rm_edge)["result"]["removed"] is True

    rm_node = runner.invoke(
        app, ["evidence", "rm-node", "--id", "e1", "--workspace", str(tmp_path)]
    )
    assert rm_node.exit_code == 0
    assert _payload(rm_node)["result"]["removed"] is True


def test_cli_evidence_add_claim_rejects_bad_strength(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "evidence",
            "add-claim",
            "--id",
            "c1",
            "--label",
            "Claim",
            "--strength",
            "BOGUS",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    assert _payload(result)["errors"][0]["code"] == "EVD_BAD_STRENGTH"


def test_cli_evidence_add_evidence_rejects_bad_source_kind(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "evidence",
            "add-evidence",
            "--id",
            "e1",
            "--label",
            "Ev",
            "--source-kind",
            "wishful",
            "--source-ref",
            "x",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    assert _payload(result)["errors"][0]["code"] == "EVD_BAD_SOURCE_KIND"


def test_cli_evidence_link_rejects_bad_edge_kind(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_workspace(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "evidence",
            "link",
            "--src",
            "a",
            "--dst",
            "b",
            "--kind",
            "implies",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    assert _payload(result)["errors"][0]["code"] == "EVD_BAD_EDGE_KIND"
