import { describe, expect, it } from "vitest";

import type { ArtistImageData } from "./artistImageApi";
import type { PlaylistExportItem } from "./playlistExport";
import {
  playlistReviewUrl,
  selectPlaylistMosaicLookups,
  uniquePlaylistArtistLookups,
} from "./playlistResults";

const sampleItem = (
  reviewId: number,
  artist: string,
  album: string,
  trackTitle: string,
): PlaylistExportItem => ({
  review_id: reviewId,
  artist,
  album,
  track_title: trackTitle,
  source_kind: "highlight",
  score_weight: 1,
  raw_score: 0.8,
});

describe("playlistReviewUrl", () => {
  it("builds a plattentests review link", () => {
    expect(playlistReviewUrl(17491)).toBe(
      "https://www.plattentests.de/rezi.php?show=17491",
    );
  });
});

describe("uniquePlaylistArtistLookups", () => {
  it("deduplicates artists while preserving order", () => {
    const lookups = uniquePlaylistArtistLookups([
      sampleItem(1, "Alpha", "Album A", "Song 1"),
      sampleItem(2, "Beta", "Album B", "Song 2"),
      sampleItem(3, "Alpha", "Album C", "Song 3"),
    ]);

    expect(lookups).toEqual([{ artistName: "Alpha" }, { artistName: "Beta" }]);
  });
});

describe("selectPlaylistMosaicLookups", () => {
  it("returns only artists with resolved images", () => {
    const image: ArtistImageData = {
      artistMbid: "",
      artistName: "Alpha",
      thumbnailUrl: "https://example.com/alpha.jpg",
      attributionText: "Demo",
      license: "CC BY 4.0",
      sourceUrl: "https://example.com/source",
    };
    const images = new Map<string, ArtistImageData | null>([
      ["name:alpha", image],
      ["name:beta", null],
    ]);

    const tiles = selectPlaylistMosaicLookups(
      [
        sampleItem(1, "Alpha", "Album A", "Song 1"),
        sampleItem(2, "Beta", "Album B", "Song 2"),
        sampleItem(3, "Gamma", "Album C", "Song 3"),
      ],
      images,
      2,
    );

    expect(tiles).toEqual([{ artistName: "Alpha", lookupKey: "name:alpha" }]);
  });
});
