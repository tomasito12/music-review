from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

# Optional: load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from music_review.metadata.musicbrainz_client import fetch_album_tags, fetch_artist_info
from music_review.metadata.genre_regex import GENRE_REGEX

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Genre regex mapping
# ---------------------------------------------------------------------------


_COMPILED_GENRE_REGEX: dict[str, list[re.Pattern]] = {
    genre: [re.compile(pat) for pat in patterns]
    for genre, patterns in GENRE_REGEX.items()
}


def split_raw_tag(raw: str) -> list[str]:
    """Normalize a raw MusicBrainz tag into a single token."""
    text = raw.strip().lower()

    for sep in ["/", ";", ",", "+", "|"]:
        text = text.replace(sep, " ")

    text = text.replace("&", " ")
    text = text.replace(" and ", " ")

    tokens = [t for t in text.split() if t]
    return [" ".join(tokens)] if tokens else []


def is_obvious_non_style(token: str) -> bool:
    """Heuristic: detect tags that are clearly not musical styles."""
    if re.search(r"\b(19|20)\d{2}\b", token):
        return True
    if "wochen" in token:
        return True
    if token in {
        "5+ wochen",
        "1–4 wochen",
        "2000",
        "2001",
        "2002",
        "2003",
        "2004",
        "2005",
        "2006",
        "80s",
        "00s",
    }:
        return True

    if any(
        kw in token
        for kw in [
            "charts",
            "plattentests.de",
            "q recommends",
            "ph_temp_checken",
            "pkg-jewel case",
            "cd extra",
            "drm",
            "self-titled",
            "concept album",
            "hidden track",
            "pregaptrack",
        ]
    ):
        return True

    if token in {
        "english",
        "deutsch",
        "german",
        "american",
        "usa",
        "sweden",
        "swedish",
        "france",
        "french",
        "français",
        "canada",
        "canadian",
        "canadien",
        "iceland",
        "british",
        "britannique",
        "scandinavia",
        "scandinave",
        "scandinavie",
    }:
        return True

    if token in {
        "melancholic",
        "bittersweet",
        "dark",
        "dense",
        "energetic",
        "passionate",
        "anxious",
        "mellow",
        "romantic",
        "aggressive",
        "uplifting",
        "sad",
        "winter",
        "summer",
        "warm",
        "cold",
        "futuristic",
        "noisy",
        "ominous",
        "playful",
        "political",
        "complex",
        "depressive",
        "existential",
        "atmospheric",
        "cryptic",
        "lonely",
        "surreal",
        "sexual",
        "optimistic",
        "serious",
        "triumphant",
        "raw",
        "heavy",
    }:
        return True

    if token in {
        "music",
        "genre",
        "vocal",
        "male vocalist",
        "female vocalist",
        "male vocalists",
        "female vocalists",
        "family",
        "live",
        "soundtrack",
        "non-music",
    }:
        return True

    return False


def match_genres_from_raw_tag(raw_tag: str) -> set[str]:
    """Parse a raw MusicBrainz tag and return a set of canonical genre labels."""
    genres: set[str] = set()

    for token in split_raw_tag(raw_tag):
        if is_obvious_non_style(token):
            continue

        for genre, patterns in _COMPILED_GENRE_REGEX.items():
            if any(pat.search(token) for pat in patterns):
                genres.add(genre)

    return genres


def map_tags_to_genres_regex(raw_tags: Iterable[str]) -> list[str]:
    """Map a list of raw tags to de-duplicated, sorted canonical genre labels."""
    result: set[str] = set()
    for raw in raw_tags:
        result |= match_genres_from_raw_tag(raw)
    return sorted(result)


# ---------------------------------------------------------------------------
# Main metadata types and pipeline
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AlbumMetadata:
    """Metadata for a single plattentests.de review / album."""

    review_id: int
    artist: str
    album: str

    mbid: str | None
    mb_title: str | None

    raw_tags: list[str]
    genres: list[str]

    # artist-level metadata (from MusicBrainz artist)
    artist_mbid: str | None
    artist_country: str | None
    artist_type: str | None
    artist_disambiguation: str | None
    artist_tags: list[str]
    artist_members: list[str]


