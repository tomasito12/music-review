import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PlaylistExportItem } from "../lib/playlistExport";
import { PlaylistTrackList } from "./playlist/PlaylistTrackList";

vi.mock("../lib/useArtistImagesBatch", () => ({
  useArtistImagesBatch: () => ({
    imagesByLookupKey: new Map([
      [
        "known-mbid",
        {
          artistMbid: "known-mbid",
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

const items: PlaylistExportItem[] = [
  {
    review_id: 42,
    artist: "Known Artist",
    artist_mbid: "known-mbid",
    album: "Recent Album",
    track_title: "Opening Track",
    source_kind: "highlight",
    score_weight: 1,
    raw_score: 0.8,
  },
  {
    review_id: 43,
    artist: "No Photo Act",
    album: "Silent Debut",
    track_title: "Hidden Gem",
    source_kind: "fallback",
    score_weight: 0.7,
    raw_score: 0.6,
  },
];

describe("PlaylistTrackList", () => {
  it("renders hybrid track rows with review links and initials fallback", () => {
    render(<PlaylistTrackList items={items} />);

    expect(screen.getByRole("link", { name: "Opening Track" })).toHaveAttribute(
      "href",
      "https://www.plattentests.de/rezi.php?show=42",
    );
    expect(screen.getByText("Known Artist · Recent Album")).toBeInTheDocument();
    expect(screen.getByAltText("Known Artist")).toBeInTheDocument();
    expect(screen.getByText("NP")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Hidden Gem" })).toHaveAttribute(
      "href",
      "https://www.plattentests.de/rezi.php?show=43",
    );
    expect(screen.getAllByRole("link", { name: "Zur Rezension" })).toHaveLength(2);
  });
});
