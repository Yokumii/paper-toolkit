"""Tests for the OpenAlex adapter using a canned JSON response."""

from __future__ import annotations

import json

from paper_toolkit.lit.http_client import HttpResponse
from paper_toolkit.lit.openalex import (
    _build_search_url,
    _reconstruct_abstract,
    fetch_openalex_doi,
    parse_work,
    search_openalex,
)

_WORK = {
    "id": "https://openalex.org/W123",
    "title": "Cross-cutting news exposure",
    "publication_year": 2022,
    "doi": "https://doi.org/10.0000/example.0002",
    "type": "journal-article",
    "primary_location": {"source": {"display_name": "Nature Communications"}},
    "authorships": [
        {"author": {"display_name": "Ro'ee Levy"}},
        {"author": {"display_name": "Co Author"}},
    ],
    "abstract_inverted_index": {
        "We": [0],
        "find": [1],
        "that": [2],
        "exposure": [3],
    },
}


def test_reconstruct_abstract_orders_words_by_position() -> None:
    text = _reconstruct_abstract({"first": [0, 3], "second": [1], "third": [2]})
    assert text == "first second third first"


def test_parse_work_extracts_core_fields() -> None:
    entry = parse_work(_WORK)
    assert entry.source == "openalex"
    assert entry.source_id == "https://openalex.org/W123"
    assert entry.title == "Cross-cutting news exposure"
    assert entry.year == 2022
    assert entry.venue == "Nature Communications"
    assert entry.doi == "10.0000/example.0002"
    assert entry.url == "https://doi.org/10.0000/example.0002"
    assert entry.entry_type == "article"
    assert entry.authors == ["Ro'ee Levy", "Co Author"]
    assert entry.abstract == "We find that exposure"
    assert entry.cite_key.startswith("levy2022_")


def test_build_search_url_includes_per_page_and_filters() -> None:
    url = _build_search_url(query="news", limit=20, year_from=2018, year_to=2021)
    assert "per_page=20" in url
    assert "from_publication_date%3A2018-01-01" in url
    assert "to_publication_date%3A2021-12-31" in url


def test_search_openalex_with_injected_client() -> None:
    def fake_client(url: str, headers: dict[str, str]) -> HttpResponse:
        payload = {"results": [_WORK, _WORK]}
        return HttpResponse(
            url=url,
            status=200,
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

    entries = search_openalex(query="news", limit=2, client=fake_client)
    assert len(entries) == 2


def test_fetch_openalex_doi_strips_https_prefix_in_url() -> None:
    captured: list[str] = []

    def fake_client(url: str, headers: dict[str, str]) -> HttpResponse:
        captured.append(url)
        return HttpResponse(
            url=url,
            status=200,
            body=json.dumps(_WORK).encode("utf-8"),
            content_type="application/json",
        )

    entry = fetch_openalex_doi(doi="10.0000/example.0002", client=fake_client)
    assert captured and "https://doi.org/10.0000/example.0002" in captured[0]
    assert entry.doi == "10.0000/example.0002"
