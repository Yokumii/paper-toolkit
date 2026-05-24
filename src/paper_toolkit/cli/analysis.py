"""`paper analysis ...` command logic.

Each `*_cmd` function returns an `Envelope`; main.py wires them to the
Typer subgroup. None of them call an LLM — judgment lives in the skill.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from paper_toolkit.analysis import (
    checkers,
    lift,
    report_context,
)
from paper_toolkit.analysis import claims as claims_state
from paper_toolkit.analysis import (
    db as analysis_db,
)
from paper_toolkit.analysis import (
    state as analysis_state_io,
)
from paper_toolkit.analysis import (
    synthesis as synthesis_state,
)
from paper_toolkit.envelope import Envelope, ErrorEntry, StateSummary, build_envelope
from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.analysis import (
    AnalysisPlan,
    Claim,
    Language,
    SynthesisClaim,
)
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
)

_VALID_LANGUAGES: tuple[str, ...] = ("en", "zh", "bilingual")
_VALID_KINDS: tuple[str, ...] = ("quantitative", "qualitative", "comparative")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _zero_summary() -> StateSummary:
    from paper_toolkit.cli.main import _zero_summary as zero

    return zero()


def _state_summary(workspace: Path) -> StateSummary:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _zero_summary()
    return compute_state_summary(workspace=workspace, state=state)


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
                fixup_hint="Run: paper init --title ... --venue nature --language en",
            )
        ],
    )


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _resolve_language(
    *,
    workspace: Path,
    language: str | None,
) -> Language:
    """Resolve language: CLI flag > paper.json:meta.language > 'bilingual'."""
    if language is not None:
        if language not in _VALID_LANGUAGES:
            raise ValueError(f"language must be one of {_VALID_LANGUAGES}; got {language!r}")
        return language  # type: ignore[return-value]
    try:
        paper_state = read_state(workspace=workspace)
        return paper_state.meta.language
    except WorkspaceNotInitialized:
        return "bilingual"


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "query"


# --- init / plan ---------------------------------------------------------


def init_cmd(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    db_path: Path,
    language: str | None,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="analysis.init")

    if not db_path.is_file():
        return build_envelope(
            action="analysis.init",
            result={"db_path": str(db_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="ANL_DB_NOT_FOUND",
                    message=f"sqlite database not found at {db_path}",
                )
            ],
        )
    try:
        resolved_language = _resolve_language(workspace=workspace, language=language)
    except ValueError as exc:
        return build_envelope(
            action="analysis.init",
            result={},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_BAD_LANGUAGE", message=str(exc))],
        )

    state, config = analysis_state_io.init_experiment(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
        db_path=db_path,
        language=resolved_language,
    )
    return build_envelope(
        action="analysis.init",
        result={
            "hypothesis_id": state.hypothesis_id,
            "experiment_id": state.experiment_id,
            "db_path": state.db_path,
            "language": config.language,
            "experiment_dir": str(
                WorkspacePaths(workspace=workspace).experiment_dir(
                    hypothesis_id=hypothesis_id, experiment_id=experiment_id
                )
            ),
        },
        state_summary=_state_summary(workspace),
    )


def write_plan_cmd(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    payload_path: Path,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="analysis.write-plan")

    if not payload_path.is_file():
        return build_envelope(
            action="analysis.write-plan",
            result={"payload": str(payload_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_PAYLOAD_NOT_FOUND", message=str(payload_path))],
        )

    text = payload_path.read_text(encoding="utf-8")
    try:
        if payload_path.suffix.lower() == ".json":
            raw = json.loads(text)
        else:
            raw = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        return build_envelope(
            action="analysis.write-plan",
            result={"payload": str(payload_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_PAYLOAD_INVALID", message=str(exc))],
        )
    if not isinstance(raw, dict):
        return build_envelope(
            action="analysis.write-plan",
            result={"payload": str(payload_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="ANL_PAYLOAD_INVALID",
                    message="payload must be a mapping/object",
                )
            ],
        )
    raw.setdefault("hypothesis_id", hypothesis_id)
    raw.setdefault("experiment_id", experiment_id)
    try:
        plan = AnalysisPlan.model_validate(raw)
    except ValidationError as exc:
        return build_envelope(
            action="analysis.write-plan",
            result={"payload": str(payload_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_PLAN_INVALID", message=str(exc))],
        )
    if plan.hypothesis_id != hypothesis_id or plan.experiment_id != experiment_id:
        return build_envelope(
            action="analysis.write-plan",
            result={
                "hypothesis_id": plan.hypothesis_id,
                "experiment_id": plan.experiment_id,
            },
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="ANL_PLAN_ID_MISMATCH",
                    message=(
                        f"plan ids ({plan.hypothesis_id}/{plan.experiment_id}) do not match "
                        f"arguments ({hypothesis_id}/{experiment_id})"
                    ),
                )
            ],
        )
    analysis_state_io.write_plan(workspace=workspace, plan=plan)
    return build_envelope(
        action="analysis.write-plan",
        result={
            "plan_path": str(
                WorkspacePaths(workspace=workspace).analysis_plan(
                    hypothesis_id=hypothesis_id, experiment_id=experiment_id
                )
            ),
            "must_inspect": plan.must_inspect,
            "expected_claim_count": plan.expected_claim_count,
        },
        state_summary=_state_summary(workspace),
    )


# --- DB introspection ---------------------------------------------------


def list_tables_cmd(
    *,
    workspace: Path,
    db_path: Path,
) -> Envelope:
    try:
        summaries = analysis_db.list_tables(db_path=db_path)
    except analysis_db.DBPathNotFound as exc:
        return build_envelope(
            action="analysis.list-tables",
            result={"db_path": str(db_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_DB_NOT_FOUND", message=str(exc))],
        )
    except sqlite3.DatabaseError as exc:
        return build_envelope(
            action="analysis.list-tables",
            result={"db_path": str(db_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_DB_INVALID", message=str(exc))],
        )
    payload = [
        {
            "name": s.name,
            "row_count": s.row_count,
            "columns": [
                {
                    "name": c.name,
                    "declared_type": c.declared_type,
                    "nullable": c.nullable,
                    "is_primary_key": c.is_primary_key,
                }
                for c in s.columns
            ],
        }
        for s in summaries
    ]
    return build_envelope(
        action="analysis.list-tables",
        result={"db_path": str(db_path), "tables": payload, "table_count": len(payload)},
        state_summary=_state_summary(workspace),
    )


def profile_table_cmd(
    *,
    workspace: Path,
    db_path: Path,
    table: str,
    sample_rows: int,
    hypothesis_id: str | None,
    experiment_id: str | None,
) -> Envelope:
    try:
        profile = analysis_db.profile_table(db_path=db_path, table=table, sample_rows=sample_rows)
    except analysis_db.DBPathNotFound as exc:
        return build_envelope(
            action="analysis.profile-table",
            result={"db_path": str(db_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_DB_NOT_FOUND", message=str(exc))],
        )
    except ValueError as exc:
        return build_envelope(
            action="analysis.profile-table",
            result={"db_path": str(db_path), "table": table},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_TABLE_NOT_FOUND", message=str(exc))],
        )
    except sqlite3.DatabaseError as exc:
        return build_envelope(
            action="analysis.profile-table",
            result={"db_path": str(db_path), "table": table},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_DB_INVALID", message=str(exc))],
        )
    payload_columns = [asdict(col) for col in profile.columns]
    payload = {
        "table": profile.table,
        "row_count": profile.row_count,
        "sampled_rows": profile.sampled_rows,
        "columns": payload_columns,
    }
    output_path: Path | None = None
    if hypothesis_id and experiment_id:
        try:
            read_state(workspace=workspace)
        except WorkspaceNotInitialized:
            return _missing_workspace_envelope(workspace=workspace, action="analysis.profile-table")
        paths = WorkspacePaths(workspace=workspace)
        eda_dir = paths.eda_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
        eda_dir.mkdir(parents=True, exist_ok=True)
        output_path = eda_dir / f"{table}_profile.json"
        write_atomic_text(
            output_path,
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
        analysis_state_io.touch_state(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
            profiled_table=table,
        )
    result: dict[str, object] = dict(payload)
    result["db_path"] = str(db_path)
    if output_path is not None:
        result["out_path"] = str(output_path)
    return build_envelope(
        action="analysis.profile-table",
        result=result,
        state_summary=_state_summary(workspace),
    )


def query_cmd(
    *,
    workspace: Path,
    db_path: Path,
    sql: str,
    limit: int,
    allow_select_all: bool,
    out_path: Path | None,
    hypothesis_id: str | None,
    experiment_id: str | None,
) -> Envelope:
    try:
        result_obj = analysis_db.query(
            db_path=db_path,
            sql=sql,
            limit=limit,
            allow_select_all=allow_select_all,
        )
    except analysis_db.DBPathNotFound as exc:
        return build_envelope(
            action="analysis.query",
            result={"db_path": str(db_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_DB_NOT_FOUND", message=str(exc))],
        )
    except analysis_db.DBQueryRefused as exc:
        return build_envelope(
            action="analysis.query",
            result={"db_path": str(db_path), "sql": sql},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="ANL_QUERY_REFUSED",
                    message=str(exc),
                    fixup_hint=("Name the columns explicitly or pass --allow-select-all."),
                )
            ],
        )
    except sqlite3.DatabaseError as exc:
        return build_envelope(
            action="analysis.query",
            result={"db_path": str(db_path), "sql": sql},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_DB_INVALID", message=str(exc))],
        )
    payload = {
        "db_path": str(db_path),
        "sql": sql,
        "columns": result_obj.columns,
        "rows": result_obj.rows,
        "row_count": len(result_obj.rows),
        "truncated": result_obj.truncated,
    }
    written: Path | None = None
    if out_path is not None or (hypothesis_id and experiment_id):
        try:
            read_state(workspace=workspace)
        except WorkspaceNotInitialized:
            return _missing_workspace_envelope(workspace=workspace, action="analysis.query")
        if out_path is not None:
            target = out_path
        else:
            assert hypothesis_id and experiment_id
            paths = WorkspacePaths(workspace=workspace)
            eda_dir = paths.eda_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
            (eda_dir / "queries").mkdir(parents=True, exist_ok=True)
            target = eda_dir / "queries" / f"{_slugify(sql)[:60]}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic_text(target, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        written = target
        if hypothesis_id and experiment_id:
            analysis_state_io.touch_state(
                workspace=workspace,
                hypothesis_id=hypothesis_id,
                experiment_id=experiment_id,
                last_query_slug=target.stem,
            )
    if written is not None:
        payload["out_path"] = str(written)
    return build_envelope(
        action="analysis.query",
        result=payload,
        state_summary=_state_summary(workspace),
    )


# --- claims / refine ----------------------------------------------------


def record_claim_cmd(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    claim_id: str,
    text: str,
    kind: str,
    evidence: str,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="analysis.record-claim")
    if kind not in _VALID_KINDS:
        return build_envelope(
            action="analysis.record-claim",
            result={},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="ANL_BAD_KIND",
                    message=f"kind must be one of {_VALID_KINDS}; got {kind!r}",
                )
            ],
        )
    try:
        claim = Claim(claim_id=claim_id, text=text, kind=kind, evidence=evidence)  # type: ignore[arg-type]
    except ValidationError as exc:
        return build_envelope(
            action="analysis.record-claim",
            result={},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_CLAIM_INVALID", message=str(exc))],
        )
    claims_file = claims_state.upsert_claim(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
        claim=claim,
    )
    analysis_state_io.touch_state(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
        claim_count=len(claims_file.claims),
    )
    return build_envelope(
        action="analysis.record-claim",
        result={
            "claim_id": claim_id,
            "claim_count": len(claims_file.claims),
        },
        state_summary=_state_summary(workspace),
    )


def record_figure_contract_cmd(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    claim_id: str,
    figure_id: str,
    rationale: str,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(
            workspace=workspace, action="analysis.record-figure-contract"
        )
    try:
        claims_state.attach_figure_contract(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
            claim_id=claim_id,
            figure_id=figure_id,
            rationale=rationale,
        )
    except claims_state.ClaimsFileNotFound as exc:
        return build_envelope(
            action="analysis.record-figure-contract",
            result={},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_CLAIMS_MISSING", message=str(exc))],
        )
    except ValueError as exc:
        return build_envelope(
            action="analysis.record-figure-contract",
            result={"claim_id": claim_id},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_CLAIM_NOT_FOUND", message=str(exc))],
        )
    return build_envelope(
        action="analysis.record-figure-contract",
        result={
            "claim_id": claim_id,
            "figure_id": figure_id,
            "rationale": rationale,
        },
        state_summary=_state_summary(workspace),
    )


# --- check-* gates ------------------------------------------------------


def _check_dispatch(
    *,
    workspace: Path,
    action: str,
    fn: Callable[..., tuple[list[ErrorEntry], list[str]]],
    **kwargs: object,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action=action)
    errors, warnings = fn(workspace=workspace, **kwargs)
    return build_envelope(
        action=action,
        result={"error_count": len(errors), "warning_count": len(warnings)},
        state_summary=_state_summary(workspace),
        errors=errors,
        warnings=warnings,
    )


def check_plan_cmd(*, workspace: Path, hypothesis_id: str, experiment_id: str) -> Envelope:
    return _check_dispatch(
        workspace=workspace,
        action="analysis.check-plan",
        fn=checkers.check_plan,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )


def check_explore_cmd(*, workspace: Path, hypothesis_id: str, experiment_id: str) -> Envelope:
    return _check_dispatch(
        workspace=workspace,
        action="analysis.check-explore",
        fn=checkers.check_explore,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )


def check_claims_cmd(*, workspace: Path, hypothesis_id: str, experiment_id: str) -> Envelope:
    return _check_dispatch(
        workspace=workspace,
        action="analysis.check-claims",
        fn=checkers.check_claims,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )


def check_refine_cmd(*, workspace: Path, hypothesis_id: str, experiment_id: str) -> Envelope:
    return _check_dispatch(
        workspace=workspace,
        action="analysis.check-refine",
        fn=checkers.check_refine,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )


def check_release_cmd(*, workspace: Path, hypothesis_id: str, experiment_id: str) -> Envelope:
    return _check_dispatch(
        workspace=workspace,
        action="analysis.check-release",
        fn=checkers.check_release,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )


def check_synthesis_cmd(*, workspace: Path, hypothesis_id: str) -> Envelope:
    return _check_dispatch(
        workspace=workspace,
        action="analysis.check-synthesis",
        fn=checkers.check_synthesis,
        hypothesis_id=hypothesis_id,
    )


# --- produce / synthesize / lift ---------------------------------------


def build_report_context_cmd(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(
            workspace=workspace, action="analysis.build-report-context"
        )
    try:
        result = report_context.build_report_context(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        )
    except claims_state.ClaimsFileNotFound as exc:
        return build_envelope(
            action="analysis.build-report-context",
            result={},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_CLAIMS_MISSING", message=str(exc))],
        )
    return build_envelope(
        action="analysis.build-report-context",
        result={
            "claim_count": result.claim_count,
            "report_context_path": str(result.report_context_path),
            "evidence_index_path": str(result.evidence_index_path),
        },
        state_summary=_state_summary(workspace),
    )


def build_synthesis_brief_cmd(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiments: list[str],
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(
            workspace=workspace, action="analysis.build-synthesis-brief"
        )
    if not experiments:
        return build_envelope(
            action="analysis.build-synthesis-brief",
            result={},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="ANL_NO_EXPERIMENTS",
                    message="at least one --experiment-id is required",
                )
            ],
        )

    aggregated: dict[str, SynthesisClaim] = {}
    missing: list[str] = []
    for experiment_id in experiments:
        try:
            claims_file = claims_state.read_claims(
                workspace=workspace,
                hypothesis_id=hypothesis_id,
                experiment_id=experiment_id,
            )
        except claims_state.ClaimsFileNotFound:
            missing.append(experiment_id)
            continue
        for claim in claims_file.claims:
            existing = aggregated.get(claim.claim_id)
            if existing is None:
                aggregated[claim.claim_id] = SynthesisClaim(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    source_experiments=[experiment_id],
                )
            else:
                if experiment_id not in existing.source_experiments:
                    existing.source_experiments = [
                        *existing.source_experiments,
                        experiment_id,
                    ]
    errors: list[ErrorEntry] = []
    if missing:
        errors.append(
            ErrorEntry(
                code="ANL_EXPERIMENT_MISSING",
                message=f"no claims.json for: {', '.join(missing)}",
                fixup_hint="Run paper analysis record-claim for each missing experiment.",
            )
        )

    if not aggregated and not errors:
        errors.append(
            ErrorEntry(
                code="ANL_SYNTHESIS_EMPTY",
                message="no claims aggregated; nothing to write",
            )
        )

    if errors:
        return build_envelope(
            action="analysis.build-synthesis-brief",
            result={},
            state_summary=_state_summary(workspace),
            errors=errors,
        )

    brief = None
    for sclaim in aggregated.values():
        brief = synthesis_state.upsert_synthesis_claim(
            workspace=workspace, hypothesis_id=hypothesis_id, claim=sclaim
        )
    assert brief is not None
    return build_envelope(
        action="analysis.build-synthesis-brief",
        result={
            "hypothesis_id": hypothesis_id,
            "experiments": brief.experiments,
            "claim_count": len(brief.claims),
            "path": str(
                WorkspacePaths(workspace=workspace).synthesis_brief(hypothesis_id=hypothesis_id)
            ),
        },
        state_summary=_state_summary(workspace),
    )


def lift_to_evidence_cmd(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> Envelope:
    try:
        result = lift.lift_claims_to_evidence(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        )
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="analysis.lift-to-evidence")
    except claims_state.ClaimsFileNotFound as exc:
        return build_envelope(
            action="analysis.lift-to-evidence",
            result={},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="ANL_CLAIMS_MISSING", message=str(exc))],
        )
    return build_envelope(
        action="analysis.lift-to-evidence",
        result={
            "added_claims": result.added_claims,
            "added_evidence": result.added_evidence,
            "added_edges": [list(e) for e in result.added_edges],
            "skipped_claims": result.skipped_claims,
        },
        state_summary=_state_summary(workspace),
    )


# --- status -------------------------------------------------------------


_STAGES: tuple[str, ...] = (
    "frame",
    "explore",
    "claims",
    "refine",
    "produce",
    "synthesis",
)


def _derive_stage(*, workspace: Path, hypothesis_id: str, experiment_id: str) -> str:
    """Return the highest completed stage name (or 'init' if none)."""
    plan_errors, _ = checkers.check_plan(
        workspace=workspace, hypothesis_id=hypothesis_id, experiment_id=experiment_id
    )
    if plan_errors:
        return "init"
    explore_errors, _ = checkers.check_explore(
        workspace=workspace, hypothesis_id=hypothesis_id, experiment_id=experiment_id
    )
    if explore_errors:
        return "frame"
    claims_errors, _ = checkers.check_claims(
        workspace=workspace, hypothesis_id=hypothesis_id, experiment_id=experiment_id
    )
    if claims_errors:
        return "explore"
    refine_errors, _ = checkers.check_refine(
        workspace=workspace, hypothesis_id=hypothesis_id, experiment_id=experiment_id
    )
    if refine_errors:
        return "claims"
    release_errors, _ = checkers.check_release(
        workspace=workspace, hypothesis_id=hypothesis_id, experiment_id=experiment_id
    )
    if release_errors:
        return "refine"
    synth_errors, _ = checkers.check_synthesis(workspace=workspace, hypothesis_id=hypothesis_id)
    if synth_errors:
        return "produce"
    return "synthesis"


def status_cmd(
    *,
    workspace: Path,
    hypothesis_id: str | None,
) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="analysis.status")
    paths = WorkspacePaths(workspace=workspace)
    analysis_dir = paths.analysis_dir
    experiments: list[dict[str, object]] = []
    if analysis_dir.exists():
        if hypothesis_id is not None:
            hypothesis_dirs = [analysis_dir / hypothesis_id]
        else:
            hypothesis_dirs = sorted(
                d for d in analysis_dir.iterdir() if d.is_dir() and d.name != "synthesis"
            )
        for hdir in hypothesis_dirs:
            if not hdir.exists():
                continue
            for edir in sorted(d for d in hdir.iterdir() if d.is_dir()):
                stage = _derive_stage(
                    workspace=workspace,
                    hypothesis_id=hdir.name,
                    experiment_id=edir.name,
                )
                experiments.append(
                    {
                        "hypothesis_id": hdir.name,
                        "experiment_id": edir.name,
                        "stage": stage,
                    }
                )
    return build_envelope(
        action="analysis.status",
        result={"experiments": experiments, "stages": list(_STAGES)},
        state_summary=_state_summary(workspace),
    )
