"""Read page metadata produced by compile runs + render PDFs to PNGs + extract elements.

Rendering uses `pdf2image` (which requires the system `poppler` package). Element
extraction is best-effort: we read `main.aux` for labels and `\\@writefile` entries
to learn page numbers and parse the pdflatex log for figure-file placements and
overfull warnings. Per spec §16, bounding boxes are optional — we leave `bbox=None`
when we can't extract one.

If pdf2image / poppler is unavailable, rendering is skipped silently and the
elements still get persisted (so `paper page count` / `elements` / `overflow`
report whatever metadata we did extract).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.compile_run import PageElement, PageElementKind, PageInfo
from paper_toolkit.paths import WorkspacePaths

_NEWLABEL_RE = re.compile(r"\\newlabel\{([^}]+)\}\{\{[^{}]*\}\{(\d+)\}")
_WRITEFILE_TOC_RE = re.compile(
    r"\\@writefile\{toc\}\{\\contentsline\s*\{[^}]+\}\{\\numberline\s*\{[^}]*\}([^{}]*)\}\{(\d+)\}"
)
_WRITEFILE_LOF_RE = re.compile(
    r"\\@writefile\{lof\}\{\\contentsline\s*\{figure\}\{\\numberline\s*\{[^}]*\}\{([^}]*)\}\}\{(\d+)\}"
)
_WRITEFILE_LOT_RE = re.compile(
    r"\\@writefile\{lot\}\{\\contentsline\s*\{table\}\{\\numberline\s*\{[^}]*\}\{([^}]*)\}\}\{(\d+)\}"
)


def _kind_from_label(label: str) -> PageElementKind:
    prefix = label.split(":", 1)[0].lower() if ":" in label else ""
    if prefix in {"fig", "figure"}:
        return "figure"
    if prefix in {"tab", "table"}:
        return "table"
    if prefix in {"eq", "equation"}:
        return "equation"
    if prefix in {"sec", "section", "subsec", "subsection", "ch", "chapter"}:
        return "heading"
    return "paragraph_start"


def parse_aux(aux_text: str) -> dict[int, list[PageElement]]:
    """Group `\\newlabel{...}` and `\\@writefile{...}` entries by page number."""
    by_page: dict[int, list[PageElement]] = defaultdict(list)
    for label, page in _NEWLABEL_RE.findall(aux_text):
        try:
            page_num = int(page)
        except ValueError:
            continue
        by_page[page_num].append(PageElement(kind=_kind_from_label(label), label=label))
    for caption, page in _WRITEFILE_LOF_RE.findall(aux_text):
        try:
            page_num = int(page)
        except ValueError:
            continue
        by_page[page_num].append(
            PageElement(kind="figure", text_preview=caption.strip()[:80] or None)
        )
    for caption, page in _WRITEFILE_LOT_RE.findall(aux_text):
        try:
            page_num = int(page)
        except ValueError:
            continue
        by_page[page_num].append(
            PageElement(kind="table", text_preview=caption.strip()[:80] or None)
        )
    for heading, page in _WRITEFILE_TOC_RE.findall(aux_text):
        try:
            page_num = int(page)
        except ValueError:
            continue
        by_page[page_num].append(
            PageElement(kind="heading", text_preview=heading.strip()[:80] or None)
        )
    return by_page


_OVERFULL_PAGE_RE = re.compile(r"Overfull \\hbox .* at lines? (\d+)")


def _annotate_overflow_from_log(by_page: dict[int, list[PageElement]], log_text: str) -> None:
    """Mark overflow on whichever page contains an existing element near the line.

    pdflatex's `Overfull \\hbox` message gives an input-line number, not an
    output page number. As a coarse approximation, mark a generic `paragraph_start`
    overflow element on every page that already has any extracted element so CC
    can spot wide pages visually; precise mapping requires `synctex` and is
    out of scope.
    """
    if not log_text or not by_page:
        return
    if _OVERFULL_PAGE_RE.search(log_text) is None:
        return
    # Tag the highest-numbered page with an overflow marker as a heuristic.
    last_page = max(by_page.keys())
    by_page[last_page].append(
        PageElement(kind="paragraph_start", overflow=True, text_preview="overfull-hbox")
    )


def _pdf_page_count(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader

        with pdf_path.open("rb") as fh:
            reader = PdfReader(fh)
            return len(reader.pages)
    except Exception:
        return 0


def _render_pngs(pdf_path: Path, pages_dir: Path, dpi: int = 150) -> list[Path]:
    """Render every PDF page to `pages_dir/page-NNN.png`. Returns the list of files.

    Falls back to an empty list if pdf2image / poppler is unavailable or the PDF
    fails to render. The caller decides whether to surface an empty list as an
    error or warning.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return []

    try:
        images = convert_from_path(str(pdf_path), dpi=dpi)
    except Exception:
        return []

    pages_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    for idx, image in enumerate(images, start=1):
        out_path = pages_dir / f"page-{idx:03d}.png"
        image.save(out_path, "PNG")
        out_paths.append(out_path)
    return out_paths