def iter_reviews(input_path: Path) -> Iterable[tuple[int, str, str]]:
    """Iterate over reviews in a JSONL corpus."""
    with input_path.open("r", encoding="utf-8") as f:
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
                    input_path,
                    exc,
                )
                continue

            try:
                review_id = int(obj["id"])
                artist = str(obj["artist"])
                album = str(obj["album"])
            except KeyError as exc:
                LOGGER.warning(
                    "Missing key %s in line %d of %s; skipping.",
                    exc,
                    line_number,
                    input_path,
                )
                continue

            yield review_id, artist, album


def load_existing_review_ids(output_path: Path) -> set[int]:
    """Load existing metadata_1.jsonl and return set of review_ids already present."""
    if not output_path.exists():
        return set()

    existing_ids: set[int] = set()
    with output_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                LOGGER.warning(
                    "Invalid JSON in metadata file %s line %d: %s",
                    output_path,
                    line_number,
                    exc,
                )
                continue

            review_id = obj.get("review_id")
            if isinstance(review_id, int):
                existing_ids.add(review_id)

    LOGGER.info(
        "Loaded %d existing metadata entries from %s",
        len(existing_ids),
        output_path,
    )
    return existing_ids


def load_existing_metadata_map(output_path: Path) -> dict[int, dict]:
    """Load full existing metadata_1.jsonl into a dict keyed by review_id.

    Used for update mode where we want to rewrite the whole file.
    """
    meta_map: dict[int, dict] = {}
    if not output_path.exists():
        return meta_map

    with output_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                LOGGER.warning(
                    "Invalid JSON in metadata file %s line %d: %s",
                    output_path,
                    line_number,
                    exc,
                )
                continue

            review_id = obj.get("review_id")
            if isinstance(review_id, int):
                meta_map[review_id] = obj

    LOGGER.info(
        "Loaded %d existing metadata entries from %s (for update mode)",
        len(meta_map),
        output_path,
    )
    return meta_map


def fetch_metadata_for_review(
    review_id: int,
    artist: str,
    album: str,
) -> AlbumMetadata:
    """Fetch MusicBrainz metadata for a single review/album."""
    info = fetch_album_tags(artist=artist, album=album)

    if info is None:
        LOGGER.info(
            "No MusicBrainz album info for %s - %s (review_id=%d)",
            artist,
            album,
            review_id,
        )
        raw_tags: list[str] = []
        genres: list[str] = []
        artist_mbid = None
        artist_country = None
        artist_type = None
        artist_disambiguation = None
        artist_tags: list[str] = []
        artist_members: list[str] = []
    else:
        raw_tags = info.tags
        genres = map_tags_to_genres_regex(raw_tags)

        artist_info = fetch_artist_info(info.artist)
        if artist_info is None:
            artist_mbid = None
            artist_country = None
            artist_type = None
            artist_disambiguation = None
            artist_tags = []
            artist_members = []
        else:
            artist_mbid = artist_info.mbid
            artist_country = artist_info.country
            artist_type = artist_info.artist_type
            artist_disambiguation = artist_info.disambiguation
            artist_tags = list(artist_info.tags)
            # this is where Paul / John / Ringo etc. land:
            artist_members = list(artist_info.members)

    return AlbumMetadata(
        review_id=review_id,
        artist=artist,
        album=album,
        mbid=None if info is None else info.mbid,
        mb_title=None if info is None else info.title,
        raw_tags=raw_tags,
        genres=genres,
        artist_mbid=artist_mbid,
        artist_country=artist_country,
        artist_type=artist_type,
        artist_disambiguation=artist_disambiguation,
        artist_tags=artist_tags,
        artist_members=artist_members,
    )


