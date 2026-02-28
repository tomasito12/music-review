from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ArtistGenreProfile:
    """Aggregated genre profile for a single artist."""

    artist_mbid: str | None
    artist_name: str
    total_albums: int
    genre_counts: dict[str, int]
    main_genres: list[str]


# ---------------------------------------------------------------------------
# Helpers: load metadata_1.jsonl
# ---------------------------------------------------------------------------


def iter_metadata(metadata_path: Path) -> Iterable[dict]:
    """Iterate over metadata_1.jsonl entries as dicts."""
    with metadata_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                LOGGER.warning(
                    "Skipping invalid JSON line %d in %s: %s",
                    line_number,
                    metadata_path,
                    exc,
                )
                continue

            yield obj


# ---------------------------------------------------------------------------
# 1) Build artist genre profiles
# ---------------------------------------------------------------------------


def build_artist_genre_profiles(
    metadata_path: Path,
    min_artist_albums: int = 1,
    min_genre_share: float = 0.15,
    top_k_main_genres: int = 3,
) -> dict[str, ArtistGenreProfile]:
    """Build genre profiles per artist from metadata_1.jsonl.

    Strategy:
        - group entries by artist_mbid if available, otherwise by artist name
        - for each artist, count all genres that appear in metadata["genres"]
        - derive main_genres as:
            * all genres with relative frequency >= min_genre_share
              OR
            * at least the top_k_main_genres if available

    Args:
        metadata_path: Path to metadata_1.jsonl.
        min_artist_albums: Minimum number of albums per artist to keep a profile.
        min_genre_share: Minimum relative share for a genre to be considered "main".
        top_k_main_genres: Fallback: ensure at least top K genres are included
                           if there are any genres for the artist.

    Returns:
        Mapping artist_key -> ArtistGenreProfile.
        The artist_key is artist_mbid if present, otherwise "name:<artist_name>".
    """
    # artist_key -> {"name": str, "mbid": str|None, "albums": set[int], "genre_counts": Counter}
    grouped: dict[str, dict] = {}

    for obj in iter_metadata(metadata_path):
        review_id = obj.get("review_id")

        artist_name = obj.get("artist")
        if not isinstance(artist_name, str) or not artist_name.strip():
            # No artist -> cannot aggregate
            continue

        artist_mbid = obj.get("artist_mbid")
        if isinstance(artist_mbid, str) and artist_mbid:
            artist_key = f"mbid:{artist_mbid}"
        else:
            # Fallback: group by name
            artist_key = f"name:{artist_name}"

        genres = obj.get("genres") or []
        if not isinstance(genres, list):
            genres = []

        # Initialize grouping entry
        if artist_key not in grouped:
            grouped[artist_key] = {
                "name": artist_name,
                "mbid": artist_mbid if isinstance(artist_mbid, str) else None,
                "albums": set(),
                "genre_counts": Counter(),
            }

        entry = grouped[artist_key]

        if isinstance(review_id, int):
            entry["albums"].add(review_id)

        entry["genre_counts"].update(str(g) for g in genres)

    profiles: dict[str, ArtistGenreProfile] = {}

    for artist_key, data in grouped.items():
        genre_counts: Counter = data["genre_counts"]
        total_albums = len(data["albums"])

        if total_albums < min_artist_albums:
            continue

        if not genre_counts:
            # No genres at all -> no profile
            continue

        total_genre_assignments = sum(genre_counts.values())

        # Compute main genres by relative share
        main_genres: list[str] = []
        for genre, count in genre_counts.most_common():
            share = count / total_genre_assignments
            if share >= min_genre_share:
                main_genres.append(genre)

        # Fallback: ensure at least top_k_main_genres if possible
        if not main_genres:
            for genre, _count in genre_counts.most_common(top_k_main_genres):
                main_genres.append(genre)

        profile = ArtistGenreProfile(
            artist_mbid=data["mbid"],
            artist_name=data["name"],
            total_albums=total_albums,
            genre_counts=dict(genre_counts),
            main_genres=main_genres,
        )
        profiles[artist_key] = profile

    LOGGER.info(
        "Built %d artist genre profiles from %s",
        len(profiles),
        metadata_path,
    )
    return profiles