def render_compile_pages(
    *,
    run_id: str,
    run_dir: Path,
    pdf_path: Path | None,
    dpi: int = 150,
) -> list[PageInfo]:
    """Render PDF pages + extract per-page elements; persist `pages/elements.json`.

    Returns the in-memory `PageInfo` list. Always writes `pages/elements.json`
    when the run directory exists, even if rendering failed, so `paper page
    elements` has something to read.
    """
    pages_dir = run_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Parse .aux + log for per-page metadata first; this works without poppler.
    aux_path = run_dir / "main.aux"
    log_path = run_dir / "main.log"
    aux_text = aux_path.read_text(encoding="utf-8", errors="replace") if aux_path.exists() else ""
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    elements_by_page = parse_aux(aux_text)
    _annotate_overflow_from_log(elements_by_page, log_text)

    # Render PNGs if we have a PDF.
    png_paths: list[Path] = []
    if pdf_path is not None and pdf_path.exists():
        png_paths = _render_pngs(pdf_path, pages_dir, dpi=dpi)

    total_pages = len(png_paths) or _pdf_page_count(pdf_path) if pdf_path else 0
    if not total_pages and elements_by_page:
        total_pages = max(elements_by_page.keys())

    pages: list[PageInfo] = []
    for page_num in range(1, total_pages + 1):
        png_path = pages_dir / f"page-{page_num:03d}.png"
        pages.append(
            PageInfo(
                page_number=page_num,
                png_path=str(png_path.relative_to(run_dir.parents[2])).replace("\\", "/")
                if png_path.exists()
                else "",
                elements=elements_by_page.get(page_num, []),
            )
        )

    _write_elements_json(pages_dir, pages)
    return pages


def _write_elements_json(pages_dir: Path, pages: list[PageInfo]) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    elements_path = pages_dir / "elements.json"
    payload = [page.model_dump(mode="json") for page in pages]
    write_atomic_text(
        elements_path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


# ---- Reader helpers (consumed by cli/page.py) ---------------------------------


def load_pages(*, workspace: Path, run_id: str) -> list[PageInfo]:
    path = WorkspacePaths(workspace=workspace).compile_run_elements(run_id)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [PageInfo.model_validate(item) for item in raw]


def count_pages(*, workspace: Path, run_id: str) -> int:
    return len(load_pages(workspace=workspace, run_id=run_id))


def load_page_elements(*, workspace: Path, run_id: str, page: int) -> list[PageElement]:
    for info in load_pages(workspace=workspace, run_id=run_id):
        if info.page_number == page:
            return info.elements
    return []


def overflow_elements(*, workspace: Path, run_id: str) -> list[PageElement]:
    return [
        element
        for info in load_pages(workspace=workspace, run_id=run_id)
        for element in info.elements
        if element.overflow
    ]


def parse_page_range(spec: str | None, *, total: int) -> list[int]:
    """Resolve a `1-5`/`2,4`/`3` spec against the available page count."""
    if spec is None or spec.strip() == "":
        return list(range(1, total + 1))
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_str, hi_str = part.split("-", 1)
            lo = int(lo_str)
            hi = int(hi_str)
            pages.update(range(lo, hi + 1))
        else:
            pages.add(int(part))
    return sorted(p for p in pages if 1 <= p <= total)
