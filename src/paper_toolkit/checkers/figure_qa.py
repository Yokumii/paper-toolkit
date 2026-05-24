"""Figure-QA checker — lints rendered figure PDFs against publication norms.

Inputs: every `.pdf` under `<workspace>/paper/figures/`. The checker is purely
deterministic and reads the PDF metadata via `pypdf`:

- **Column width**: PDF media-box width must be within ~5% of
  89 mm (single) or 183 mm (double).
- **Font family**: every embedded font name should contain Arial /
  Helvetica / DejaVu Sans / Liberation Sans (or "Sans" as a generic
  fallback). Anything else (Times, Computer Modern, custom CID fonts)
  is flagged.
- **Font embedding**: any font missing the embedded-program flag becomes
  an error — typesetters reject PDFs whose fonts are referenced but
  not bundled.

Subjective checks (panel-label placement, "rainbow colormap") stay out of
scope — those are LLM judgment, not deterministic mechanism.
"""

from __future__ import annotations

import re
from pathlib import Path

from paper_toolkit.checkers.base import issue
from paper_toolkit.models.check_report import CheckIssue, CheckReport
from paper_toolkit.paths import WorkspacePaths

_PT_PER_MM = 72.0 / 25.4
_SINGLE_COLUMN_MM = 89.0
_DOUBLE_COLUMN_MM = 183.0
_WIDTH_TOLERANCE_MM = 10.0  # generous: covers `\columnwidth` vs raw 89 mm

_APPROVED_FONT_TOKENS: tuple[str, ...] = (
    "arial",
    "helvetica",
    "dejavu sans",
    "dejavusans",
    "liberation sans",
    "liberationsans",
    "freesans",
)


def _strip_subset_prefix(font_name: str) -> str:
    """PDF subset fonts come prefixed with `ABCDEF+ActualFontName`."""
    if "+" in font_name and len(font_name.split("+", 1)[0]) == 6:
        return font_name.split("+", 1)[1]
    return font_name


def _font_is_approved(font_name: str) -> bool:
    name = _strip_subset_prefix(font_name).lower()
    return any(token in name for token in _APPROVED_FONT_TOKENS)


