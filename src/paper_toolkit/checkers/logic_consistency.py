"""Logic consistency checker for claim graph."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

from paper_toolkit.checkers.base import issue
from paper_toolkit.models.check_report import CheckReport
from paper_toolkit.models.evidence import GraphNode
from paper_toolkit.state import evidence_graph

_OPPOSITES = [
    ("increase", "decrease"),
    ("increases", "decreases"),
    ("improve", "worsen"),
    ("improves", "worsens"),
    ("positive", "negative"),
]


def _claims_by_id(claims: list[GraphNode]) -> dict[str, GraphNode]:
    return {claim.id: claim for claim in claims}


def _has_opposite_sign(a: str, b: str) -> bool:
    left = a.lower()
    right = b.lower()
    return any((x in left and y in right) or (y in left and x in right) for x, y in _OPPOSITES)


def check_logic_consistency(*, workspace: Path) -> CheckReport:
    graph = evidence_graph.load_or_empty(workspace=workspace)
    claims = [node for node in graph.nodes if node.kind == "claim"]
    by_id = _claims_by_id(claims)
    issues = []
    for edge in graph.edges:
        if edge.kind != "contradicts":
            continue
        src = by_id.get(edge.src)
        dst = by_id.get(edge.dst)
        if src is None or dst is None:
            continue
        issues.append(
            issue(
                severity="error",
                code="LOGIC_DECLARED_CONTRADICTION",
                message=f"claims {src.id!r} and {dst.id!r} are connected by a contradicts edge",
                location=f"edge:{edge.src}->{edge.dst}",
                fixup_hint=(
                    "Resolve the contradiction in prose or remove the "
                    "contradicts edge after revision."
                ),
            )
        )
    for left, right in combinations(claims, 2):
        if (
            left.section
            and right.section
            and left.section == right.section
            and _has_opposite_sign(left.label, right.label)
        ):
            issues.append(
                issue(
                    severity="warning",
                    code="LOGIC_OPPOSITE_SIGN_HEURISTIC",
                    message=(
                        f"claims {left.id!r} and {right.id!r} may point in opposite directions"
                    ),
                    location=f"section:{left.section}",
                    fixup_hint="Check whether both claims can be true in the same section.",
                )
            )
    return CheckReport(checker="logic-consistency", issues=issues)
