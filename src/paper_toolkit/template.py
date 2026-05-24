"""Template discovery and slot expansion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.paths import WorkspacePaths

_SLOT_RE = re.compile(r"\{\{slot:([^|}]+)(?:\|([^}]+))?\}\}")


@dataclass(frozen=True)
class TemplateExpandResult:
    section: str
    path: Path
    source: str


def _parse_attrs(raw: str | None) -> dict[str, str]:
    attrs: dict[str, str] = {}
    if not raw:
        return attrs
    for part in raw.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        attrs[key.strip()] = value.strip().strip('"')
    return attrs


def render_slot_placeholder(slot_text: str) -> str:
    match = _SLOT_RE.fullmatch(slot_text.strip())
    if match is None:
        return slot_text
    name = match.group(1).strip()
    attrs = _parse_attrs(match.group(2))
    lines = [f"% slot: {name}"]
    for key in sorted(attrs):
        lines.append(f"% {key}: {attrs[key]}")
    lines.append(f"\\textbf{{[{name}]}}")
    return "\n".join(lines)


def _expand_slots(text: str) -> str:
    return _SLOT_RE.sub(lambda match: render_slot_placeholder(match.group(0)), text)


def _builtin_template_path(section: str) -> Path:
    resource = files("paper_toolkit.templates").joinpath("nature", "sections", f"{section}.tex")
    return Path(str(resource))


def _workspace_template_path(paths: WorkspacePaths, section: str) -> Path:
    return paths.paper_dir / "templates" / "sections" / f"{section}.tex"


def _template_source(paths: WorkspacePaths, section: str) -> tuple[Path, str]:
    workspace_template = _workspace_template_path(paths, section)
    if workspace_template.exists():
        return workspace_template, "workspace"
    builtin = _builtin_template_path(section)
    if not builtin.exists():
        raise FileNotFoundError(f"template not found for section {section!r}")
    return builtin, "builtin:nature"


def list_templates(*, workspace: Path) -> list[str]:
    paths = WorkspacePaths(workspace=workspace)
    names = {path.stem for path in _builtin_template_path("intro").parent.glob("*.tex")}
    workspace_dir = paths.paper_dir / "templates" / "sections"
    if workspace_dir.exists():
        names.update(path.stem for path in workspace_dir.glob("*.tex"))
    return sorted(names)


def expand_template(*, workspace: Path, section: str, target: Path | None) -> TemplateExpandResult:
    paths = WorkspacePaths(workspace=workspace)
    source_path, source_name = _template_source(paths, section)
    rendered = _expand_slots(source_path.read_text(encoding="utf-8"))
    out = (
        target.resolve()
        if target is not None
        else (paths.sections_dir / f"{section}.tex").resolve()
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(out, rendered)
    return TemplateExpandResult(section=section, path=out, source=source_name)
