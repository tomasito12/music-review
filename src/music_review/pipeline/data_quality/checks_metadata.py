"""Rules for imputed metadata JSONL (``review_id``, duplicates, coverage)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from music_review.pipeline.data_quality.models import Finding


def scan_metadata_imputed(
    path: Path,
    review_ids: set[int],
    *,
    missing_metadata_warn_rate: float,
) -> list[Finding]:
    """Check metadata file for duplicates and coverage vs. review id set."""
    findings: list[Finding] = []

    if not path.exists():
        findings.append(
            Finding(
                code="METADATA_IMPUTED_MISSING",
                severity="warning",
                message=f"Imputed metadata file does not exist: {path}",
                path=str(path),
            ),
        )
        return findings

    seen: set[int] = set()
    duplicates: list[int] = []
    meta_ids: set[int] = set()
    invalid_lines = 0

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                obj: Any = json.loads(raw)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if not isinstance(obj, dict):
                invalid_lines += 1
                continue
            rid = obj.get("review_id")
            if not isinstance(rid, int):
                invalid_lines += 1
                continue
            if rid in seen:
                duplicates.append(rid)
            seen.add(rid)
            meta_ids.add(rid)

    dup_u = sorted(set(duplicates))
    if dup_u:
        findings.append(
            Finding(
                code="METADATA_DUPLICATE_REVIEW_ID",
                severity="error",
                message=(
                    f"Duplicate review_id in {path.name}: "
                    f"{len(dup_u)} id(s), e.g. {dup_u[:10]!r}"
                ),
                path=str(path),
                details={"sample_ids": dup_u[:20]},
            ),
        )

    if invalid_lines > 0:
        findings.append(
            Finding(
                code="METADATA_INVALID_LINES",
                severity="warning",
                message=(
                    f"Non-parseable lines or rows without integer review_id: "
                    f"{invalid_lines}."
                ),
                path=str(path),
                details={"invalid_lines": invalid_lines},
            ),
        )

    if review_ids and meta_ids:
        missing = review_ids - meta_ids
        rate = len(missing) / len(review_ids)
        if rate > missing_metadata_warn_rate:
            sample = sorted(missing)[:15]
            findings.append(
                Finding(
                    code="METADATA_COVERAGE_LOW",
                    severity="warning",
                    message=(
                        f"Share of reviews without imputed metadata row {rate:.2%} "
                        f"exceeds threshold {missing_metadata_warn_rate:.2%} "
                        f"({len(missing)}/{len(review_ids)} missing)."
                    ),
                    path=str(path),
                    details={
                        "missing_count": len(missing),
                        "review_id_count": len(review_ids),
                        "rate": rate,
                        "threshold": missing_metadata_warn_rate,
                        "sample_missing_ids": sample,
                    },
                ),
            )

    return findings
