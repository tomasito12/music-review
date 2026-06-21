"""Framework-agnostic loaders for pipeline and dashboard data artifacts."""

from music_review.data_access.affinities import (
    affinities_by_review_id,
    affinities_list,
    load_affinities_raw,
    top_communities_per_review,
)
from music_review.data_access.artist_genres import load_artist_genre_profiles
from music_review.data_access.communities import (
    load_artist_communities,
    load_broad_categories_res_10,
    load_communities_res_10,
    load_communities_res_file,
    load_existing_genre_labels,
    load_genre_labels_res_10,
)
from music_review.data_access.metadata import load_metadata_map
from music_review.data_access.paths import (
    album_community_affinities_path,
    artist_genres_path,
    artist_reference_graph_path,
    communities_res_10_path,
    community_broad_categories_res_10_path,
    community_genre_labels_res_10_path,
    community_memberships_path,
    community_resolution_scan_path,
    data_dir,
    metadata_imputed_path,
    metadata_path,
    pipeline_health_report_path,
    reviews_path,
)
from music_review.data_access.reviews import (
    load_reviews,
    max_release_year_in_jsonl,
    min_release_year_in_jsonl,
    plattenlabel_album_count_buckets_from_reviews_jsonl,
    review_raw_release_year,
    unique_plattenlabels_from_reviews_jsonl,
)

__all__ = [
    "affinities_by_review_id",
    "affinities_list",
    "album_community_affinities_path",
    "artist_genres_path",
    "artist_reference_graph_path",
    "communities_res_10_path",
    "community_broad_categories_res_10_path",
    "community_genre_labels_res_10_path",
    "community_memberships_path",
    "community_resolution_scan_path",
    "data_dir",
    "load_affinities_raw",
    "load_artist_communities",
    "load_artist_genre_profiles",
    "load_broad_categories_res_10",
    "load_communities_res_10",
    "load_communities_res_file",
    "load_existing_genre_labels",
    "load_genre_labels_res_10",
    "load_metadata_map",
    "load_reviews",
    "max_release_year_in_jsonl",
    "metadata_imputed_path",
    "metadata_path",
    "min_release_year_in_jsonl",
    "pipeline_health_report_path",
    "plattenlabel_album_count_buckets_from_reviews_jsonl",
    "review_raw_release_year",
    "reviews_path",
    "top_communities_per_review",
    "unique_plattenlabels_from_reviews_jsonl",
]
