"""arXiv search + DOI fetch via the public Atom API.

arXiv exposes `http://export.arxiv.org/api/query` with Atom XML output.
The toolkit only consumes the small subset of the Atom schema it needs:
title, authors, summary (abstract), published date, primary category,
arxiv id, and the optional `<arxiv:doi>` element.
"""

from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET

from paper_toolkit.lit.citekey import make_cite_key
from paper_toolkit.lit.http_client import HttpClient, HttpError, polite_get
from paper_toolkit.lit.models import LiteratureEntry

_BASE_URL = "http://export.arxiv.org/api/query"
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"
_NS = {"atom": _ATOM_NS, "arxiv": _ARXIV_NS}


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _extract_year(published: str) -> int | None:
    if not published:
        return None
    # `published` looks like `2024-05-12T17:34:21Z`.
    try:
        return int(published[:4])
    except ValueError:
        return None


def _arxiv_id_from_entry_id(entry_id: str) -> str:
    """`http://arxiv.org/abs/2401.01234v3` -> `2401.01234v3`."""
    return entry_id.rsplit("/", 1)[-1]


def _parse_entry(node: ET.Element) -> LiteratureEntry:
    title = _text(node.find("atom:title", _NS))
    abstract = _text(node.find("atom:summary", _NS))
    published = _text(node.find("atom:published", _NS))
    entry_id = _text(node.find("atom:id", _NS))
    arxiv_id = _arxiv_id_from_entry_id(entry_id)
    authors = [_text(name) for name in node.findall("atom:author/atom:name", _NS) if _text(name)]
    doi_node = node.find("arxiv:doi", _NS)
    doi = _text(doi_node) if doi_node is not None else None
    primary_category = node.find("arxiv:primary_category", _NS)
    venue = primary_category.attrib.get("term") if primary_category is not None else None
    year = _extract_year(published)
    pdf_url = None
    for link in node.findall("atom:link", _NS):
        if link.attrib.get("title") == "pdf":
            pdf_url = link.attrib.get("href")
            break
    cite_key = make_cite_key(authors=authors, year=year, title=title)
    return LiteratureEntry(
        source="arxiv",
        source_id=arxiv_id,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi or None,
        url=pdf_url or entry_id or None,
        abstract=abstract or None,
        entry_type="article",
        cite_key=cite_key,
    )


def _build_search_url(
    *,
    query: str,
    limit: int,
    year_from: int | None,
    year_to: int | None,
) -> str:
    parts: list[str] = [f"all:{query}"]
    if year_from is not None or year_to is not None:
        lo = f"{year_from:04d}" if year_from is not None else "*"
        hi = f"{year_to:04d}" if year_to is not None else "*"
        parts.append(f"submittedDate:[{lo}0101 TO {hi}1231]")
    search_query = " AND ".join(parts)
    params = {
        "search_query": search_query,
        "start": "0",
        "max_results": str(max(1, min(limit, 100))),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    return f"{_BASE_URL}?{urllib.parse.urlencode(params)}"


def parse_atom_feed(body: bytes) -> list[LiteratureEntry]:
    root = ET.fromstring(body)
    return [_parse_entry(entry) for entry in root.findall("atom:entry", _NS)]


def search_arxiv(
    *,
    query: str,
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    client: HttpClient | None = None,
) -> list[LiteratureEntry]:
    url = _build_search_url(query=query, limit=limit, year_from=year_from, year_to=year_to)
    response = polite_get(url, accept="application/atom+xml", client=client)
    if response.status != 200:
        raise HttpError(f"arXiv returned HTTP {response.status} for {url}")
    return parse_atom_feed(response.body)


def fetch_arxiv_id(*, arxiv_id: str, client: HttpClient | None = None) -> LiteratureEntry:
    url = f"{_BASE_URL}?{urllib.parse.urlencode({'id_list': arxiv_id})}"
    response = polite_get(url, accept="application/atom+xml", client=client)
    if response.status != 200:
        raise HttpError(f"arXiv returned HTTP {response.status} for {url}")
    entries = parse_atom_feed(response.body)
    if not entries:
        raise HttpError(f"arXiv returned no entries for id {arxiv_id}")
    return entries[0]
