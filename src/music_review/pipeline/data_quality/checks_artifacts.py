"""Optional checks for graph pipeline outputs."""

from __future__ import annotations

from pathlib import Path

from music_review.config import resolve_data_path
from music_review.pipeline.data_quality.models import Finding


def _non_empty_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return -1
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def check_graph_artifacts() -> list[Finding]:
    """Ensure community and affinity exports exist and are non-empty."""
    findings: list[Finding] = []
    data_dir = resolve_data_path("data")
    memberships = data_dir / "community_memberships.jsonl"
    affinities = data_dir / "album_community_affinities.jsonl"

    for label, path in (
        ("community_memberships", memberships),
        ("album_community_affinities", affinities),
    ):
        n = _non_empty_jsonl_lines(path)
        if n < 0:
            findings.append(
                Finding(
                    code=f"ARTIFACT_{label.upper()}_MISSING",
                    severity="error",
                    message=f"Expected graph artifact missing: {path}",
                    path=str(path),
                ),
            )
        elif n == 0:
            findings.append(
                Finding(
                    code=f"ARTIFACT_{label.upper()}_EMPTY",
                    severity="error",
                    message=f"Graph artifact is empty: {path}",
                    path=str(path),
                ),
            )

    return findings
