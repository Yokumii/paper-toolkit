#!/usr/bin/env python3
"""Check paper-toolkit migration readiness gates."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

REQUIRED_TAGS = [
    "plan-01-foundation",
    "plan-02-scanner-evidence",
    "plan-03-compose-typeset",
    "plan-04-checkers",
    "plan-05-templates-skill-migration",
]


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()
    tags = set(_git(repo, "tag", "--list", "plan-*").splitlines())
    status = _git(repo, "status", "--short").strip()
    missing = [tag for tag in REQUIRED_TAGS if tag not in tags]
    for tag in REQUIRED_TAGS:
        print(f"{tag}: {'present' if tag in tags else 'missing'}")
    print(f"working_tree: {'clean' if not status else 'dirty'}")
    return 0 if not missing and not status else 1


if __name__ == "__main__":
    raise SystemExit(main())
