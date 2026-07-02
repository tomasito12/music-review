import { describe, expect, it, vi } from "vitest";

import { ApiClient } from "./apiClient";
import {
  createTemporaryTasteProfile,
  DEFAULT_BALANCED_FILTER_SETTINGS,
  exportPlaylist,
  filterSettingsFromPreset,
  loadArchiveRecommendations,
  loginAccount,
  loadNewReviewRecommendations,
  registerAccount,
  temporaryProfileToApi,
  loadTasteCommunities,
  loadTasteCommunityMap,
  loadTastePresets,
} from "./plattenradarApi";

const exploratoryPreset = {
  id: "exploratory",
  label: "Entdeckerisch",
  subtitle: "Mehr angrenzende Stile",
  description: "Öffnet die Sortierung für angrenzende Fundstücke.",
  icon: "compass",
  filter_settings: {
    ...DEFAULT_BALANCED_FILTER_SETTINGS,
    overall_weight_alpha: 0.3,
    overall_weight_beta: 0.3,
    overall_weight_gamma: 0.4,
  },
};

describe("createTemporaryTasteProfile", () => {
  it("creates the balanced profile used for temporary recommendations", () => {
    const profile = createTemporaryTasteProfile(["C001", "C002"]);

    expect(profile.community_weights_raw).toEqual({ C001: 0.5, C002: 0.5 });
    expect(profile.filter_settings.score_min).toBe(0.4);
  });

  it("applies custom filter settings from a preset", () => {
    const profile = createTemporaryTasteProfile(
      ["C001"],
      filterSettingsFromPreset(exploratoryPreset),
    );

    expect(profile.filter_settings.score_min).toBe(0.4);
    expect(profile.filter_settings.overall_weight_alpha).toBe(0.3);
    expect(profile.filter_settings.overall_weight_gamma).toBe(0.4);
  });

  it("maps temporary profiles into API payloads", () => {
    const profile = createTemporaryTasteProfile(["C001", "C002"]);
    expect(temporaryProfileToApi(profile)).toEqual({
      name: "Temporäres Musikprofil",
      selected_communities: ["C001", "C002"],
      community_weights_raw: { C001: 0.5, C002: 0.5 },
      filter_settings: profile.filter_settings,
    });
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
            example_artists: ["Radiohead", "The National", "Arcade Fire"],
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
        example_artists: ["Radiohead", "The National", "Arcade Fire"],
      },
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/taste-communities",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

describe("loadTasteCommunityMap", () => {
  it("loads graph layout nodes from the API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          nodes: [
            {
              id: "C001",
              x: 0.2,
              y: 0.4,
              size: 12,
              neighbors: ["C002"],
            },
          ],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const map = await loadTasteCommunityMap(
      new ApiClient({ baseUrl: "https://api.example.test" }),
    );

    expect(map.nodes[0]?.id).toBe("C001");
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/taste-communities/map",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

describe("loadTastePresets", () => {
  it("loads preset definitions from the API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([exploratoryPreset]), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const presets = await loadTastePresets(
      new ApiClient({ baseUrl: "https://api.example.test" }),
    );

    expect(presets[0]?.id).toBe("exploratory");
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/presets",
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
              artist_mbid: "mbid-alpha",
              year: 2024,
              release_date: "2024-05-01",
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
      artistMbid: "mbid-alpha",
      fitPercent: 81,
      fitLabel: "Sehr passend",
      source: "entdecken",
      tags: [{ label: "Indie Rock", matchesProfile: true, affinity: 0.9 }],
    });
  });

  it("requests a specific archive page via limit and offset", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ total: 100, items: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await loadArchiveRecommendations(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      createTemporaryTasteProfile(["C001"]),
      { limit: 20, offset: 40 },
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/recommendations/archive",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          profile: createTemporaryTasteProfile(["C001"]),
          limit: 20,
          offset: 40,
        }),
      }),
    );
  });
});

describe("registerAccount", () => {
  it("registers a user with an optional taste profile", async () => {
    const profile = createTemporaryTasteProfile(["C001"]);
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "token-abc",
          token_type: "bearer",
          user: { slug: "alice", email: "alice@example.com" },
        }),
        { status: 201 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await registerAccount(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      "alice@example.com",
      "secret123",
      profile,
    );

    expect(result.token).toBe("token-abc");
    expect(result.user.email).toBe("alice@example.com");
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/auth/register",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "alice@example.com",
          password: "secret123",
          profile: temporaryProfileToApi(profile),
        }),
      }),
    );
  });
});

describe("loginAccount", () => {
  it("logs in and returns a bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "token-xyz",
          token_type: "bearer",
          user: { slug: "alice", email: "alice@example.com" },
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loginAccount(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      "alice@example.com",
      "secret123",
    );

    expect(result.token).toBe("token-xyz");
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/v1/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("loadNewReviewRecommendations", () => {
  it("maps newest-review API responses to aktuell cards", async () => {
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
              release_date: "2024-05-01",
              rating: 8,
              overall_score: 0.81,
              labels: "Tiny Label",
              text_excerpt: "A strong first record.",
              url: "https://example.com/review",
              source: "new_reviews",
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

    const result = await loadNewReviewRecommendations(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      createTemporaryTasteProfile(["C001"]),
      { updateRounds: 4, limit: 20, offset: 0 },
    );

    expect(result.total).toBe(1);
    expect(result.recommendations[0]?.source).toBe("aktuell");
    const requestBody = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(requestBody).toMatchObject({
      update_rounds: 4,
      limit: 20,
      offset: 0,
      profile: temporaryProfileToApi(createTemporaryTasteProfile(["C001"])),
    });
  });

  it("defaults update_rounds to 1 when omitted", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ total: 0, items: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await loadNewReviewRecommendations(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      createTemporaryTasteProfile(["C001"]),
      { limit: 20, offset: 0 },
    );

    const requestBody = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(requestBody.update_rounds).toBe(1);
  });
});

describe("exportPlaylist", () => {
  it("posts playlist export settings to the API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          source: "archive",
          name: "Test",
          format: "csv",
          filename: "test.csv",
          content_type: "text/csv",
          content: "Track name,Artist name,Playlist name\nTrack,Artist,Test",
          items: [],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const profile = createTemporaryTasteProfile(["C001"]);
    const result = await exportPlaylist(new ApiClient({ baseUrl: "https://api.example.test" }), {
      source: "entdecken",
      profile,
      name: "Test",
      targetCount: 20,
      newestTasteFocus: 0.25,
      archiveDepth: 0.35,
      archiveAlbumLimit: 200,
      updateRounds: "4",
      format: "csv",
    });

    expect(result.filename).toBe("test.csv");
    const requestBody = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(requestBody).toMatchObject({
      source: "archive",
      playlist_name: "Test",
      target_count: 20,
      format: "csv",
    });
  });
});
