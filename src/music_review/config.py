# music_review/config.py

"""Shared configuration and environment setup."""

from __future__ import annotations

from pathlib import Path


def _project_root_for_dotenv() -> Path | None:
    """Resolve repo root when running from a source checkout (`src/music_review/`)."""
    pkg_dir = Path(__file__).resolve().parent
    if pkg_dir.name != "music_review":
        return None
    src_dir = pkg_dir.parent
    if src_dir.name != "src":
        return None
    root = src_dir.parent
    env_file = root / ".env"
    return root if env_file.is_file() else None


def _load_dotenv_files() -> None:
    """Load `.env` from the project checkout first, then fall back to cwd."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    root = _project_root_for_dotenv()
    if root is not None:
        load_dotenv(root / ".env", override=True)
    else:
        load_dotenv(override=True)


_load_dotenv_files()


def get_project_root() -> Path:
    """Return the project root directory.

    Prefers MUSIC_REVIEW_PROJECT_ROOT env var. Falls back to current working
    directory.
    """
    from os import getenv

    if root := getenv("MUSIC_REVIEW_PROJECT_ROOT"):
        return Path(root).resolve()
    return Path.cwd()


# Dashboard overall score: alpha*S_a + beta*R + gamma*coverage_norm.
# Weights: get_recommendation_overall_weights().
RECOMMENDATION_OVERALL_ALPHA: float = 0.5
RECOMMENDATION_OVERALL_BETA: float = 0.25
RECOMMENDATION_OVERALL_GAMMA: float = 0.25
# Plattentests rating default on 0-10 scale when missing (scoring and rating filter).
RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING: float = 7.0
# Filter slider default: 0 = blütenrein (purity), 1 = genre-übergreifend (breadth).
RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER: float = 0.5
# Probeweise: Community-Spektrum-Term wird mit g(S_a) moduliert, g(s)=s/(s+k).
# Bei S_a == k ist g = 0.5. <= 0 schaltet die Kopplung aus (g = 1).
RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION: float = 0.2
# Reference list: first ref weight 1.0, last linear down to this minimum
# (graph + album affinities pipeline).
REFERENCE_POSITION_W_MIN: float = 0.2


def normalize_overall_weights(
    alpha: float,
    beta: float,
    gamma: float,
) -> tuple[float, float, float]:
    """Return normalized (alpha, beta, gamma) with non-negative values summing to 1.

    Used for dashboard sliders (raw relative weights) and config defaults.
    """
    a = max(0.0, float(alpha))
    b = max(0.0, float(beta))
    c = max(0.0, float(gamma))
    total = a + b + c
    if total <= 0.0:
        return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    return (a / total, b / total, c / total)


def get_recommendation_overall_weights() -> tuple[float, float, float]:
    """Return default (alpha, beta, gamma) from config, normalized to sum to 1."""
    return normalize_overall_weights(
        RECOMMENDATION_OVERALL_ALPHA,
        RECOMMENDATION_OVERALL_BETA,
        RECOMMENDATION_OVERALL_GAMMA,
    )


def resolve_data_path(path: str | Path) -> Path:
    """Resolve a data path relative to the project root.

    If the path is absolute, it is returned as-is. Otherwise it is resolved
    against get_project_root(), so data paths work regardless of cwd.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    return get_project_root() / p
