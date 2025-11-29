"""
Minimal test script to fetch genre tags for a single album from MusicBrainz.

Usage:
    python test_musicbrainz.py
or:
    MB_VERIFY_TLS=false python test_musicbrainz.py
"""

import os

from music_review.metadata.musicbrainz_client import (
    fetch_album_tags,
    fetch_album_genres,
)

def main() -> None:
    # Pick an example album
    artist = "Rhiannon Giddens"
    album = "Freedom Highway"

    print("MB_VERIFY_TLS:", os.getenv("MB_VERIFY_TLS"))

    print(f"=== Fetching tags for: {artist} – {album} ===\n")

    # Fetch raw tags (unmapped MusicBrainz user tags)
    info = fetch_album_tags(artist, album)

    if info is None:
        print("❌ No information returned (MusicBrainz unreachable or no match).")
        return

    print("MBID:  ", info.mbid)
    print("Title: ", info.title)
    print("Artist:", info.artist)
    print("\nRaw MusicBrainz Tags:")
    print("----------------------")

    if not info.tags:
        print("(no tags found)")
    else:
        for t in info.tags:
            print("  -", t)

    # Fetch mapped canonical internal genres
    print("\nMapped Internal Genres:")
    print("------------------------")
    genres = fetch_album_genres(artist, album)

    if not genres:
        print("(no internal genres mapped)")
    else:
        for g in genres:
            print("  -", g)


if __name__ == "__main__":
    main()
