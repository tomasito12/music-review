"""Types for data-quality findings and run configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class Finding:
    """One rule outcome (error or warning)."""

    code: str
    severity: Severity
    message: str
    path: str | None = None
    details: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class DataQualityConfig:
    """Inputs and thresholds for a DQ run."""

    reviews_path: Path
    metadata_imputed_path: Path
    output_report_path: Path
    expect_graph_artifacts: bool
    strict: bool
    empty_text_warn_rate: float = 0.01
    missing_metadata_warn_rate: float = 0.50
    short_text_chars: int = 50
    short_text_warn_rate: float = 0.01
    rating_min: float = 0.0
    rating_max: float = 15.0
    year_min: int = 1900


@dataclass(slots=True)
class DataQualityResult:
    """Outcome of ``run_data_quality`` including exit semantics."""

    findings: list[Finding]
    report_path: Path | None
    exit_code: int

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


@dataclass(slots=True)
class ReviewScanStats:
    """Aggregates from streaming ``reviews.jsonl`` (for metadata join)."""

    review_ids: set[int] = field(default_factory=set)
    valid_review_count: int = 0
    non_empty_line_count: int = 0
    invalid_json_lines: int = 0
    empty_text_count: int = 0
    short_text_count: int = 0
    missing_required_field_count: int = 0
    bad_year_count: int = 0
    bad_rating_count: int = 0
    duplicate_ids: list[int] = field(default_factory=list)
