"""`paper lit ...` command logic."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from paper_toolkit.envelope import Envelope, ErrorEntry, StateSummary, build_envelope
from paper_toolkit.lit import arxiv, crossref, openalex
from paper_toolkit.lit.bibtex_emit import entries_to_bibtex
from paper_toolkit.lit.http_client import HttpError
from paper_toolkit.lit.index import (
    parse_jsonl,
    read_index,
    slugify_query,
    write_index,
)
from paper_toolkit.lit.merge import merge_into_bib
from paper_toolkit.lit.models import LiteratureEntry
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
    refresh_artifact_ref,
    write_state,
)

Source = Literal["arxiv", "crossref", "openalex"]


def _zero_summary() -> StateSummary:
    from paper_toolkit.cli.main import _zero_summary as zero

    return zero()


def _missing_workspace_envelope(*, workspace: Path, action: str) -> Envelope:
    paths = WorkspacePaths(workspace=workspace)
    return build_envelope(
        action=action,
        result={"workspace": str(paths.workspace)},
        state_summary=_zero_summary(),
        errors=[
            ErrorEntry(
                code="WS_NOT_INITIALIZED",
                message=f"no paper.json found at {paths.paper_state}",
            )
        ],
    )


def _state_summary(workspace: Path) -> StateSummary:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _zero_summary()
    return compute_state_summary(workspace=workspace, state=state)


def _dispatch_search(
    *, source: Source, query: str, limit: int, year_from: int | None, year_to: int | None
) -> list[LiteratureEntry]:
    if source == "arxiv":
        return arxiv.search_arxiv(query=query, limit=limit, year_from=year_from, year_to=year_to)
    if source == "crossref":
        return crossref.search_crossref(
            query=query, limit=limit, year_from=year_from, year_to=year_to
        )
    if source == "openalex":
        return openalex.search_openalex(
            query=query, limit=limit, year_from=year_from, year_to=year_to
        )
    raise ValueError(f"unsupported source {source!r}")


def search_cmd(
    *,
    workspace: Path,
    source: str,
    query: str,
    limit: int,
    year_from: int | None,
    year_to: int | None,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="lit.search")

    if source not in {"arxiv", "crossref", "openalex"}:
        return build_envelope(
            action="lit.search",
            result={"source": source, "query": query},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="LIT_UNKNOWN_SOURCE",
                    message=f"unknown source {source!r}; pick arxiv | crossref | openalex.",
                )
            ],
        )

    try:
        entries = _dispatch_search(
            source=source,  # type: ignore[arg-type]
            query=query,
            limit=limit,
            year_from=year_from,
            year_to=year_to,
        )
    except HttpError as exc:
        return build_envelope(
            action="lit.search",
            result={"source": source, "query": query},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="LIT_HTTP_ERROR", message=str(exc))],
        )

    slug = f"{source}_{slugify_query(query)}"
    out_path = write_index(workspace=workspace, slug=slug, entries=entries)
    return build_envelope(
        action="lit.search",
        result={
            "source": source,
            "query": query,
            "count": len(entries),
            "out_path": str(out_path),
            "cite_keys": [entry.cite_key for entry in entries],
        },
        state_summary=_state_summary(workspace),
    )


def fetch_doi_cmd(*, workspace: Path, doi: str, source: str) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="lit.fetch-doi")

    if source not in {"crossref", "openalex"}:
        return build_envelope(
            action="lit.fetch-doi",
            result={"source": source, "doi": doi},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="LIT_UNKNOWN_SOURCE",
                    message=f"DOI fetch supports crossref | openalex; got {source!r}.",
                )
            ],
        )

    try:
        if source == "crossref":
            entry = crossref.fetch_crossref_doi(doi=doi)
        else:
            entry = openalex.fetch_openalex_doi(doi=doi)
    except HttpError as exc:
        return build_envelope(
            action="lit.fetch-doi",
            result={"source": source, "doi": doi},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="LIT_HTTP_ERROR", message=str(exc))],
        )

    slug = f"{source}_doi_{slugify_query(doi)}"
    out_path = write_index(workspace=workspace, slug=slug, entries=[entry])
    return build_envelope(
        action="lit.fetch-doi",
        result={
            "source": source,
            "doi": doi,
            "out_path": str(out_path),
            "cite_key": entry.cite_key,
            "title": entry.title,
        },
        state_summary=_state_summary(workspace),
    )


def to_bibtex_cmd(*, workspace: Path, input_path: Path, out_path: Path | None) -> Envelope:
    if not input_path.is_file():
        return build_envelope(
            action="lit.to-bibtex",
            result={"input": str(input_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="LIT_INPUT_NOT_FOUND",
                    message=f"JSONL input not found: {input_path}",
                )
            ],
        )
    try:
        entries = read_index(input_path)
    except ValueError as exc:
        return build_envelope(
            action="lit.to-bibtex",
            result={"input": str(input_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="LIT_INPUT_INVALID", message=str(exc))],
        )
    body = entries_to_bibtex(entries)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf-8")
    return build_envelope(
        action="lit.to-bibtex",
        result={
            "input": str(input_path),
            "out_path": str(out_path) if out_path is not None else None,
            "entry_count": len(entries),
            "bibtex": body if out_path is None else None,
        },
        state_summary=_state_summary(workspace),
    )


def merge_bib_cmd(*, workspace: Path, inputs: list[Path]) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="lit.merge-bib")

    entries: list[LiteratureEntry] = []
    missing: list[str] = []
    invalid: list[str] = []
    for input_path in inputs:
        if not input_path.is_file():
            missing.append(str(input_path))
            continue
        try:
            entries.extend(parse_jsonl(input_path.read_text(encoding="utf-8")))
        except ValueError as exc:
            invalid.append(f"{input_path}: {exc}")

    errors = [
        ErrorEntry(code="LIT_INPUT_NOT_FOUND", message=f"input not found: {path}")
        for path in missing
    ] + [ErrorEntry(code="LIT_INPUT_INVALID", message=msg) for msg in invalid]
    if errors:
        return build_envelope(
            action="lit.merge-bib",
            result={"inputs": [str(p) for p in inputs]},
            state_summary=_state_summary(workspace),
            errors=errors,
        )

    report = merge_into_bib(workspace=workspace, entries=entries)
    refresh_artifact_ref(workspace=workspace, state=state, artifact="bib")
    write_state(workspace=workspace, state=state)
    return build_envelope(
        action="lit.merge-bib",
        result={
            "inputs": [str(p) for p in inputs],
            "bib_path": str(report.bib_path),
            "added": report.added,
            "skipped": report.skipped,
        },
        state_summary=_state_summary(workspace),
    )
