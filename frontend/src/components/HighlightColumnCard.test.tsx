import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Recommendation } from "../types";
import type { ArtistImageData } from "../lib/artistImageApi";
import { ApiClientProvider } from "../lib/apiClientContext";
import { FavoritesProvider } from "../lib/favoritesContext";
import { HighlightColumnCard } from "./HighlightColumnCard";

const recommendation: Recommendation = {
  rank: 2,
  reviewId: 42,
  artist: "Newcomer Band",
  album: "Debut",
  year: 2025,
  rating: 8,
  score: 0.81,
  styleFit: 0.81,
  albumStyleBreadth: 0.4,
  fitLabel: "Passend",
  fitPercent: 81,
  excerpt: "Ein starker Einstieg.",
  reviewUrl: "https://example.com/review",
  tags: [{ label: "Indie", affinity: 0.7, matchesProfile: true }],
  source: "aktuell",
};

function renderHighlight(
  overrides: {
    image?: ArtistImageData | null;
    imageLoading?: boolean;
  } = {},
): ReturnType<typeof render> {
  return render(
    <ApiClientProvider>
      <FavoritesProvider accessToken={null}>
        <HighlightColumnCard
          highlight={{
            label: "Beste Passung",
            description: "Das Album mit dem höchsten Gesamtscore.",
            recommendation,
          }}
          image={overrides.image ?? null}
          imageLoading={overrides.imageLoading ?? false}
          imageOnStart
          showSaveAction={false}
          useAccentPanelWithoutPhoto
        />
      </FavoritesProvider>
    </ApiClientProvider>,
  );
}

describe("HighlightColumnCard", () => {
  it("keeps the two-column layout with an accent panel when no photo is available", () => {
    const { container } = renderHighlight();

    expect(container.querySelector(".highlight-tile-accent-panel")).toBeTruthy();
    expect(container.querySelector(".highlight-tile-media")).toBeTruthy();
    expect(screen.getByText("Beste Passung")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Newcomer Band/i })).toBeTruthy();
    expect(container.querySelector(".highlight-tile-initials")).toBeNull();
    expect(container.querySelector(".highlight-tile-photo")).toBeNull();
  });

  it("renders a photo tile when an artist image is available", () => {
    const { container } = renderHighlight({
      image: {
        artistMbid: "mbid-1",
        artistName: "Newcomer Band",
        thumbnailUrl: "https://example.com/photo.jpg",
        attributionText: "Demo",
        license: "CC BY 4.0",
        sourceUrl: "https://example.com/source",
      },
    });

    expect(container.querySelector(".highlight-tile-photo")).toBeTruthy();
    expect(container.querySelector(".highlight-tile-accent-panel")).toBeNull();
  });
});
