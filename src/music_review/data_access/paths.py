"""Central data artifact paths resolved against the project root."""

from __future__ import annotations

from pathlib import Path

from music_review.config import resolve_data_path

DATA_REVIEWS = "data/reviews.jsonl"
DATA_METADATA = "data/metadata.jsonl"
DATA_METADATA_IMPUTED = "data/metadata_imputed.jsonl"
DATA_ARTIST_GENRES = "data/artist_genres.json"
DATA_ALBUM_COMMUNITY_AFFINITIES = "data/album_community_affinities.jsonl"
DATA_COMMUNITY_MEMBERSHIPS = "data/community_memberships.jsonl"
DATA_COMMUNITIES_RES_10 = "data/communities_res_10.json"
DATA_COMMUNITY_GENRE_LABELS_RES_10 = "data/community_genre_labels_res_10.json"
DATA_COMMUNITY_BROAD_CATEGORIES_RES_10 = "data/community_broad_categories_res_10.json"
DATA_PIPELINE_HEALTH_REPORT = "data/pipeline_health_report.json"
DATA_PRODUCTION_UPDATE_LOCK = "data/.production_update.lock"
DATA_ARTIST_REFERENCE_GRAPH = "data/artist_reference_graph.graphml"
DATA_COMMUNITY_RESOLUTION_SCAN = "data/community_resolution_scan.json"
DATA_DIR = "data"


def data_dir() -> Path:
    """Resolved path to the project data directory."""
    return resolve_data_path(DATA_DIR)


def reviews_path() -> Path:
    """Resolved path to the scraped reviews JSONL corpus."""
    return resolve_data_path(DATA_REVIEWS)


def metadata_path() -> Path:
    """Resolved path to MusicBrainz metadata JSONL."""
    return resolve_data_path(DATA_METADATA)


def metadata_imputed_path() -> Path:
    """Resolved path to genre-imputed metadata JSONL."""
    return resolve_data_path(DATA_METADATA_IMPUTED)


def artist_genres_path() -> Path:
    """Resolved path to artist genre profiles JSON."""
    return resolve_data_path(DATA_ARTIST_GENRES)


def album_community_affinities_path() -> Path:
    """Resolved path to album-to-community affinity JSONL."""
    return resolve_data_path(DATA_ALBUM_COMMUNITY_AFFINITIES)


def community_memberships_path() -> Path:
    """Resolved path to artist community memberships JSONL."""
    return resolve_data_path(DATA_COMMUNITY_MEMBERSHIPS)


def communities_res_10_path() -> Path:
    """Resolved path to Louvain communities export (resolution 10)."""
    return resolve_data_path(DATA_COMMUNITIES_RES_10)


def community_genre_labels_res_10_path() -> Path:
    """Resolved path to LLM genre labels for communities (resolution 10)."""
    return resolve_data_path(DATA_COMMUNITY_GENRE_LABELS_RES_10)


def community_broad_categories_res_10_path() -> Path:
    """Resolved path to broad category mappings (resolution 10)."""
    return resolve_data_path(DATA_COMMUNITY_BROAD_CATEGORIES_RES_10)


def pipeline_health_report_path() -> Path:
    """Resolved path to the data-quality health report JSON."""
    return resolve_data_path(DATA_PIPELINE_HEALTH_REPORT)


def production_update_lock_path() -> Path:
    """Resolved path to the production update lock file."""
    return resolve_data_path(DATA_PRODUCTION_UPDATE_LOCK)


def artist_reference_graph_path() -> Path:
    """Resolved path to the artist reference graph GraphML export."""
    return resolve_data_path(DATA_ARTIST_REFERENCE_GRAPH)


def community_resolution_scan_path() -> Path:
    """Resolved path to the Louvain resolution scan JSON."""
    return resolve_data_path(DATA_COMMUNITY_RESOLUTION_SCAN)