def save_artist_genre_profiles(
    profiles: dict[str, ArtistGenreProfile],
    output_path: Path,
) -> None:
    """Save artist genre profiles as JSON (one dict with artist_key -> profile)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    serializable = {
        artist_key: asdict(profile) for artist_key, profile in profiles.items()
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)

    LOGGER.info("Saved %d artist profiles to %s", len(profiles), output_path)


# ---------------------------------------------------------------------------
# 2) Impute missing review genres from artist profiles
# ---------------------------------------------------------------------------


def _build_artist_key_from_metadata_entry(obj: dict) -> str | None:
    """Build artist key (same logic as in build_artist_genre_profiles)."""
    artist_name = obj.get("artist")
    if not isinstance(artist_name, str) or not artist_name.strip():
        return None

    artist_mbid = obj.get("artist_mbid")
    if isinstance(artist_mbid, str) and artist_mbid:
        return f"mbid:{artist_mbid}"

    return f"name:{artist_name}"


def impute_missing_review_genres(
    metadata_path: Path,
    output_path: Path,
    min_artist_albums: int = 1,
    min_genre_share: float = 0.15,
    top_k_main_genres: int = 3,
) -> int:
    """Impute missing metadata['genres'] based on artist genre profiles.

    Reads metadata_1.jsonl, builds artist profiles, then rewrites a new metadata
    file in which entries with empty genres are filled from the corresponding
    artist profile if available.

    The imputed entries get a flag "genres_inferred_from_artist": true.

    Args:
        metadata_path: Input metadata_1.jsonl.
        output_path: Output metadata_1.jsonl with imputed genres.
        min_artist_albums: Minimum album count per artist to build a profile.
        min_genre_share: Threshold for main genre share in artist profile.
        top_k_main_genres: Fallback: at least top K genres per artist.

    Returns:
        Number of reviews for which genres were imputed.
    """
    profiles = build_artist_genre_profiles(
        metadata_path=metadata_path,
        min_artist_albums=min_artist_albums,
        min_genre_share=min_genre_share,
        top_k_main_genres=top_k_main_genres,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    imputed_count = 0
    total_entries = 0

    with metadata_path.open("r", encoding="utf-8") as fin, output_path.open(
        "w",
        encoding="utf-8",
    ) as fout:
        for line_number, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                LOGGER.warning(
                    "Skipping invalid JSON line %d in %s during imputation: %s",
                    line_number,
                    metadata_path,
                    exc,
                )
                continue

            total_entries += 1

            genres = obj.get("genres")
            has_genres = isinstance(genres, list) and len(genres) > 0

            if has_genres:
                obj["genres_inferred_from_artist"] = False
            else:
                artist_key = _build_artist_key_from_metadata_entry(obj)
                profile = profiles.get(artist_key) if artist_key else None

                if profile and profile.main_genres:
                    obj["genres"] = list(profile.main_genres)
                    obj["genres_inferred_from_artist"] = True
                    imputed_count += 1
                else:
                    obj["genres"] = [] if genres is None else genres
                    obj["genres_inferred_from_artist"] = False

            json_line = json.dumps(obj, ensure_ascii=False)
            fout.write(json_line + "\n")

    LOGGER.info(
        "Imputation done. Total entries=%d, genres imputed=%d",
        total_entries,
        imputed_count,
    )
    return imputed_count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build artist genre profiles from metadata.jsonl and optionally "
            "impute missing review genres based on those profiles."
        ),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/metadata_1.jsonl"),
        help="Path to input metadata JSONL.",
    )
    parser.add_argument(
        "--artist-profiles-output",
        type=Path,
        default=None,
        help=(
            "Optional path to write artist genre profiles as JSON "
            "(artist_key -> profile)."
        ),
    )
    parser.add_argument(
        "--imputed-metadata-output",
        type=Path,
        default=None,
        help=(
            "Optional path to write a new metadata JSONL with "
            "imputed genres."
        ),
    )
    parser.add_argument(
        "--min-artist-albums",
        type=int,
        default=1,
        help="Minimum number of albums per artist to keep a profile.",
    )
    parser.add_argument(
        "--min-genre-share",
        type=float,
        default=0.15,
        help="Minimum relative share for a genre to be considered 'main'.",
    )
    parser.add_argument(
        "--top-k-main-genres",
        type=int,
        default=3,
        help="Fallback: ensure at least the top K genres per artist.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = parse_args(argv)

    profiles = build_artist_genre_profiles(
        metadata_path=args.metadata,
        min_artist_albums=args.min_artist_albums,
        min_genre_share=args.min_genre_share,
        top_k_main_genres=args.top_k_main_genres,
    )

    if args.artist_profiles_output is not None:
        save_artist_genre_profiles(profiles, args.artist_profiles_output)

    if args.imputed_metadata_output is not None:
        impute_missing_review_genres(
            metadata_path=args.metadata,
            output_path=args.imputed_metadata_output,
            min_artist_albums=args.min_artist_albums,
            min_genre_share=args.min_genre_share,
            top_k_main_genres=args.top_k_main_genres,
        )


if __name__ == "__main__":
    main()
