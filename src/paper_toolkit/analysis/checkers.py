"""Deterministic gate checks for the six analysis stages.

Each `check_*` function returns a `(errors, warnings)` tuple of
`paper_toolkit.envelope.ErrorEntry` and plain-string warnings. The CLI
layer wraps the result into an Envelope. No prose-quality judgment; only
filesystem + schema gates.

Stages (derived from artifact presence, not a state-machine flag):

- check_plan: `analysis_plan.yaml` exists, parses, hypothesis/experiment ids match.
- check_explore: every plan `must_inspect` table has a profile under `eda/`.
- check_claims: `claims.json` exists, non-empty, validates, no duplicate ids,
  claim count matches plan's `expected_claim_count` (within a small slack).
- check_refine: every claim has a `figure_contract`; matching FigureSpec
  exists under `paper/figure_specs/<figure_id>.json`; rendered PDF exists
  under `paper/figures/<figure_id>.pdf`.
- check_release: per-language `report_*.md` files exist and are non-empty
  (language comes from `config.yaml`, with paper.json:meta.language as a
  fallback resolved by the caller).
- check_synthesis: `synthesis_brief.json` exists; every claim has
  `lifted_to` set OR `lifted_to_status == "deferred"`.
"""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.analysis import claims as claims_state
from paper_toolkit.analysis import state as state_io
from paper_toolkit.analysis import synthesis as synthesis_state
from paper_toolkit.envelope import ErrorEntry
from paper_toolkit.models.analysis import Language
from paper_toolkit.paths import WorkspacePaths

EDA_PROFILE_SUFFIX = "_profile.json"


