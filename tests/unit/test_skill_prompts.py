from pathlib import Path

ROOT = Path(__file__).parents[2]
PROMPTS = ROOT / "skills" / "agentsociety-generate-paper" / "prompts"


def test_required_prompts_exist_and_are_concrete() -> None:
    names = [
        "writing_abstract.md",
        "writing_intro.md",
        "writing_results.md",
        "writing_discussion.md",
        "writing_methods.md",
        "skeptical_review.md",
        "revision_decision.md",
    ]
    for name in names:
        text = (PROMPTS / name).read_text(encoding="utf-8")
        assert "paper-toolkit" in text
        assert "evidence" in text.lower()
        assert "TBD" not in text
        assert "TODO" not in text
