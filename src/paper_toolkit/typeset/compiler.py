"""Run one immutable LaTeX compile attempt under paper/compile_runs/rN/.

Orchestration choices:
- `bibtex` returning non-zero is **not fatal** to the run: bibtex returns 2 when
  the document has no `\\cite{}` calls, which is normal. We continue the
  pdflatex passes regardless and let log-parse errors decide `ok`.
- All subprocess calls are guarded against `subprocess.TimeoutExpired` and
  turned into a `LatexError(code="other", ...)`.
- `max_print_line=200` is passed to pdflatex so warnings don't hard-wrap at
  column 79 (defence-in-depth — the log parser also un-wraps).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.compile_run import CompileRunResult, LatexError
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.typeset.log_parser import parse_latex_log
from paper_toolkit.typeset.page_inspector import render_compile_pages

CommandRunner = Callable[[list[str], Path], tuple[int, str, str]]

_SUBPROCESS_TIMEOUT_SECONDS = 600
_MAX_PRINT_LINE = "200"


def next_run_id(*, workspace: Path) -> str:
    paths = WorkspacePaths(workspace=workspace)
    existing = []
    if paths.compile_runs_dir.exists():
        for path in paths.compile_runs_dir.iterdir():
            if path.is_dir() and path.name.startswith("r") and path.name[1:].isdigit():
                existing.append(int(path.name[1:]))
    return f"r{(max(existing) if existing else 0) + 1}"


def _subprocess_runner(command: list[str], cwd: Path) -> tuple[int, str, str]:
    env = dict(os.environ)
    env.setdefault("max_print_line", _MAX_PRINT_LINE)
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        leftover_stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        return -1, leftover_stdout, f"timeout after {_SUBPROCESS_TIMEOUT_SECONDS}s: {exc}"
    return proc.returncode, proc.stdout, proc.stderr


def _write_run_json(paths: WorkspacePaths, result: CompileRunResult) -> None:
    run_path = paths.compile_run_json(result.id)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(
        run_path,
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
    )


def _missing_engine_result(
    *,
    run_id: str,
    engine_name: str,
    paths: WorkspacePaths,
    log_path: Path,
    attempt_index: int,
    started: float,
) -> CompileRunResult:
    return CompileRunResult(
        id=run_id,
        ok=False,
        pdf_path=None,
        log_path=paths.relative_to_workspace(log_path),
        errors=[
            LatexError(
                code="missing-engine",
                message=f"{engine_name!r} not found on PATH",
                fixup_hint=(
                    "Install TeX Live (or a distribution that provides this command) "
                    "and ensure it is on PATH."
                ),
            )
        ],
        warnings=[],
        pages=[],
        attempt_index=attempt_index,
        duration_seconds=time.monotonic() - started,
    )


def compile_once(
    *,
    workspace: Path,
    engine: str = "pdflatex",
    max_attempts: int | None = None,
    runner: CommandRunner | None = None,
) -> CompileRunResult:
    # `max_attempts` is advisory only — emitted as a warning at the CLI layer
    # (see cli/compile.py). The compiler itself never refuses to run.
    del max_attempts  # explicit-acknowledge unused parameter
    started = time.monotonic()
    paths = WorkspacePaths(workspace=workspace)
    run_id = next_run_id(workspace=workspace)
    attempt_index = int(run_id[1:])
    run_dir = paths.compile_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    main_tex = paths.main_tex
    log_path = run_dir / "main.log"
    pdf_path = run_dir / "main.pdf"

    if not main_tex.exists():
        result = CompileRunResult(
            id=run_id,
            ok=False,
            pdf_path=None,
            log_path=paths.relative_to_workspace(log_path),
            errors=[
                LatexError(
                    code="missing-file",
                    message=f"main.tex not found at {main_tex}",
                    fixup_hint="Run paper compose assemble-latex.",
                )
            ],
            warnings=[],
            pages=[],
            attempt_index=attempt_index,
            duration_seconds=time.monotonic() - started,
        )
        _write_run_json(paths, result)
        return result

    command_runner = runner or _subprocess_runner
    if runner is None:
        for required_engine in (engine, "bibtex"):
            if shutil.which(required_engine) is None:
                result = _missing_engine_result(
                    run_id=run_id,
                    engine_name=required_engine,
                    paths=paths,
                    log_path=log_path,
                    attempt_index=attempt_index,
                    started=started,
                )
                _write_run_json(paths, result)
                return result

    _tex_cmd = [
        engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(run_dir),
        str(main_tex),
    ]
    # bibtex respects `openout_any = p` (paranoid) on a default TeX Live install,
    # which refuses to write `.bbl`/`.blg` to absolute paths even inside the
    # workspace. We pass a path relative to `paths.paper_dir` (the cwd of every
    # step) so bibtex stays inside its sandbox and still locates `refs.bib`.
    bibtex_arg = str((run_dir / "main").relative_to(paths.paper_dir))
    sequence: list[tuple[str, list[str]]] = [
        ("pdflatex", _tex_cmd),
        ("bibtex", ["bibtex", bibtex_arg]),
        ("pdflatex", _tex_cmd),
        ("pdflatex", _tex_cmd),
    ]
    final_pdflatex_return_code = 0
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    for name, command in sequence:
        return_code, stdout, stderr = command_runner(command, paths.paper_dir)
        stdout_parts.append(stdout)
        stderr_parts.append(stderr)
        if name == "pdflatex":
            final_pdflatex_return_code = return_code
            # Abort only if pdflatex itself fails — bibtex non-zero is tolerated.
            if return_code != 0:
                break

    if not log_path.exists():
        write_atomic_text(log_path, "\n".join(stdout_parts + stderr_parts))
    parsed = parse_latex_log(log_path.read_text(encoding="utf-8", errors="replace"))
    ok = final_pdflatex_return_code == 0 and pdf_path.exists() and not parsed.errors

    pages = render_compile_pages(
        run_id=run_id, run_dir=run_dir, pdf_path=pdf_path if pdf_path.exists() else None
    )

    result = CompileRunResult(
        id=run_id,
        ok=ok,
        pdf_path=paths.relative_to_workspace(pdf_path) if pdf_path.exists() else None,
        log_path=paths.relative_to_workspace(log_path),
        errors=parsed.errors,
        warnings=parsed.warnings,
        pages=pages,
        attempt_index=attempt_index,
        duration_seconds=time.monotonic() - started,
    )
    _write_run_json(paths, result)
    return result
