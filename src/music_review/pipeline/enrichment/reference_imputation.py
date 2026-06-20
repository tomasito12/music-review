"""Impute missing album genres from plattentests.de references via artist profiles."""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

from music_review.config import resolve_data_path
from music_review.io.jsonl import iter_jsonl_objects

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize artist name for matching (lowercase, strip)."""
    return name.strip().lower() if name else ""


def load_artist_profiles(
    artist_genres_path: Path,
) -> tuple[dict[str, dict], dict[str, str]]:
    """Load artist genre profiles from JSON.

    Returns:
        (profiles_by_key, normalized_name_to_key).
        profiles_by_key: artist_key -> profile (artist_name, genre_counts, main_genres).
        normalized_name_to_key: normalized name -> artist_key (prefers mbid key).
    """
    if not artist_genres_path.exists():
        return {}, {}

    with artist_genres_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    profiles: dict[str, dict] = {}
    name_to_key: dict[str, str] = {}

    for artist_key, profile in raw.items():
        if not isinstance(profile, dict):
            continue
        profiles[artist_key] = profile
        name = profile.get("artist_name")
        if isinstance(name, str):
            norm = _normalize_name(name)
            if norm and (norm not in name_to_key or artist_key.startswith("mbid:")):
                name_to_key[norm] = artist_key

    return profiles, name_to_key


def load_references_by_review_id(reviews_path: Path) -> dict[int, list[str]]:
    """Load review_id -> list of reference strings from reviews JSONL."""
    result: dict[int, list[str]] = {}
    for obj in iter_jsonl_objects(reviews_path, log_errors=False):
        review_id = obj.get("id")
        if not isinstance(review_id, int):
            continue
        refs = obj.get("references")
        if isinstance(refs, list):
            result[review_id] = [str(r) for r in refs if r]
        else:
            result[review_id] = []
    return result


def _main_genres_from_counts(
    genre_counts: Counter[str],
    min_genre_share: float,
    top_k_main_genres: int,
) -> list[str]:
    """Main genres from aggregated counts (same rule as artist_genres)."""
    if not genre_counts:
        return []
    total = sum(genre_counts.values())
    main: list[str] = []
    for genre, count in genre_counts.most_common():
        if total > 0 and count / total >= min_genre_share:
            main.append(genre)
    if not main:
        for genre, _ in genre_counts.most_common(top_k_main_genres):
            main.append(genre)
    return main


def impute_from_references(
    imputed_metadata_path: Path,
    reviews_path: Path,
    artist_genres_path: Path,
    output_path: Path,
    max_references: int = 3,
    min_genre_share: float = 0.15,
    top_k_main_genres: int = 3,
) -> int:
    """Impute missing genres from first N references with artist profiles.

    Reads imputed metadata, reviews (for reference lists), and artist_genres.json.
    For entries with empty genres: resolve references to profiles, aggregate
    genre counts, assign main genres (same rule as same-artist imputation).
    Sets genres_inferred_from_references and reference_artists_used.

    Returns:
        Number of entries imputed from references.
    """
    profiles, name_to_key = load_artist_profiles(artist_genres_path)
    refs_by_id = load_references_by_review_id(reviews_path)

    entries: list[dict] = []
    for obj in iter_jsonl_objects(imputed_metadata_path, log_errors=False):
        entries.append(obj)

    imputed_count = 0
    for obj in entries:
        genres = obj.get("genres")
        has_genres = isinstance(genres, list) and len(genres) > 0

        obj["genres_inferred_from_references"] = False
        if "reference_artists_used" in obj:
            del obj["reference_artists_used"]

        if has_genres:
            continue

        review_id = obj.get("review_id")
        if not isinstance(review_id, int):
            continue

        references = refs_by_id.get(review_id, [])
        if not references:
            continue

        aggregated: Counter[str] = Counter()
        used_refs: list[str] = []

        for ref in references:
            if len(used_refs) >= max_references:
                break
            norm = _normalize_name(ref)
            if not norm:
                continue
            artist_key = name_to_key.get(norm)
            if not artist_key:
                continue
            profile = profiles.get(artist_key)
            if not profile or not profile.get("main_genres"):
                continue
            genre_counts = profile.get("genre_counts")
            if isinstance(genre_counts, dict):
                aggregated.update(genre_counts)
            else:
                for g in profile.get("main_genres") or []:
                    aggregated[g] += 1
            used_refs.append(ref)

        if not aggregated or not used_refs:
            continue

        main_genres = _main_genres_from_counts(
            aggregated,
            min_genre_share=min_genre_share,
            top_k_main_genres=top_k_main_genres,
        )
        if not main_genres:
            continue

        obj["genres"] = main_genres
        obj["genres_inferred_from_references"] = True
        obj["reference_artists_used"] = used_refs
        imputed_count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for obj in entries:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    logger.info(
        "Reference imputation: %d entries imputed from references (total entries: %d).",
        imputed_count,
        len(entries),
    )
    return imputed_count


def main(argv: list[str] | None = None) -> None:
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Impute missing metadata genres from plattentests.de references.",
    )
    parser.add_argument(
        "--imputed-metadata",
        type=Path,
        default=Path("data/metadata_imputed.jsonl"),
        help="Path to imputed metadata JSONL (output of artist_genres).",
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        default=Path("data/reviews.jsonl"),
        help="Path to reviews JSONL.",
    )
    parser.add_argument(
        "--artist-genres",
        type=Path,
        default=Path("data/artist_genres.json"),
        help="Path to artist_genres.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite --imputed-metadata).",
    )
    parser.add_argument(
        "--max-references",
        type=int,
        default=3,
        help="Max number of reference artists to use per review (default: 3).",
    )
    parser.add_argument(
        "--min-genre-share",
        type=float,
        default=0.15,
        help="Min share for a genre to be considered main (default: 0.15).",
    )
    parser.add_argument(
        "--top-k-main-genres",
        type=int,
        default=3,
        help="Fallback: at least top K genres (default: 3).",
    )
    args = parser.parse_args(argv)

    output = args.output if args.output is not None else args.imputed_metadata

    imputed_metadata_path = resolve_data_path(args.imputed_metadata)
    reviews_path = resolve_data_path(args.reviews)
    artist_genres_path = resolve_data_path(args.artist_genres)
    output_path = resolve_data_path(output)

    if not imputed_metadata_path.exists():
        logger.error("Imputed metadata not found: %s", imputed_metadata_path)
        sys.exit(1)

    impute_from_references(
        imputed_metadata_path=imputed_metadata_path,
        reviews_path=reviews_path,
        artist_genres_path=artist_genres_path,
        output_path=output_path,
        max_references=args.max_references,
        min_genre_share=args.min_genre_share,
        top_k_main_genres=args.top_k_main_genres,
    )


if __name__ == "__main__":
    main()
