"""Top-level Typer app for `paper`. Subcommands are wired in here.

Every CLI subcommand goes through `safe_dispatch`, which catches any uncaught
exception (Pydantic ValidationError, subprocess.TimeoutExpired, FileNotFoundError,
etc.) and converts it into a structured `INTERNAL_ERROR` envelope on stdout —
the toolkit never emits raw tracebacks to stderr (spec §8).
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from paper_toolkit import __version__
from paper_toolkit.cli import analysis as analysis_cmd
from paper_toolkit.cli import check as check_cmd
from paper_toolkit.cli import compile as compile_cmd
from paper_toolkit.cli import compose as compose_cmd
from paper_toolkit.cli import evidence as evidence_cmd
from paper_toolkit.cli import figure as figure_cmd
from paper_toolkit.cli import init as init_cmd
from paper_toolkit.cli import lit as lit_cmd
from paper_toolkit.cli import page as page_cmd
from paper_toolkit.cli import refs as refs_cmd
from paper_toolkit.cli import scan as scan_cmd
from paper_toolkit.cli import status as status_cmd
from paper_toolkit.cli import table as table_cmd
from paper_toolkit.cli import template as template_cmd
from paper_toolkit.envelope import Envelope, ErrorEntry, StateSummary, build_envelope
from paper_toolkit.paths import WorkspacePaths

app = typer.Typer(
    name="paper",
    help="Deterministic CLI for academic paper workflows. No LLM calls.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
)


def _zero_summary() -> StateSummary:
    return StateSummary(
        section_count=0,
        claim_count=0,
        evidence_count=0,
        citation_count=0,
        figure_count=0,
        packed_figure_count=0,
        graph_valid=True,
        graph_issue_count=0,
        last_compile=None,
        last_updated_artifact=None,
        paper_json_checksum="0" * 64,
    )


def _internal_error_envelope(action: str, exc: BaseException) -> Envelope:
    debug = os.environ.get("PAPER_TOOLKIT_DEBUG") == "1"
    message = f"{type(exc).__name__}: {exc}"
    if debug:
        message = message + "\n" + traceback.format_exc()
    return build_envelope(
        action=action,
        result={},
        state_summary=_zero_summary(),
        errors=[
            ErrorEntry(
                code="INTERNAL_ERROR",
                message=message,
                fixup_hint="Set PAPER_TOOLKIT_DEBUG=1 for a traceback, then report the bug.",
            )
        ],
    )


def _render_human(env: Envelope) -> str:
    head = f"[{'OK' if env.ok else 'FAIL'}] {env.action}"
    parts: list[str] = [head]
    if env.errors:
        for e in env.errors:
            parts.append(f"  ERROR {e.code}: {e.message}")
    if env.warnings:
        for w in env.warnings:
            parts.append(f"  WARN: {w}")
    summary = env.state_summary
    parts.append(
        "  state: "
        f"sections={summary.section_count} claims={summary.claim_count} "
        f"evidence={summary.evidence_count} figures={summary.figure_count} "
        f"graph_valid={summary.graph_valid}"
    )
    return "\n".join(parts)


def emit_envelope(
    envelope: Envelope,
    *,
    workspace: Path | None,
    human: bool,
    verbose_state: bool,
) -> None:
    """Print the envelope and exit with code 0 (ok) or 1 (not ok).

    `--verbose-state` (per spec §8) replaces the compact `state_summary` with
    the full `paper.json` content, when the workspace has been initialized.
    """
    if human:
        print(_render_human(envelope))
    else:
        data = envelope.model_dump(mode="json")
        if verbose_state and workspace is not None:
            paths = WorkspacePaths(workspace=workspace)
            if paths.paper_state.exists():
                try:
                    data["state_summary"] = json.loads(
                        paths.paper_state.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    pass
        print(json.dumps(data, indent=2, sort_keys=True))
    if not envelope.ok:
        raise typer.Exit(code=1)


def safe_dispatch(
    *,
    action: str,
    fn: Callable[[], Envelope],
    workspace: Path | None,
    human: bool,
    verbose_state: bool,
) -> None:
    """Run `fn()`, convert any unhandled exception into an INTERNAL_ERROR envelope, emit."""
    try:
        envelope = fn()
    except typer.Exit:
        raise
    except Exception as exc:
        envelope = _internal_error_envelope(action, exc)
    emit_envelope(envelope, workspace=workspace, human=human, verbose_state=verbose_state)


WorkspaceOption = Annotated[
    Path | None,
    typer.Option(
        "--workspace",
        "-w",
        help="Workspace root (defaults to cwd).",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
]
HumanOption = Annotated[
    bool, typer.Option("--human", help="Print a short human-readable summary instead of JSON.")
]
VerboseStateOption = Annotated[
    bool,
    typer.Option(
        "--verbose-state",
        help="Replace state_summary with full paper.json content (spec §8).",
    ),
]


def _ws(workspace: Path | None) -> Path:
    return workspace if workspace is not None else Path.cwd()


@app.command("version")
def version() -> None:
    """Print package version."""
    print(__version__)


@app.command("init")
def init(
    title: Annotated[str, typer.Option("--title", help="Paper title.")],
    venue: Annotated[str, typer.Option("--venue", help="Venue id, e.g. 'nature'.")] = "nature",
    language: Annotated[
        str, typer.Option("--language", help="Language code: en | zh | bilingual.")
    ] = "en",
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    """Initialize a paper workspace: create paper/ subtree and write paper.json."""
    ws = _ws(workspace)
    safe_dispatch(
        action="init",
        fn=lambda: init_cmd.run(workspace=ws, title=title, venue=venue, language=language),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@app.command("status")
def status(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    """Report current workspace state."""
    ws = _ws(workspace)
    safe_dispatch(
        action="status",
        fn=lambda: status_cmd.run(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@app.command("scan")
def scan(
    scanner: Annotated[str, typer.Option("--scanner", help="Scanner id.")] = "agentsociety",
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    """Scan a workspace and write paper/research_pack.json."""
    ws = _ws(workspace)
    safe_dispatch(
        action="scan",
        fn=lambda: scan_cmd.run(workspace=ws, scanner=scanner),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


evidence_app = typer.Typer(help="Manage paper/evidence_graph.json.")
app.add_typer(evidence_app, name="evidence")

compose_app = typer.Typer(help="Compose figures, bibliography, and main.tex.")
app.add_typer(compose_app, name="compose")

template_app = typer.Typer(help="List and expand paper section templates.")
app.add_typer(template_app, name="template")

check_app = typer.Typer(help="Run deterministic manuscript checkers.")
app.add_typer(check_app, name="check")

page_app = typer.Typer(help="Inspect compile-run page metadata.")
app.add_typer(page_app, name="page")

figure_app = typer.Typer(help="Render figures from JSON specs.")
app.add_typer(figure_app, name="figure")

table_app = typer.Typer(help="Render LaTeX tables from JSON specs.")
app.add_typer(table_app, name="table")

lit_app = typer.Typer(help="Search arXiv / CrossRef / OpenAlex and merge into refs.bib.")
app.add_typer(lit_app, name="lit")

refs_app = typer.Typer(help="Inspect and clean up paper/refs.bib.")
app.add_typer(refs_app, name="refs")

analysis_app = typer.Typer(
    help="Drive the analysis pipeline that feeds the agentsociety-generate-paper skill."
)
app.add_typer(analysis_app, name="analysis")


@template_app.command("list")
def template_list(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="template.list",
        fn=lambda: template_cmd.list_cmd(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@template_app.command("expand")
def template_expand(
    section: Annotated[str, typer.Option("--section", help="Section template name.")],
    target: Annotated[Path | None, typer.Option("--target", help="Optional output path.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="template.expand",
        fn=lambda: template_cmd.expand_cmd(workspace=ws, section=section, target=target),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@compose_app.command("pack-figures")
def compose_pack_figures(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="compose.pack-figures",
        fn=lambda: compose_cmd.pack_figures_cmd(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@compose_app.command("write-bib")
def compose_write_bib(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="compose.write-bib",
        fn=lambda: compose_cmd.write_bib_cmd(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@compose_app.command("assemble-latex")
def compose_assemble_latex(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="compose.assemble-latex",
        fn=lambda: compose_cmd.assemble_latex_cmd(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("add-claim")
def evidence_add_claim(
    node_id: Annotated[str, typer.Option("--id", help="Claim node id.")],
    label: Annotated[str, typer.Option("--label", help="Human-readable claim label.")],
    body: Annotated[str | None, typer.Option("--body", help="Full claim text.")] = None,
    section: Annotated[str | None, typer.Option("--section", help="Section name.")] = None,
    strength: Annotated[
        str | None, typer.Option("--strength", help="primary | supporting | minor.")
    ] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.add-claim",
        fn=lambda: evidence_cmd.add_claim(
            workspace=ws,
            node_id=node_id,
            label=label,
            body=body,
            section=section,
            strength=strength,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("add-evidence")
def evidence_add_evidence(
    node_id: Annotated[str, typer.Option("--id", help="Evidence node id.")],
    label: Annotated[str, typer.Option("--label", help="Human-readable evidence label.")],
    source_kind: Annotated[
        str, typer.Option("--source-kind", help="figure | table | stat | qual | external.")
    ],
    source_ref: Annotated[str, typer.Option("--source-ref", help="Source reference id or path.")],
    source_detail: Annotated[
        str | None, typer.Option("--source-detail", help="Optional source detail.")
    ] = None,
    body: Annotated[str | None, typer.Option("--body", help="Full evidence text.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.add-evidence",
        fn=lambda: evidence_cmd.add_evidence(
            workspace=ws,
            node_id=node_id,
            label=label,
            source_kind=source_kind,
            source_ref=source_ref,
            source_detail=source_detail,
            body=body,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("add-citation")
def evidence_add_citation(
    node_id: Annotated[str, typer.Option("--id", help="Citation node id.")],
    cite_key: Annotated[str, typer.Option("--cite-key", help="BibTeX cite key.")],
    label: Annotated[str, typer.Option("--label", help="Human-readable citation label.")],
    body: Annotated[str | None, typer.Option("--body", help="Optional citation note.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.add-citation",
        fn=lambda: evidence_cmd.add_citation(
            workspace=ws, node_id=node_id, cite_key=cite_key, label=label, body=body
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("link")
def evidence_link(
    src: Annotated[str, typer.Option("--src", help="Source node id.")],
    dst: Annotated[str, typer.Option("--dst", help="Destination node id.")],
    kind: Annotated[
        str, typer.Option("--kind", help="supports | derives_from | cites | contradicts.")
    ],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.link",
        fn=lambda: evidence_cmd.link(workspace=ws, src=src, dst=dst, kind=kind),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("rm-node")
def evidence_rm_node(
    node_id: Annotated[str, typer.Option("--id", help="Node id to remove.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.rm-node",
        fn=lambda: evidence_cmd.rm_node(workspace=ws, node_id=node_id),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("rm-edge")
def evidence_rm_edge(
    src: Annotated[str, typer.Option("--src", help="Source node id.")],
    dst: Annotated[str, typer.Option("--dst", help="Destination node id.")],
    kind: Annotated[str | None, typer.Option("--kind", help="Optional edge kind filter.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.rm-edge",
        fn=lambda: evidence_cmd.rm_edge(workspace=ws, src=src, dst=dst, kind=kind),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("validate")
def evidence_validate(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.validate",
        fn=lambda: evidence_cmd.validate(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("topo-order")
def evidence_topo_order(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.topo-order",
        fn=lambda: evidence_cmd.topo_order(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@evidence_app.command("render-mermaid")
def evidence_render_mermaid(
    out: Annotated[Path | None, typer.Option("--out", help="Optional output .mmd path.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="evidence.render-mermaid",
        fn=lambda: evidence_cmd.render_mermaid(workspace=ws, out=out),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@app.command("compile-once")
def compile_once_cmd(
    engine: Annotated[str, typer.Option("--engine", help="LaTeX engine.")] = "pdflatex",
    max_attempts: Annotated[
        int | None, typer.Option("--max-attempts", help="Advisory max attempt count.")
    ] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="compile-once",
        fn=lambda: compile_cmd.run(workspace=ws, engine=engine, max_attempts=max_attempts),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@page_app.command("render")
def page_render(
    run_id: Annotated[str, typer.Option("--run", help="Compile run id, e.g. r1.")],
    pages: Annotated[
        str | None,
        typer.Option(
            "--pages",
            help="Page range or list, e.g. '1-5', '2,4', or '3'. Omit for all pages.",
        ),
    ] = None,
    dpi: Annotated[int, typer.Option("--dpi", help="Render DPI.")] = 150,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="page.render",
        fn=lambda: page_cmd.render_cmd(workspace=ws, run_id=run_id, pages=pages, dpi=dpi),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@page_app.command("count")
def page_count(
    run_id: Annotated[str, typer.Option("--run", help="Compile run id, e.g. r1.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="page.count",
        fn=lambda: page_cmd.count_cmd(workspace=ws, run_id=run_id),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@page_app.command("elements")
def page_elements(
    run_id: Annotated[str, typer.Option("--run", help="Compile run id, e.g. r1.")],
    page: Annotated[int, typer.Option("--page", help="1-based page number.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="page.elements",
        fn=lambda: page_cmd.elements_cmd(workspace=ws, run_id=run_id, page=page),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@page_app.command("overflow")
def page_overflow(
    run_id: Annotated[str, typer.Option("--run", help="Compile run id, e.g. r1.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="page.overflow",
        fn=lambda: page_cmd.overflow_cmd(workspace=ws, run_id=run_id),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@figure_app.command("render")
def figure_render(
    spec: Annotated[Path, typer.Option("--spec", help="Path to a figure spec JSON.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="figure.render",
        fn=lambda: figure_cmd.render_cmd(workspace=ws, spec_path=spec),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@figure_app.command("render-all")
def figure_render_all(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="figure.render-all",
        fn=lambda: figure_cmd.render_all_cmd(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@figure_app.command("list-palettes")
def figure_list_palettes(
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    safe_dispatch(
        action="figure.list-palettes",
        fn=figure_cmd.list_palettes_cmd,
        workspace=None,
        human=human,
        verbose_state=verbose_state,
    )


@figure_app.command("register")
def figure_register(
    spec: Annotated[Path, typer.Option("--spec", help="Path to a figure spec JSON.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="figure.register",
        fn=lambda: figure_cmd.register_cmd(workspace=ws, spec_path=spec),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@table_app.command("render")
def table_render(
    spec: Annotated[Path, typer.Option("--spec", help="Path to a table spec JSON.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="table.render",
        fn=lambda: table_cmd.render_cmd(workspace=ws, spec_path=spec),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@table_app.command("render-all")
def table_render_all(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="table.render-all",
        fn=lambda: table_cmd.render_all_cmd(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@lit_app.command("search")
def lit_search(
    source: Annotated[str, typer.Option("--source", help="arxiv | crossref | openalex.")],
    query: Annotated[str, typer.Option("--query", help="Free-form search query.")],
    limit: Annotated[int, typer.Option("--limit", help="Max results to fetch.")] = 10,
    year_from: Annotated[
        int | None, typer.Option("--year-from", help="Earliest year (inclusive).")
    ] = None,
    year_to: Annotated[
        int | None, typer.Option("--year-to", help="Latest year (inclusive).")
    ] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="lit.search",
        fn=lambda: lit_cmd.search_cmd(
            workspace=ws,
            source=source,
            query=query,
            limit=limit,
            year_from=year_from,
            year_to=year_to,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@lit_app.command("fetch-doi")
def lit_fetch_doi(
    doi: Annotated[str, typer.Option("--doi", help="DOI to look up.")],
    source: Annotated[str, typer.Option("--source", help="crossref | openalex.")] = "crossref",
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="lit.fetch-doi",
        fn=lambda: lit_cmd.fetch_doi_cmd(workspace=ws, doi=doi, source=source),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@lit_app.command("to-bibtex")
def lit_to_bibtex(
    input_path: Annotated[Path, typer.Option("--input", help="Path to a lit JSONL index.")],
    out: Annotated[Path | None, typer.Option("--out", help="Optional output .bib path.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="lit.to-bibtex",
        fn=lambda: lit_cmd.to_bibtex_cmd(workspace=ws, input_path=input_path, out_path=out),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@lit_app.command("merge-bib")
def lit_merge_bib(
    inputs: Annotated[
        list[Path],
        typer.Option("--input", help="One or more JSONL files to merge (use multiple --input)."),
    ],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="lit.merge-bib",
        fn=lambda: lit_cmd.merge_bib_cmd(workspace=ws, inputs=list(inputs)),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("style")
def check_style_cmd(
    section: Annotated[str | None, typer.Option("--section", help="Optional section name.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.style",
        fn=lambda: check_cmd.run_style(workspace=ws, section=section),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("citations")
def check_citations_cmd(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.citations",
        fn=lambda: check_cmd.run_citations(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("figures")
def check_figures_cmd(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.figures",
        fn=lambda: check_cmd.run_figures(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("figure-qa")
def check_figure_qa_cmd(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.figure-qa",
        fn=lambda: check_cmd.run_figure_qa(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("claim-coverage")
def check_claim_coverage_cmd(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.claim-coverage",
        fn=lambda: check_cmd.run_claim_coverage(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("word-count")
def check_word_count_cmd(
    section: Annotated[str | None, typer.Option("--section", help="Optional section name.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.word-count",
        fn=lambda: check_cmd.run_word_count(workspace=ws, section=section),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("logic-consistency")
def check_logic_consistency_cmd(
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.logic-consistency",
        fn=lambda: check_cmd.run_logic_consistency(workspace=ws),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@check_app.command("all")
def check_all_cmd(
    section: Annotated[str | None, typer.Option("--section", help="Optional section name.")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="check.all",
        fn=lambda: check_cmd.run_all(workspace=ws, section=section),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@refs_app.command("dedup")
def refs_dedup(
    apply: Annotated[
        bool,
        typer.Option(
            "--apply",
            help="Rewrite refs.bib with absorbed duplicates removed (default reports only).",
        ),
    ] = False,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="refs.dedup",
        fn=lambda: refs_cmd.dedup_cmd(workspace=ws, apply=apply),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


# --- paper analysis -----------------------------------------------------


@analysis_app.command("init")
def analysis_init(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id", help="Hypothesis identifier.")],
    experiment_id: Annotated[str, typer.Option("--experiment-id", help="Experiment identifier.")],
    db: Annotated[Path, typer.Option("--db", help="Path to the experiment's sqlite.db.")],
    language: Annotated[
        str | None,
        typer.Option("--language", help="Override report language (en | zh | bilingual)."),
    ] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.init",
        fn=lambda: analysis_cmd.init_cmd(
            workspace=ws,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
            db_path=db,
            language=language,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("write-plan")
def analysis_write_plan(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
    experiment_id: Annotated[str, typer.Option("--experiment-id")],
    payload: Annotated[Path, typer.Option("--payload", help="Path to JSON or YAML plan payload.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.write-plan",
        fn=lambda: analysis_cmd.write_plan_cmd(
            workspace=ws,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
            payload_path=payload,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("list-tables")
def analysis_list_tables(
    db: Annotated[Path, typer.Option("--db", help="Path to a sqlite database.")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.list-tables",
        fn=lambda: analysis_cmd.list_tables_cmd(workspace=ws, db_path=db),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("profile-table")
def analysis_profile_table(
    db: Annotated[Path, typer.Option("--db", help="Path to a sqlite database.")],
    table: Annotated[str, typer.Option("--table", help="Table name to profile.")],
    sample_rows: Annotated[int, typer.Option("--sample-rows")] = 5_000,
    hypothesis_id: Annotated[str | None, typer.Option("--hypothesis-id")] = None,
    experiment_id: Annotated[str | None, typer.Option("--experiment-id")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.profile-table",
        fn=lambda: analysis_cmd.profile_table_cmd(
            workspace=ws,
            db_path=db,
            table=table,
            sample_rows=sample_rows,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("query")
def analysis_query(
    db: Annotated[Path, typer.Option("--db", help="Path to a sqlite database.")],
    sql: Annotated[str, typer.Option("--sql", help="SQL statement to execute.")],
    limit: Annotated[int, typer.Option("--limit")] = 1_000,
    allow_select_all: Annotated[
        bool, typer.Option("--allow-select-all", help="Permit SELECT *.")
    ] = False,
    out: Annotated[Path | None, typer.Option("--out", help="Optional JSON output path.")] = None,
    hypothesis_id: Annotated[str | None, typer.Option("--hypothesis-id")] = None,
    experiment_id: Annotated[str | None, typer.Option("--experiment-id")] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.query",
        fn=lambda: analysis_cmd.query_cmd(
            workspace=ws,
            db_path=db,
            sql=sql,
            limit=limit,
            allow_select_all=allow_select_all,
            out_path=out,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("record-claim")
def analysis_record_claim(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
    experiment_id: Annotated[str, typer.Option("--experiment-id")],
    claim_id: Annotated[str, typer.Option("--claim-id")],
    text: Annotated[str, typer.Option("--text")],
    kind: Annotated[
        str,
        typer.Option("--kind", help="quantitative | qualitative | comparative"),
    ],
    evidence: Annotated[
        str, typer.Option("--evidence", help="Reference to supporting query/profile slug.")
    ],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.record-claim",
        fn=lambda: analysis_cmd.record_claim_cmd(
            workspace=ws,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
            claim_id=claim_id,
            text=text,
            kind=kind,
            evidence=evidence,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("record-figure-contract")
def analysis_record_figure_contract(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
    experiment_id: Annotated[str, typer.Option("--experiment-id")],
    claim_id: Annotated[str, typer.Option("--claim-id")],
    figure_id: Annotated[str, typer.Option("--figure-id")],
    rationale: Annotated[str, typer.Option("--rationale")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.record-figure-contract",
        fn=lambda: analysis_cmd.record_figure_contract_cmd(
            workspace=ws,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
            claim_id=claim_id,
            figure_id=figure_id,
            rationale=rationale,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


def _wire_check(name: str, fn):  # type: ignore[no-untyped-def]
    @analysis_app.command(name)
    def _cmd(
        hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
        experiment_id: Annotated[str, typer.Option("--experiment-id")],
        workspace: WorkspaceOption = None,
        human: HumanOption = False,
        verbose_state: VerboseStateOption = False,
    ) -> None:
        ws = _ws(workspace)
        safe_dispatch(
            action=f"analysis.{name}",
            fn=lambda: fn(workspace=ws, hypothesis_id=hypothesis_id, experiment_id=experiment_id),
            workspace=ws,
            human=human,
            verbose_state=verbose_state,
        )

    _cmd.__name__ = f"analysis_{name.replace('-', '_')}"


_wire_check("check-plan", analysis_cmd.check_plan_cmd)
_wire_check("check-explore", analysis_cmd.check_explore_cmd)
_wire_check("check-claims", analysis_cmd.check_claims_cmd)
_wire_check("check-refine", analysis_cmd.check_refine_cmd)
_wire_check("check-release", analysis_cmd.check_release_cmd)


@analysis_app.command("check-synthesis")
def analysis_check_synthesis(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.check-synthesis",
        fn=lambda: analysis_cmd.check_synthesis_cmd(workspace=ws, hypothesis_id=hypothesis_id),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("build-report-context")
def analysis_build_report_context(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
    experiment_id: Annotated[str, typer.Option("--experiment-id")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.build-report-context",
        fn=lambda: analysis_cmd.build_report_context_cmd(
            workspace=ws, hypothesis_id=hypothesis_id, experiment_id=experiment_id
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("build-synthesis-brief")
def analysis_build_synthesis_brief(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
    experiments: Annotated[
        list[str],
        typer.Option("--experiment-id", help="Repeat for each experiment."),
    ],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.build-synthesis-brief",
        fn=lambda: analysis_cmd.build_synthesis_brief_cmd(
            workspace=ws,
            hypothesis_id=hypothesis_id,
            experiments=list(experiments),
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("lift-to-evidence")
def analysis_lift_to_evidence(
    hypothesis_id: Annotated[str, typer.Option("--hypothesis-id")],
    experiment_id: Annotated[str, typer.Option("--experiment-id")],
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.lift-to-evidence",
        fn=lambda: analysis_cmd.lift_to_evidence_cmd(
            workspace=ws,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        ),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


@analysis_app.command("status")
def analysis_status(
    hypothesis_id: Annotated[
        str | None,
        typer.Option("--hypothesis-id", help="Optional filter; default lists every hypothesis."),
    ] = None,
    workspace: WorkspaceOption = None,
    human: HumanOption = False,
    verbose_state: VerboseStateOption = False,
) -> None:
    ws = _ws(workspace)
    safe_dispatch(
        action="analysis.status",
        fn=lambda: analysis_cmd.status_cmd(workspace=ws, hypothesis_id=hypothesis_id),
        workspace=ws,
        human=human,
        verbose_state=verbose_state,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