def check_plan(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> tuple[list[ErrorEntry], list[str]]:
    errors: list[ErrorEntry] = []
    warnings: list[str] = []
    paths = WorkspacePaths(workspace=workspace)
    plan_path = paths.analysis_plan(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    if not plan_path.exists():
        errors.append(
            ErrorEntry(
                code="ANL_PLAN_MISSING",
                message=f"analysis_plan.yaml not found at {plan_path}",
                fixup_hint="Run: paper analysis write-plan --payload <plan.yaml>",
            )
        )
        return errors, warnings
    try:
        plan = state_io.read_plan(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        )
    except Exception as exc:  # ValidationError or yaml error
        errors.append(
            ErrorEntry(
                code="ANL_PLAN_INVALID",
                message=f"analysis_plan.yaml failed to parse: {exc}",
                fixup_hint="Edit the file and re-run write-plan.",
            )
        )
        return errors, warnings
    if plan.hypothesis_id != hypothesis_id or plan.experiment_id != experiment_id:
        errors.append(
            ErrorEntry(
                code="ANL_PLAN_ID_MISMATCH",
                message=(
                    f"plan ids ({plan.hypothesis_id}/{plan.experiment_id}) "
                    f"do not match arguments ({hypothesis_id}/{experiment_id})"
                ),
            )
        )
    return errors, warnings


def check_explore(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> tuple[list[ErrorEntry], list[str]]:
    errors, warnings = check_plan(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    if errors:
        return errors, warnings
    paths = WorkspacePaths(workspace=workspace)
    plan = state_io.read_plan(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    eda = paths.eda_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    if not eda.exists():
        errors.append(
            ErrorEntry(
                code="ANL_EDA_DIR_MISSING",
                message=f"eda directory not found at {eda}",
                fixup_hint=(
                    "Run paper analysis profile-table for each table in the plan's must_inspect."
                ),
            )
        )
        return errors, warnings
    existing = {p.stem.removesuffix("_profile") for p in eda.glob(f"*{EDA_PROFILE_SUFFIX}")}
    missing = [t for t in plan.must_inspect if t not in existing]
    for table in missing:
        errors.append(
            ErrorEntry(
                code="ANL_EDA_TABLE_MISSING",
                message=f"plan requires table {table!r} but no profile under eda/",
                fixup_hint=f"Run: paper analysis profile-table --db <db> --table {table}",
            )
        )
    return errors, warnings


def check_claims(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> tuple[list[ErrorEntry], list[str]]:
    errors: list[ErrorEntry] = []
    warnings: list[str] = []
    paths = WorkspacePaths(workspace=workspace)
    path = paths.claims_file(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    if not path.exists():
        errors.append(
            ErrorEntry(
                code="ANL_CLAIMS_MISSING",
                message=f"claims.json not found at {path}",
                fixup_hint="Run paper analysis record-claim at least once.",
            )
        )
        return errors, warnings
    try:
        claims = claims_state.read_claims(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        )
    except Exception as exc:
        errors.append(
            ErrorEntry(
                code="ANL_CLAIMS_INVALID",
                message=f"claims.json failed to parse: {exc}",
            )
        )
        return errors, warnings
    if not claims.claims:
        errors.append(
            ErrorEntry(
                code="ANL_CLAIMS_EMPTY",
                message="claims.json contains no claims",
                fixup_hint="Record at least one claim before advancing.",
            )
        )
        return errors, warnings
    seen: set[str] = set()
    for c in claims.claims:
        if c.claim_id in seen:
            errors.append(
                ErrorEntry(
                    code="ANL_CLAIMS_DUP",
                    message=f"duplicate claim_id {c.claim_id!r}",
                )
            )
        seen.add(c.claim_id)
    # Soft warning when claim count is far below plan's expected count.
    try:
        plan = state_io.read_plan(
            workspace=workspace,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
        )
        if len(claims.claims) < plan.expected_claim_count // 2:
            warnings.append(
                f"claim count {len(claims.claims)} is below half of expected "
                f"({plan.expected_claim_count}); revisit explore stage?"
            )
    except state_io.AnalysisPlanNotFound:
        pass
    return errors, warnings


def check_refine(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> tuple[list[ErrorEntry], list[str]]:
    errors, warnings = check_claims(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    if errors:
        return errors, warnings
    paths = WorkspacePaths(workspace=workspace)
    claims = claims_state.read_claims(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    for claim in claims.claims:
        if claim.figure_contract is None:
            errors.append(
                ErrorEntry(
                    code="ANL_REFINE_NO_CONTRACT",
                    message=f"claim {claim.claim_id!r} has no figure_contract",
                    fixup_hint=(
                        "Run: paper analysis record-figure-contract --claim-id ... "
                        "--figure-id ... --rationale ..."
                    ),
                )
            )
            continue
        figure_id = claim.figure_contract.figure_id
        spec_path = paths.figure_specs_dir / f"{figure_id}.json"
        pdf_path = paths.figures_dir / f"{figure_id}.pdf"
        if not spec_path.exists():
            errors.append(
                ErrorEntry(
                    code="ANL_REFINE_SPEC_MISSING",
                    message=f"figure spec {figure_id!r} not found at {spec_path}",
                    fixup_hint=f"Author paper/figure_specs/{figure_id}.json.",
                )
            )
        if not pdf_path.exists():
            errors.append(
                ErrorEntry(
                    code="ANL_REFINE_PDF_MISSING",
                    message=f"rendered figure {figure_id!r} not found at {pdf_path}",
                    fixup_hint=f"Run: paper figure render --spec {spec_path}",
                )
            )
    return errors, warnings


def check_release(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    language: Language | None = None,
) -> tuple[list[ErrorEntry], list[str]]:
    errors: list[ErrorEntry] = []
    warnings: list[str] = []
    paths = WorkspacePaths(workspace=workspace)
    if language is None:
        try:
            cfg = state_io.read_config(
                workspace=workspace,
                hypothesis_id=hypothesis_id,
                experiment_id=experiment_id,
            )
            language = cfg.language
        except state_io.AnalysisConfigNotFound:
            errors.append(
                ErrorEntry(
                    code="ANL_CONFIG_MISSING",
                    message="analysis config.yaml missing; cannot determine language",
                    fixup_hint="Run: paper analysis init --hypothesis-id ... --experiment-id ...",
                )
            )
            return errors, warnings
    required_langs = ["zh", "en"] if language == "bilingual" else [language]
    for lang in required_langs:
        report = paths.report_md(
            hypothesis_id=hypothesis_id, experiment_id=experiment_id, language=lang
        )
        if not report.exists():
            errors.append(
                ErrorEntry(
                    code="ANL_REPORT_MISSING",
                    message=f"report_{lang}.md not found at {report}",
                    fixup_hint=f"Author the report file at {report}.",
                )
            )
            continue
        if report.stat().st_size == 0:
            errors.append(
                ErrorEntry(
                    code="ANL_REPORT_EMPTY",
                    message=f"report_{lang}.md is empty: {report}",
                )
            )
    return errors, warnings


def check_synthesis(
    *,
    workspace: Path,
    hypothesis_id: str,
) -> tuple[list[ErrorEntry], list[str]]:
    errors: list[ErrorEntry] = []
    warnings: list[str] = []
    paths = WorkspacePaths(workspace=workspace)
    path = paths.synthesis_brief(hypothesis_id=hypothesis_id)
    if not path.exists():
        errors.append(
            ErrorEntry(
                code="ANL_SYNTHESIS_MISSING",
                message=f"synthesis_brief.json not found at {path}",
                fixup_hint=(
                    "Run: paper analysis build-synthesis-brief --hypothesis-id ... "
                    "--experiments E1 E2 ..."
                ),
            )
        )
        return errors, warnings
    try:
        brief = synthesis_state.read_brief(workspace=workspace, hypothesis_id=hypothesis_id)
    except Exception as exc:
        errors.append(
            ErrorEntry(
                code="ANL_SYNTHESIS_INVALID",
                message=f"synthesis_brief.json failed to parse: {exc}",
            )
        )
        return errors, warnings
    if not brief.claims:
        errors.append(
            ErrorEntry(
                code="ANL_SYNTHESIS_EMPTY",
                message="synthesis_brief.json has no claims",
            )
        )
        return errors, warnings
    for claim in brief.claims:
        if claim.lifted_to is None and claim.lifted_to_status != "deferred":
            errors.append(
                ErrorEntry(
                    code="ANL_SYNTHESIS_NOT_LIFTED",
                    message=(
                        f"synthesis claim {claim.claim_id!r} is neither lifted "
                        "(lifted_to set) nor explicitly deferred"
                    ),
                    fixup_hint=(
                        "Either run paper analysis lift-to-evidence (for the relevant "
                        "experiment) or mark the claim as deferred in synthesis_brief.json."
                    ),
                )
            )
    return errors, warnings
