"""Rules for ``reviews.jsonl`` (structure, duplicates, null rates, outliers)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from music_review.pipeline.data_quality.models import Finding, ReviewScanStats

_REQUIRED_KEYS = ("id", "url", "artist", "album", "text")


def scan_reviews_jsonl(
    path: Path,
    *,
    short_text_chars: int,
    year_min: int,
    rating_min: float,
    rating_max: float,
    empty_text_warn_rate: float,
    short_text_warn_rate: float = 0.01,
) -> tuple[list[Finding], ReviewScanStats]:
    """Stream reviews file once; return findings and stats for downstream checks."""
    stats = ReviewScanStats()
    findings: list[Finding] = []

    if not path.exists():
        findings.append(
            Finding(
                code="REVIEWS_FILE_MISSING",
                severity="warning",
                message=f"Reviews file does not exist: {path}",
                path=str(path),
            ),
        )
        return findings, stats

    seen_ids: set[int] = set()
    year_max = datetime.now(tz=UTC).year + 1

    with path.open("r", encoding="utf-8") as f:
        for _line_number, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            stats.non_empty_line_count += 1
            try:
                obj: Any = json.loads(raw)
            except json.JSONDecodeError:
                stats.invalid_json_lines += 1
                continue

            if not isinstance(obj, dict):
                stats.invalid_json_lines += 1
                continue

            rid = obj.get("id")
            if not isinstance(rid, int):
                continue

            if rid in seen_ids:
                stats.duplicate_ids.append(rid)
            seen_ids.add(rid)
            stats.valid_review_count += 1

            missing = [k for k in _REQUIRED_KEYS if _is_empty_value(obj.get(k))]
            if missing:
                stats.missing_required_field_count += 1
            else:
                stats.review_ids.add(rid)

            text_val = obj.get("text")
            if isinstance(text_val, str):
                if not text_val.strip():
                    stats.empty_text_count += 1
                elif len(text_val.strip()) < short_text_chars:
                    stats.short_text_count += 1

            ry = obj.get("release_year")
            if ry is not None:
                try:
                    y = int(ry)
                    if y < year_min or y > year_max:
                        stats.bad_year_count += 1
                except (TypeError, ValueError):
                    stats.bad_year_count += 1

            rt = obj.get("rating")
            if rt is not None:
                try:
                    r = float(rt)
                    if r < rating_min or r > rating_max:
                        stats.bad_rating_count += 1
                except (TypeError, ValueError):
                    stats.bad_rating_count += 1

    dup_unique = sorted(set(stats.duplicate_ids))
    if dup_unique:
        findings.append(
            Finding(
                code="REVIEWS_DUPLICATE_ID",
                severity="error",
                message=(
                    f"Duplicate review id(s) in {path.name}: "
                    f"{len(dup_unique)} id(s), e.g. {dup_unique[:10]!r}"
                ),
                path=str(path),
                details={
                    "duplicate_id_count": len(dup_unique),
                    "sample_ids": dup_unique[:20],
                },
            ),
        )

    if stats.non_empty_line_count > 0 and stats.valid_review_count == 0:
        findings.append(
            Finding(
                code="REVIEWS_ZERO_VALID",
                severity="error",
                message=(
                    f"File has {stats.non_empty_line_count} non-empty line(s) but "
                    "no valid review objects with integer id."
                ),
                path=str(path),
                details={
                    "non_empty_lines": stats.non_empty_line_count,
                    "invalid_json_lines": stats.invalid_json_lines,
                },
            ),
        )

    if stats.valid_review_count > 0:
        empty_rate = stats.empty_text_count / stats.valid_review_count
        if empty_rate > empty_text_warn_rate:
            findings.append(
                Finding(
                    code="REVIEWS_EMPTY_TEXT_RATE",
                    severity="warning",
                    message=(
                        f"Empty review text rate {empty_rate:.2%} exceeds threshold "
                        f"{empty_text_warn_rate:.2%} "
                        f"({stats.empty_text_count}/{stats.valid_review_count})."
                    ),
                    path=str(path),
                    details={
                        "rate": empty_rate,
                        "threshold": empty_text_warn_rate,
                        "empty_count": stats.empty_text_count,
                        "valid_count": stats.valid_review_count,
                    },
                ),
            )

        if stats.short_text_count > 0:
            short_rate = stats.short_text_count / stats.valid_review_count
            if short_rate > short_text_warn_rate:
                findings.append(
                    Finding(
                        code="REVIEWS_SHORT_TEXT_RATE",
                        severity="warning",
                        message=(
                            f"Short text rate {short_rate:.2%} exceeds threshold "
                            f"{short_text_warn_rate:.2%} "
                            f"(<{short_text_chars} chars, "
                            f"{stats.short_text_count}/{stats.valid_review_count})."
                        ),
                        path=str(path),
                        details={
                            "rate": short_rate,
                            "threshold_chars": short_text_chars,
                        },
                    ),
                )

        if stats.bad_year_count > 0:
            findings.append(
                Finding(
                    code="REVIEWS_RELEASE_YEAR_OUTLIER",
                    severity="warning",
                    message=(
                        f"Reviews with release_year outside [{year_min}, {year_max}]: "
                        f"{stats.bad_year_count}."
                    ),
                    path=str(path),
                    details={"count": stats.bad_year_count},
                ),
            )

        if stats.bad_rating_count > 0:
            findings.append(
                Finding(
                    code="REVIEWS_RATING_OUTLIER",
                    severity="warning",
                    message=(
                        f"Reviews with rating outside [{rating_min}, {rating_max}]: "
                        f"{stats.bad_rating_count}."
                    ),
                    path=str(path),
                    details={"count": stats.bad_rating_count},
                ),
            )

        if stats.missing_required_field_count > 0:
            findings.append(
                Finding(
                    code="REVIEWS_MISSING_REQUIRED_FIELDS",
                    severity="warning",
                    message=(
                        f"Reviews missing required non-empty fields "
                        f"(id/url/artist/album/text): "
                        f"{stats.missing_required_field_count} "
                        f"of {stats.valid_review_count} valid ids."
                    ),
                    path=str(path),
                    details={"count": stats.missing_required_field_count},
                ),
            )

    if stats.invalid_json_lines > 0:
        findings.append(
            Finding(
                code="REVIEWS_INVALID_JSON_LINES",
                severity="warning",
                message=(
                    f"Non-parseable or non-object JSON lines in reviews: "
                    f"{stats.invalid_json_lines}."
                ),
                path=str(path),
                details={"invalid_json_lines": stats.invalid_json_lines},
            ),
        )

    return findings, stats


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    return bool(isinstance(value, str) and not value.strip())