def _normalize_pdf_string(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    return text.lstrip("/")


def _font_is_embedded(font_obj: object) -> bool:
    """A font is embedded iff its descriptor includes FontFile / FontFile2 / FontFile3."""
    try:
        font_dict = font_obj.get_object() if hasattr(font_obj, "get_object") else font_obj
    except Exception:
        return False
    if not hasattr(font_dict, "get"):
        return False
    # Type 0 (CID) fonts use DescendantFonts; recurse one level.
    subtype = _normalize_pdf_string(font_dict.get("/Subtype"))
    if subtype == "Type0":
        descendants = font_dict.get("/DescendantFonts") or []
        try:
            iterable = list(descendants)
        except TypeError:
            iterable = []
        for child in iterable:
            try:
                resolved = child.get_object() if hasattr(child, "get_object") else child
            except Exception:
                continue
            if _font_is_embedded(resolved):
                return True
        return False
    descriptor = font_dict.get("/FontDescriptor")
    if descriptor is None:
        return False
    try:
        resolved = descriptor.get_object() if hasattr(descriptor, "get_object") else descriptor
    except Exception:
        return False
    if not hasattr(resolved, "get"):
        return False
    return any(resolved.get(key) is not None for key in ("/FontFile", "/FontFile2", "/FontFile3"))


def _collect_font_records(pdf_reader: object) -> list[tuple[str, bool]]:
    """Return (font_name, embedded) pairs for every font referenced in any page."""
    records: list[tuple[str, bool]] = []
    seen: set[int] = set()
    try:
        pages = pdf_reader.pages  # type: ignore[attr-defined]
    except Exception:
        return records
    for page in pages:
        try:
            resources = page.get("/Resources") or {}
        except Exception:
            continue
        fonts = resources.get("/Font") if hasattr(resources, "get") else None
        if fonts is None:
            continue
        try:
            font_entries = fonts.items() if hasattr(fonts, "items") else []
        except Exception:
            continue
        for _, font_ref in font_entries:
            try:
                font_obj = font_ref.get_object() if hasattr(font_ref, "get_object") else font_ref
            except Exception:
                continue
            ident = id(font_obj)
            if ident in seen:
                continue
            seen.add(ident)
            name = _normalize_pdf_string(font_obj.get("/BaseFont") or font_obj.get("/Name"))
            records.append((name or "(unknown)", _font_is_embedded(font_obj)))
    return records


def _pdf_width_mm(pdf_reader: object) -> float | None:
    try:
        page = pdf_reader.pages[0]  # type: ignore[attr-defined]
    except Exception:
        return None
    try:
        box = page.mediabox
        width_pt = float(box.width)
    except Exception:
        return None
    return width_pt / _PT_PER_MM


_FIGURE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def check_figure_qa(*, workspace: Path) -> CheckReport:
    """Run figure-QA over every PDF under `<workspace>/paper/figures/`."""
    paths = WorkspacePaths(workspace=workspace)
    issues: list[CheckIssue] = []
    inspected: list[dict[str, object]] = []
    if not paths.figures_dir.exists():
        return CheckReport(checker="figure-qa", issues=issues, result={"inspected": []})

    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover — pypdf is a hard dep.
        raise RuntimeError(f"pypdf is required for figure-qa: {exc}") from exc

    for pdf_path in sorted(paths.figures_dir.glob("*.pdf")):
        figure_id = pdf_path.stem
        if not _FIGURE_ID_RE.match(figure_id):
            continue
        try:
            reader = PdfReader(str(pdf_path))
        except Exception as exc:
            issues.append(
                issue(
                    severity="error",
                    code="FQA_UNREADABLE_PDF",
                    message=f"could not read PDF {pdf_path.name}: {exc}",
                    location=str(pdf_path),
                )
            )
            continue

        width_mm = _pdf_width_mm(reader)
        font_records = _collect_font_records(reader)

        location = f"paper/figures/{pdf_path.name}"
        if width_mm is None:
            issues.append(
                issue(
                    severity="warning",
                    code="FQA_NO_MEDIABOX",
                    message=f"{pdf_path.name}: could not determine page width.",
                    location=location,
                )
            )
        else:
            if (
                abs(width_mm - _SINGLE_COLUMN_MM) > _WIDTH_TOLERANCE_MM
                and abs(width_mm - _DOUBLE_COLUMN_MM) > _WIDTH_TOLERANCE_MM
            ):
                issues.append(
                    issue(
                        severity="warning",
                        code="FQA_WIDTH_OUT_OF_RANGE",
                        message=(
                            f"{pdf_path.name}: width {width_mm:.1f} mm is outside Nature's "
                            f"single-column ({_SINGLE_COLUMN_MM:.0f} mm) and "
                            f"double-column ({_DOUBLE_COLUMN_MM:.0f} mm) targets "
                            f"(tolerance ±{_WIDTH_TOLERANCE_MM:.0f} mm)."
                        ),
                        location=location,
                        fixup_hint=(
                            "Render the figure spec with width='single' or 'double', or "
                            "adjust the figure spec's font_size / data so the layout fits."
                        ),
                    )
                )

        if not font_records:
            issues.append(
                issue(
                    severity="warning",
                    code="FQA_NO_FONTS_FOUND",
                    message=(
                        f"{pdf_path.name}: no text fonts detected — likely outlined paths. "
                        "Editable text is required for Nature submissions."
                    ),
                    location=location,
                    fixup_hint=(
                        "Re-render with svg.fonttype='none' and pdf.fonttype=42 (the "
                        "toolkit's apply_publication_style sets both)."
                    ),
                )
            )
        for font_name, embedded in font_records:
            if not embedded:
                issues.append(
                    issue(
                        severity="error",
                        code="FQA_FONT_NOT_EMBEDDED",
                        message=(
                            f"{pdf_path.name}: font {font_name!r} is referenced but not embedded."
                        ),
                        location=location,
                        fixup_hint=(
                            "Re-render with pdf.fonttype=42 so TrueType programs are embedded."
                        ),
                    )
                )
            if not _font_is_approved(font_name):
                issues.append(
                    issue(
                        severity="warning",
                        code="FQA_NON_STANDARD_FONT",
                        message=(
                            f"{pdf_path.name}: font {font_name!r} is not Arial / Helvetica / "
                            "DejaVu Sans / Liberation Sans."
                        ),
                        location=location,
                        fixup_hint=(
                            "Set plt.rcParams['font.family'] to a sans-serif fallback (the "
                            "toolkit's apply_publication_style does this)."
                        ),
                    )
                )
        inspected.append(
            {
                "figure_id": figure_id,
                "path": str(pdf_path),
                "width_mm": round(width_mm, 2) if width_mm is not None else None,
                "fonts": [{"name": name, "embedded": embed} for name, embed in font_records],
            }
        )

    return CheckReport(checker="figure-qa", issues=issues, result={"inspected": inspected})
