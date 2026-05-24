"""Tests for the arXiv adapter using a canned Atom response."""

from __future__ import annotations

from paper_toolkit.lit.arxiv import _build_search_url, parse_atom_feed, search_arxiv
from paper_toolkit.lit.http_client import HttpResponse

_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.01234v1</id>
    <updated>2024-01-12T00:00:00Z</updated>
    <published>2024-01-12T00:00:00Z</published>
    <title>An agent-based study of news exposure</title>
    <summary>Abstract body
    spanning lines.</summary>
    <author><name>Ada Lovelace</name></author>
    <author><name>Charles Babbage</name></author>
    <arxiv:doi>10.0000/example.0001</arxiv:doi>
    <arxiv:primary_category term="cs.SI"/>
    <link title="pdf"
          href="http://arxiv.org/pdf/2401.01234v1"
          rel="related" type="application/pdf"/>
  </entry>
</feed>
"""


def test_parse_atom_feed_extracts_core_fields() -> None:
    entries = parse_atom_feed(_SAMPLE)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.source == "arxiv"
    assert entry.source_id == "2401.01234v1"
    assert entry.title.startswith("An agent-based")
    assert entry.year == 2024
    assert entry.venue == "cs.SI"
    assert entry.doi == "10.0000/example.0001"
    assert entry.url == "http://arxiv.org/pdf/2401.01234v1"
    assert entry.authors == ["Ada Lovelace", "Charles Babbage"]
    assert entry.cite_key.startswith("lovelace2024_")
    assert entry.entry_type == "article"


def test_build_search_url_includes_date_filter_when_provided() -> None:
    url = _build_search_url(query="news", limit=5, year_from=2020, year_to=2022)
    assert "search_query=all%3Anews+AND+submittedDate%3A%5B20200101+TO+20221231%5D" in url


def test_search_arxiv_with_injected_client() -> None:
    captured: list[str] = []

    def fake_client(url: str, headers: dict[str, str]) -> HttpResponse:
        captured.append(url)
        return HttpResponse(
            url=url,
            status=200,
            body=_SAMPLE,
            content_type="application/atom+xml",
        )

    entries = search_arxiv(query="news", limit=1, client=fake_client)
    assert len(captured) == 1
    assert "export.arxiv.org" in captured[0]
    assert entries[0].title.startswith("An agent-based")