def write_metadata_jsonl(
    metadata: Iterable[AlbumMetadata] | Iterable[dict],
    output_path: Path,
    append: bool = True,
) -> None:
    """Write AlbumMetadata entries (or raw dicts) to a JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and output_path.exists() else "w"

    with output_path.open(mode, encoding="utf-8") as f:
        for entry in metadata:
            if isinstance(entry, AlbumMetadata):
                obj = asdict(entry)
            else:
                obj = entry
            json_line = json.dumps(obj, ensure_ascii=False)
            f.write(json_line + "\n")


def build_metadata(
    input_path: Path,
    output_path: Path,
    overwrite: bool = False,
    update: bool = False,
) -> int:
    """Main batch function: iterate reviews, fetch metadata, write JSONL."""
    if overwrite and update:
        raise ValueError("Options 'overwrite' and 'update' cannot be used together.")

    if overwrite:
        if output_path.exists():
            LOGGER.info("Overwriting existing metadata file %s", output_path)
            output_path.unlink()

        new_entries: list[AlbumMetadata] = []
        total_processed = 0

        for review_id, artist, album in iter_reviews(input_path):
            total_processed += 1
            meta = fetch_metadata_for_review(review_id, artist, album)
            new_entries.append(meta)

            if len(new_entries) >= 50:
                write_metadata_jsonl(new_entries, output_path=output_path, append=True)
                LOGGER.info(
                    "Flushed %d metadata entries to %s",
                    len(new_entries),
                    output_path,
                )
                new_entries.clear()

        if new_entries:
            write_metadata_jsonl(new_entries, output_path=output_path, append=True)
            LOGGER.info(
                "Flushed final %d metadata entries to %s",
                len(new_entries),
                output_path,
            )

        LOGGER.info(
            "Metadata build (overwrite) done. Processed=%d, new=%d",
            total_processed,
            total_processed,
        )
        return total_processed

    if update:
        meta_map = load_existing_metadata_map(output_path)

        total_processed = 0
        updated_or_new = 0

        for review_id, artist, album in iter_reviews(input_path):
            total_processed += 1

            meta = fetch_metadata_for_review(review_id, artist, album)
            meta_map[review_id] = asdict(meta)
            updated_or_new += 1

        all_entries = [meta_map[rid] for rid in sorted(meta_map.keys())]
        write_metadata_jsonl(all_entries, output_path=output_path, append=False)

        LOGGER.info(
            "Metadata build (update) done. Processed=%d, written(updated+new)=%d",
            total_processed,
            updated_or_new,
        )
        return updated_or_new

    existing_ids = load_existing_review_ids(output_path)
    new_entries: list[AlbumMetadata] = []
    total_processed = 0
    total_skipped = 0

    for review_id, artist, album in iter_reviews(input_path):
        total_processed += 1

        if review_id in existing_ids:
            total_skipped += 1
            continue

        meta = fetch_metadata_for_review(review_id, artist, album)
        new_entries.append(meta)

        if len(new_entries) >= 50:
            write_metadata_jsonl(new_entries, output_path=output_path, append=True)
            LOGGER.info(
                "Flushed %d new metadata entries to %s",
                len(new_entries),
                output_path,
            )
            new_entries.clear()

    if new_entries:
        write_metadata_jsonl(new_entries, output_path=output_path, append=True)
        LOGGER.info(
            "Flushed final %d new metadata entries to %s",
            len(new_entries),
            output_path,
        )

    LOGGER.info(
        "Metadata build (append+skip) done. Processed=%d, skipped(existing)=%d, new=%d",
        total_processed,
        total_skipped,
        total_processed - total_skipped,
    )
    return total_processed - total_skipped


def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fetch MusicBrainz metadata for plattentests.de reviews.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/reviews.jsonl"),
        help="Path to review corpus JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/metadata_1.jsonl"),
        help="Path to output metadata JSONL file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing metadata file instead of appending/resuming.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help=(
            "Update existing metadata entries instead of skipping them. "
            "Existing metadata_1.jsonl is read, updated in memory and then fully rewritten."
        ),
    )

    args = parser.parse_args()

    build_metadata(
        input_path=args.input,
        output_path=args.output,
        overwrite=args.overwrite,
        update=args.update,
    )

    # Example: python -m music_review.metadata.fetch_metadata \
    #     --input data/reviews.jsonl \
    #     --output data/metadata.jsonl \
    #     --overwrite

if __name__ == "__main__":
    main()
