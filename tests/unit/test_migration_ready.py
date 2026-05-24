import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_migration_ready_script_reports_required_plan_tags() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_migration_ready.py"), "--repo", str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode in {0, 1}
    assert "plan-01-foundation" in result.stdout
    assert "plan-05-templates-skill-migration" in result.stdout
