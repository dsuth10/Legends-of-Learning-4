"""
Scan Adventures graphs and progress rows for integrity issues.

Surfaces:
- Non-optional nodes unreachable from any start (orphans).
- End-flagged nodes unreachable from any start.
- character_node_progress rows pointing at deleted nodes.
- character_adventure_progress.current_node_id pointing at deleted nodes.

Usage (from repo root):
    python scripts/check_adventure_graph_integrity.py
    python scripts/check_adventure_graph_integrity.py --adventure-id 42
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.adventure import Adventure, AdventureNode
from app.models.adventure_progress import (
    CharacterAdventureProgress,
    CharacterNodeProgress,
)
from app.services.adventure_graph import (
    _build_adjacency,
    _reachable_from_starts,
)


@dataclass
class IntegrityIssue:
    code: str
    message: str
    adventure_id: Optional[int] = None
    node_slug: Optional[str] = None


@dataclass
class ScanReport:
    issues: List[IntegrityIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, issue: IntegrityIssue) -> None:
        self.issues.append(issue)


def scan_adventure(adventure: Adventure) -> ScanReport:
    report = ScanReport()
    nodes = list(adventure.nodes)
    edges = list(adventure.edges)
    node_ids = {n.id for n in nodes}
    outbound, inbound = _build_adjacency(nodes, edges)
    reachable = _reachable_from_starts(nodes, outbound, inbound)

    for node in nodes:
        if node.is_end and node.id not in reachable:
            report.add(
                IntegrityIssue(
                    code="END_UNREACHABLE",
                    message=f"End node '{node.slug}' is not reachable from any start.",
                    adventure_id=adventure.id,
                    node_slug=node.slug,
                )
            )
        if not node.is_optional and node.id not in reachable and nodes:
            report.add(
                IntegrityIssue(
                    code="ORPHAN_NODE",
                    message=f"Non-optional node '{node.slug}' is unreachable.",
                    adventure_id=adventure.id,
                    node_slug=node.slug,
                )
            )

    for row in CharacterAdventureProgress.query.filter_by(adventure_id=adventure.id).all():
        if row.current_node_id and row.current_node_id not in node_ids:
            report.add(
                IntegrityIssue(
                    code="DANGLING_CURRENT_NODE",
                    message=(
                        f"character_adventure_progress id={row.id} has "
                        f"current_node_id={row.current_node_id} not in adventure graph."
                    ),
                    adventure_id=adventure.id,
                )
            )

    return report


def scan_dangling_progress_globally() -> ScanReport:
    """Progress rows whose node_id no longer exists in adventure_nodes."""
    report = ScanReport()
    dangling = (
        CharacterNodeProgress.query.outerjoin(
            AdventureNode, AdventureNode.id == CharacterNodeProgress.node_id
        )
        .filter(AdventureNode.id.is_(None))
        .all()
    )
    for row in dangling:
        report.add(
            IntegrityIssue(
                code="DANGLING_NODE_PROGRESS",
                message=(
                    f"character_node_progress id={row.id} references "
                    f"deleted node_id={row.node_id}."
                ),
            )
        )
    return report


def scan_all(*, adventure_id: Optional[int] = None) -> ScanReport:
    combined = ScanReport()
    query = Adventure.query
    if adventure_id is not None:
        query = query.filter_by(id=adventure_id)
    for adventure in query.order_by(Adventure.id).all():
        for issue in scan_adventure(adventure).issues:
            combined.add(issue)
    for issue in scan_dangling_progress_globally().issues:
        combined.add(issue)
    return combined


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Adventures graph integrity scanner")
    parser.add_argument(
        "--adventure-id",
        type=int,
        default=None,
        help="Limit scan to a single adventure id",
    )
    args = parser.parse_args(argv)

    app = create_app()
    with app.app_context():
        report = scan_all(adventure_id=args.adventure_id)

    if report.ok:
        print("Adventures integrity scan: OK (no issues found)")
        return 0

    print(f"Adventures integrity scan: {len(report.issues)} issue(s) found")
    for issue in report.issues:
        prefix = f"[adventure {issue.adventure_id}]" if issue.adventure_id else "[global]"
        slug = f" ({issue.node_slug})" if issue.node_slug else ""
        print(f"  {prefix} {issue.code}{slug}: {issue.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
