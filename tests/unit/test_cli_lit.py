"""CLI integration tests for `paper lit ...` with mocked HTTP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from paper_toolkit.cli.main import app
from paper_toolkit.lit import arxiv, crossref, openalex
from paper_toolkit.lit.http_client import HttpResponse


def _init_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)])


def _atom_payload() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.01234v1</id>
    <published>2024-01-12T00:00:00Z</published>
    <title>An agent-based study of news exposure</title>
    <summary>Abstract.</summary>
    <author><name>Ada Lovelace</name></author>
    <arxiv:primary_category term="cs.SI"/>
  </entry>
</feed>
"""


def _crossref_payload() -> bytes:
    item = {
        "DOI": "10.1126/science.aap9559",
        "title": ["Sleep deprivation impairs cognition"],
        "author": [{"given": "Matthew", "family": "Walker"}],
        "issued": {"date-parts": [[2018]]},
        "container-title": ["Science"],
        "type": "journal-article",
        "URL": "https://science.example.org/aap9559",
    }
    return json.dumps({"status": "ok", "message": {"items": [item]}}).encode("utf-8")


def _crossref_single_payload() -> bytes:
    item = {
        "DOI": "10.1126/science.aap9559",
        "title": ["Sleep deprivation impairs cognition"],
        "author": [{"given": "Matthew", "family": "Walker"}],
        "issued": {"date-parts": [[2018]]},
        "container-title": ["Science"],
        "type": "journal-article",
    }
    return json.dumps({"status": "ok", "message": item}).encode("utf-8")


def _install_fake_clients(monkeypatch: Any) -> None:
    """Force every adapter to use a deterministic in-process HTTP fake."""

    def fake_arxiv_get(url: str, headers: dict[str, str]) -> HttpResponse:
        return HttpResponse(
            url=url, status=200, body=_atom_payload(), content_type="application/atom+xml"
        )

    def fake_crossref_get(url: str, headers: dict[str, str]) -> HttpResponse:
        if "works/" in url and "?" not in url.split("works/")[1]:
            body = _crossref_single_payload()
        else:
            body = _crossref_payload()
        return HttpResponse(url=url, status=200, body=body, content_type="application/json")

    def fake_openalex_get(url: str, headers: dict[str, str]) -> HttpResponse:
        work = {
            "id": "https://openalex.org/W123",
            "title": "News exposure",
            "publication_year": 2022,
            "doi": "https://doi.org/10.0000/example",
            "type": "journal-article",
            "primary_location": {"source": {"display_name": "Nature"}},
            "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
            "abstract_inverted_index": {"hello": [0]},
        }
        if url.endswith("/W123") or "https://doi.org/" in url:
            body = json.dumps(work).encode("utf-8")
        else:
            body = json.dumps({"results": [work]}).encode("utf-8")
        return HttpResponse(url=url, status=200, body=body, content_type="application/json")

    monkeypatch.setattr(arxiv, "default_http_get", fake_arxiv_get, raising=False)
    monkeypatch.setattr(crossref, "default_http_get", fake_crossref_get, raising=False)
    monkeypatch.setattr(openalex, "default_http_get", fake_openalex_get, raising=False)
    # The polite_get wrapper resolves `default_http_get` via the http_client module
    # at call time; override there too to be safe.
    from paper_toolkit.lit import http_client

    def dispatch(url: str, headers: dict[str, str]) -> HttpResponse:
        if "arxiv.org" in url:
            return fake_arxiv_get(url, headers)
        if "crossref.org" in url:
            return fake_crossref_get(url, headers)
        if "openalex.org" in url:
            return fake_openalex_get(url, headers)
        raise AssertionError(f"unexpected URL in test: {url}")

    monkeypatch.setattr(http_client, "default_http_get", dispatch)


def test_lit_search_arxiv_writes_jsonl(tmp_path: Path, monkeypatch: Any) -> None:
    _init_workspace(tmp_path)
    _install_fake_clients(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "lit",
            "search",
            "--source",
            "arxiv",
            "--query",
            "news exposure",
            "--limit",
            "1",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["count"] == 1
    out_path = Path(payload["result"]["out_path"])
    assert out_path.is_file()
    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[0])
    assert record["source"] == "arxiv"
    assert record["cite_key"].startswith("lovelace2024_")


def test_lit_fetch_doi_crossref_writes_single_entry(tmp_path: Path, monkeypatch: Any) -> None:
    _init_workspace(tmp_path)
    _install_fake_clients(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "lit",
            "fetch-doi",
            "--doi",
            "10.1126/science.aap9559",
            "--source",
            "crossref",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["title"].startswith("Sleep deprivation")


def test_lit_to_bibtex_returns_bibtex_inline_when_no_out(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    jsonl = tmp_path / "paper" / "lit" / "demo.jsonl"
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl.write_text(
        json.dumps(
            {
                "source": "crossref",
                "source_id": "x",
                "title": "Demo",
                "authors": ["Doe, Jane"],
                "year": 2024,
                "venue": "J",
                "doi": "10.0000/x",
                "url": None,
                "abstract": None,
                "entry_type": "article",
                "cite_key": "doe2024_a001",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["lit", "to-bibtex", "--input", str(jsonl), "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "@article{doe2024_a001," in payload["result"]["bibtex"]


def test_lit_merge_bib_appends_and_dedupes(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    # Seed refs.bib with one existing entry.
    bib = tmp_path / "paper" / "refs.bib"
    bib.write_text("@article{doe2024_a001,\n  title = {Old}\n}\n", encoding="utf-8")
    jsonl = tmp_path / "paper" / "lit" / "demo.jsonl"
    payload_lines = []
    for cite_key, title in (("doe2024_a001", "Dup"), ("doe2024_b002", "New")):
        payload_lines.append(
            json.dumps(
                {
                    "source": "crossref",
                    "source_id": cite_key,
                    "title": title,
                    "authors": ["Doe, Jane"],
                    "year": 2024,
                    "venue": "J",
                    "doi": f"10.0000/{cite_key}",
                    "url": None,
                    "abstract": None,
                    "entry_type": "article",
                    "cite_key": cite_key,
                }
            )
        )
    jsonl.write_text("\n".join(payload_lines) + "\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["lit", "merge-bib", "--input", str(jsonl), "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["result"]["added"] == ["doe2024_b002"]
    assert payload["result"]["skipped"] == ["doe2024_a001"]


def test_lit_search_unknown_source_returns_error(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "lit",
            "search",
            "--source",
            "scholar",
            "--query",
            "x",
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "LIT_UNKNOWN_SOURCE"
