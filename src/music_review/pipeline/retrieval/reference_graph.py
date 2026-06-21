"""Artist reference graph and community analysis utilities (facade)."""

from __future__ import annotations

from music_review.data_access.communities import load_artist_communities
from music_review.domain.reference_masses import (
    normalize_reference_artist_name,
    position_weight,
    reference_community_position_masses,
)
from music_review.pipeline.retrieval.album_affinities import compute_album_affinities
from music_review.pipeline.retrieval.communities_export import (
    export_communities_incremental,
    export_fixed_clusterings,
    merge_memberships_incremental,
    previous_memberships_usable,
    resolution_to_res_key,
)
from music_review.pipeline.retrieval.graph_build import (
    attribute_purity_summary,
    build_artist_attribute_profiles,
    build_artist_graph,
    load_graph,
    save_graph,
    to_undirected_weighted,
)
from music_review.pipeline.retrieval.graph_communities import (
    centroid_distance_between_communities,
    community_centroid,
    community_distance_matrix,
    detect_communities,
    distance_between_communities,
)

__all__ = [
    "attribute_purity_summary",
    "build_artist_attribute_profiles",
    "build_artist_graph",
    "centroid_distance_between_communities",
    "community_centroid",
    "community_distance_matrix",
    "compute_album_affinities",
    "detect_communities",
    "distance_between_communities",
    "export_communities_incremental",
    "export_fixed_clusterings",
    "load_artist_communities",
    "load_graph",
    "merge_memberships_incremental",
    "normalize_reference_artist_name",
    "position_weight",
    "previous_memberships_usable",
    "reference_community_position_masses",
    "resolution_to_res_key",
    "save_graph",
    "to_undirected_weighted",
]

if __name__ == "__main__":
    from music_review.pipeline.retrieval.reference_graph_cli import main

    raise SystemExit(main())
