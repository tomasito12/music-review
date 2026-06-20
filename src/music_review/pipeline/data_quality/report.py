"""Build JSON-serialisable pipeline health reports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from music_review.pipeline.data_quality.models import DataQualityConfig, Finding


def findings_to_serialisable(findings: list[Finding]) -> list[dict[str, Any]]:
    """Convert findings to JSON-friendly dicts."""
    out: list[dict[str, Any]] = []
    for f in findings:
        d: dict[str, Any] = {
            "code": f.code,
            "severity": f.severity,
            "message": f.message,
        }
        if f.path is not None:
            d["path"] = f.path
        if f.details is not None:
            d["details"] = f.details
        out.append(d)
    return out


def write_report(
    path: Path,
    *,
    findings: list[Finding],
    config_summary: dict[str, Any],
) -> None:
    """Write the health report JSON next to other data artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    payload: dict[str, Any] = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "summary": {
            "error_count": errors,
            "warning_count": warnings,
        },
        "config": config_summary,
        "findings": findings_to_serialisable(findings),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def config_summary_dict(cfg: DataQualityConfig) -> dict[str, Any]:
    """Subset of config safe to persist in reports."""
    return {
        "reviews_path": str(cfg.reviews_path),
        "metadata_imputed_path": str(cfg.metadata_imputed_path),
        "expect_graph_artifacts": cfg.expect_graph_artifacts,
        "strict": cfg.strict,
        "empty_text_warn_rate": cfg.empty_text_warn_rate,
        "missing_metadata_warn_rate": cfg.missing_metadata_warn_rate,
        "short_text_chars": cfg.short_text_chars,
        "short_text_warn_rate": cfg.short_text_warn_rate,
    }
