import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Recommendation } from "../types";
import { AktuellRankingList } from "./AktuellRankingList";

vi.mock("../lib/useArtistImagesBatch", () => ({
  useArtistImagesBatch: () => ({
    imagesByLookupKey: new Map([
      [
        "name:known artist",
        {
          artistMbid: "mbid-2",
          artistName: "Known Artist",
          thumbnailUrl: "https://example.com/thumb.jpg",
          attributionText: "Demo",
          license: "CC BY 4.0",
          sourceUrl: "https://example.com/source",
        },
      ],
    ]),
    imagesSettled: true,
    loading: false,
  }),
}));

const recommendations: Recommendation[] = [
  {
    rank: 4,
    reviewId: 11,
    artist: "Known Artist",
    album: "Recent Album",
    year: 2024,
    rating: 7,
    score: 0.66,
    styleFit: 0.66,
    albumStyleBreadth: 0.35,
    fitLabel: "Passend",
    fitPercent: 66,
    excerpt: "Kurzer Auszug.",
    reviewUrl: "https://example.com/review",
    tags: [],
    source: "aktuell",
  },
  {
    rank: 5,
    reviewId: 12,
    artist: "No Photo Act",
    album: "Silent Debut",
    year: 2025,
    rating: 8,
    score: 0.6,
    styleFit: 0.6,
    albumStyleBreadth: 0.3,
    fitLabel: "Passend",
    fitPercent: 60,
    excerpt: "Noch ohne Foto.",
    reviewUrl: "https://example.com/review-2",
    tags: [],
    source: "aktuell",
  },
];

describe("AktuellRankingList", () => {
  it("renders list rows and attaches thumbnails only when images are available", () => {
    render(<AktuellRankingList recommendations={recommendations} />);

    expect(screen.getByRole("heading", { name: "Weitere neue Rezensionen" })).toBeTruthy();
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getByRole("img", { name: "Known Artist" })).toBeTruthy();
    expect(screen.queryByRole("img", { name: "No Photo Act" })).toBeNull();
  });
});
