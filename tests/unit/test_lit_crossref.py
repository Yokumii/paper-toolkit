"""Tests for the CrossRef adapter using a canned JSON response."""

from __future__ import annotations

import json

from paper_toolkit.lit.crossref import (
    _build_search_url,
    fetch_crossref_doi,
    parse_work,
    search_crossref,
)
from paper_toolkit.lit.http_client import HttpResponse

_ITEM = {
    "DOI": "10.1126/science.aap9559",
    "title": ["Sleep deprivation impairs cognition"],
    "author": [
        {"given": "Matthew", "family": "Walker"},
        {"given": "Ada", "family": "Smith"},
    ],
    "issued": {"date-parts": [[2018, 5, 1]]},
    "container-title": ["Science"],
    "type": "journal-article",
    "URL": "https://science.example.org/aap9559",
    "abstract": "<jats:p>Important finding.</jats:p>",
}


def test_parse_work_extracts_article_fields() -> None:
    entry = parse_work(_ITEM)
    assert entry.source == "crossref"
    assert entry.title == "Sleep deprivation impairs cognition"
    assert entry.year == 2018
    assert entry.venue == "Science"
    assert entry.entry_type == "article"
    assert entry.doi == "10.1126/science.aap9559"
    assert entry.url == "https://science.example.org/aap9559"
    assert entry.authors == ["Matthew Walker", "Ada Smith"]
    assert entry.abstract == "Important finding."
    assert entry.cite_key.startswith("walker2018_")


def test_parse_work_falls_back_to_misc_for_unknown_type() -> None:
    item = dict(_ITEM)
    item["type"] = "dataset"
    entry = parse_work(item)
    assert entry.entry_type == "misc"


def test_parse_work_routes_proceedings_to_inproceedings() -> None:
    item = dict(_ITEM)
    item["type"] = "proceedings-article"
    entry = parse_work(item)
    assert entry.entry_type == "inproceedings"


def test_build_search_url_includes_year_filter() -> None:
    url = _build_search_url(query="news", limit=5, year_from=2019, year_to=2021)
    assert "from-pub-date%3A2019" in url
    assert "until-pub-date%3A2021" in url


def test_search_crossref_with_injected_client() -> None:
    captured: list[str] = []

    def fake_client(url: str, headers: dict[str, str]) -> HttpResponse:
        captured.append(url)
        payload = {"status": "ok", "message": {"items": [_ITEM, _ITEM]}}
        return HttpResponse(
            url=url,
            status=200,
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

    entries = search_crossref(query="sleep", limit=2, client=fake_client)
    assert len(entries) == 2
    assert captured and "api.crossref.org/works" in captured[0]


def test_fetch_crossref_doi_with_injected_client() -> None:
    def fake_client(url: str, headers: dict[str, str]) -> HttpResponse:
        payload = {"status": "ok", "message": _ITEM}
        return HttpResponse(
            url=url,
            status=200,
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

    entry = fetch_crossref_doi(doi="10.1126/science.aap9559", client=fake_client)
    assert entry.doi == "10.1126/science.aap9559"
