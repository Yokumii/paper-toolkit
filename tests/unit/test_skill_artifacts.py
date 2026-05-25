import json
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_skill_frontmatter_and_no_phase_machine() -> None:
    text = (ROOT / "skills" / "agentsociety-generate-paper" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert text.startswith("---\n")
    assert "name: agentsociety-generate-paper" in text
    assert "description:" in text
    assert "No phase machine" in text
    assert "paper init" in text
    assert "paper template expand" in text


def test_plugin_manifest_valid_minimal_shape() -> None:
    data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert data["name"] == "paper-toolkit"
    assert data["version"] == "0.1.2"
    assert data["skills"] == "./skills/"
    assert data["author"]["name"] == "AgentSociety"
    assert data["interface"]["displayName"] == "Paper Toolkit"
    assert "Write" in data["interface"]["capabilities"]
