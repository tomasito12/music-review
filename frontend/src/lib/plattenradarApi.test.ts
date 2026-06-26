import { describe, expect, it, vi } from "vitest";

import { ApiClient } from "./apiClient";
import {
  createTemporaryTasteProfile,
  loadArchiveRecommendations,
  loadTasteCommunities,
} from "./plattenradarApi";

describe("createTemporaryTasteProfile", () => {
  it("creates the balanced profile used for temporary recommendations", () => {
    const profile = createTemporaryTasteProfile(["C001", "C002"]);

    expect(profile.community_weights_raw).toEqual({ C001: 1, C002: 1 });
    expect(profile.filter_settings.score_min).toBe(0.4);
  });
});

describe("loadTasteCommunities", () => {
  it("loads community labels with broad category assignments", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: "C001",
            label: "Indie Rock",
            broad_categories: ["Rock & Alternative"],
          },
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const options = await loadTasteCommunities(
      new ApiClient({ baseUrl: "https://api.example.test" }),
    );

    expect(options).toEqual([
      {
        id: "C001",
        label: "Indie Rock",
        broad_categories: ["Rock & Alternative"],
      },
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/taste-communities",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

describe("loadArchiveRecommendations", () => {
  it("maps the API response into card-ready recommendations", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          total: 1,
          items: [
            {
              rank: 1,
              artist: "Alpha",
              album: "First",
              year: 2024,
              rating: 8,
              overall_score: 0.81,
              labels: "Tiny Label",
              text_excerpt: "A strong first record.",
              url: "https://example.com/review",
              source: "archive",
              matched_tags: [
                { id: "C001", label: "Indie Rock", affinity: 0.9, matched: true },
              ],
            },
          ],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadArchiveRecommendations(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      createTemporaryTasteProfile(["C001"]),
    );

    expect(result.total).toBe(1);
    expect(result.recommendations[0]).toMatchObject({
      artist: "Alpha",
      fitPercent: 81,
      fitLabel: "Sehr passend",
      source: "entdecken",
      tags: [{ label: "Indie Rock", matchesProfile: true, strength: "high" }],
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/recommendations/archive",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
