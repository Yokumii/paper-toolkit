from pathlib import Path

ROOT = Path(__file__).parents[2]
REFS = ROOT / "skills" / "agentsociety-generate-paper" / "references"


def test_skill_references_cover_core_schemas_and_tools() -> None:
    required = [
        "tool_catalog.md",
        "envelope_schema.md",
        "evidence_graph_schema.md",
        "check_report_schema.md",
        "compile_run_schema.md",
    ]
    for name in required:
        text = (REFS / name).read_text(encoding="utf-8")
        assert "paper" in text
        assert "TBD" not in text
        assert "TODO" not in text
