import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Recommendation } from "../types";
import { ApiClientProvider } from "../lib/apiClientContext";
import { FavoritesProvider } from "../lib/favoritesContext";
import { RecommendationCard } from "./RecommendationCard";

const recommendation: Recommendation = {
  rank: 3,
  reviewId: 7,
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
};

function renderCard(
  props: Partial<Parameters<typeof RecommendationCard>[0]> = {},
): ReturnType<typeof render> {
  return render(
    <ApiClientProvider>
      <FavoritesProvider accessToken={null}>
        <RecommendationCard recommendation={recommendation} {...props} />
      </FavoritesProvider>
    </ApiClientProvider>,
  );
}

describe("RecommendationCard", () => {
  it("renders a compact row without a thumbnail by default", () => {
    const { container } = renderCard();

    expect(screen.getByRole("article").className).not.toContain(
      "recommendation-card-with-thumbnail",
    );
    expect(container.querySelector(".recommendation-card-thumbnail")).toBeNull();
  });

  it("renders a thumbnail when an artist image is available", () => {
    renderCard({
      artistImage: {
        artistMbid: "mbid-2",
        artistName: "Known Artist",
        thumbnailUrl: "https://example.com/thumb.jpg",
        attributionText: "Demo",
        license: "CC BY 4.0",
        sourceUrl: "https://example.com/source",
      },
    });

    expect(screen.getByRole("article").className).toContain(
      "recommendation-card-with-thumbnail",
    );
    expect(screen.getByRole("img", { name: "Known Artist" })).toBeTruthy();
  });

  it("drops the thumbnail column when the image fails to load", () => {
    renderCard({
      artistImage: {
        artistMbid: "mbid-2",
        artistName: "Known Artist",
        thumbnailUrl: "https://example.com/thumb.jpg",
        attributionText: "Demo",
        license: "CC BY 4.0",
        sourceUrl: "https://example.com/source",
      },
    });

    screen.getByRole("img", { name: "Known Artist" }).dispatchEvent(
      new Event("error"),
    );

    expect(screen.getByRole("article").className).not.toContain(
      "recommendation-card-with-thumbnail",
    );
    expect(screen.queryByRole("img", { name: "Known Artist" })).toBeNull();
  });
});
