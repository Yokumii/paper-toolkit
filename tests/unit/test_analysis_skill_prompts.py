from pathlib import Path

ROOT = Path(__file__).parents[2]
ANALYSIS_ROOT = ROOT / "skills" / "agentsociety-analysis"


def _read(*parts: str) -> str:
    text = (ANALYSIS_ROOT / Path(*parts)).read_text(encoding="utf-8")
    return " ".join(text.split()).lower()


def test_figure_emission_requires_comparative_claims_to_share_a_chart() -> None:
    text = _read("prompts", "figure_emission.md")
    assert (
        "comparative claims must put the compared arms / conditions in the same chart" in text
    )
    assert "may combine rows from sibling experiments when the comparison itself is the claim" in text


def test_figure_contract_rejects_experiment_local_summary_for_comparative_claims() -> None:
    text = _read("references", "figure_contract.md")
    assert (
        "a comparative claim is disqualified if its chart omits one side of the comparison"
        in text
    )
    assert "single-experiment summary" in text


def test_figure_reviewer_requires_post_render_pdf_audit() -> None:
    text = _read("subagent_prompts", "figure-reviewer.md")
    assert "after render, open the pdf" in text
    assert "title clipping" in text
    assert "tick-label overlap" in text
    assert "y-axis truncation" in text


def test_analysis_quality_refine_section_requires_comparator_visible_in_chart() -> None:
    text = _read("references", "analysis_quality.md")
    assert (
        "comparative claim's chart includes every compared arm / condition needed to see the verdict"
        in text
    )


def test_analysis_prompts_explain_when_to_use_structured_vs_script_figures() -> None:
    text = _read("prompts", "figure_emission.md")
    assert "use the structured spec path for common single-chart and composite figures" in text
    assert (
        "use a script-backed figure when the claim needs a layout or modality the built-in chart kinds cannot express"
        in text
    )
