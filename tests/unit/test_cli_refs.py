"""CLI integration tests for `paper refs dedup`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.cli.main import app


def _init_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)])


def test_refs_dedup_reports_doi_duplicates_without_modifying_file(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    bib = tmp_path / "paper" / "refs.bib"
    bib.write_text(
        """
@article{a, title={Old}, doi={10.1/Y}}

@article{b, title={New}, doi={https://doi.org/10.1/Y}, year={2024}}
""",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["refs", "dedup", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["result"]["duplicate_count"] == 1
    assert payload["result"]["applied"] is False
    # The file is untouched without --apply.
    assert bib.read_text(encoding="utf-8").count("@article{a,") == 1
    assert bib.read_text(encoding="utf-8").count("@article{b,") == 1


def test_refs_dedup_apply_rewrites_file_dropping_absorbed_entries(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    bib = tmp_path / "paper" / "refs.bib"
    bib.write_text(
        """
@article{a, title={Old}, doi={10.1/Y}}

@article{b, title={New}, doi={https://doi.org/10.1/Y}, year={2024}}

@misc{c, title={Independent}}
""",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["refs", "dedup", "--apply", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["result"]["applied"] is True
    text_after = bib.read_text(encoding="utf-8")
    # Keeper survives; absorbed entry is dropped; independent entry preserved.
    assert "@article{b," in text_after
    assert "@article{a," not in text_after
    assert "@misc{c," in text_after


def test_refs_dedup_returns_envelope_error_when_bib_missing(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["refs", "dedup", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "REFS_BIB_MISSING"
