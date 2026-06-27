import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient } from "./apiClient";
import {
  clearArtistImageCache,
  loadArtistImage,
  loadArtistImagesBatch,
  resolveArtistImageUrl,
} from "./artistImageApi";

describe("resolveArtistImageUrl", () => {
  it("prefixes API-relative thumbnail paths with the client base URL", () => {
    const client = new ApiClient({ baseUrl: "http://127.0.0.1:8000" });

    expect(resolveArtistImageUrl(client, "/v1/artists/mbid-1/image/file")).toBe(
      "http://127.0.0.1:8000/v1/artists/mbid-1/image/file",
    );
    expect(resolveArtistImageUrl(client, "https://example.com/thumb.jpg")).toBe(
      "https://example.com/thumb.jpg",
    );
  });
});

describe("loadArtistImagesBatch", () => {
  afterEach(() => {
    clearArtistImageCache();
    vi.unstubAllGlobals();
  });

  it("returns null for an empty MBID without calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadArtistImagesBatch(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      [{ artistMbid: "  " }],
    );

    expect(result.get("")).toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("maps a successful batch response and caches results", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              artist_mbid: "mbid-1",
              image: {
                artist_mbid: "mbid-1",
                artist_name: "Radiohead",
                thumbnail_url: "/v1/artists/mbid-1/image/file",
                attribution_text:
                  "Radiohead by User, CC BY 4.0 via Wikimedia Commons",
                license: "CC BY 4.0",
                source_url: "https://commons.wikimedia.org/wiki/File:Radiohead.jpg",
              },
            },
            {
              artist_mbid: "mbid-2",
              image: null,
            },
          ],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = new ApiClient({ baseUrl: "https://api.example.test" });

    const first = await loadArtistImagesBatch(client, [
      { artistMbid: "mbid-1", artistName: "Radiohead" },
      { artistMbid: "mbid-2", artistName: "Missing" },
    ]);
    const second = await loadArtistImagesBatch(client, [
      { artistMbid: "mbid-1", artistName: "Radiohead" },
      { artistMbid: "mbid-2", artistName: "Missing" },
    ]);

    expect(first.get("mbid-1")?.thumbnailUrl).toBe(
      "https://api.example.test/v1/artists/mbid-1/image/file",
    );
    expect(first.get("mbid-2")).toBeNull();
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(second.get("mbid-1")?.artistName).toBe("Radiohead");
  });
});

describe("loadArtistImage", () => {
  afterEach(() => {
    clearArtistImageCache();
    vi.unstubAllGlobals();
  });

  it("delegates single lookups to the batch endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              artist_mbid: "mbid-1",
              image: {
                artist_mbid: "mbid-1",
                artist_name: "Alpha",
                thumbnail_url: "https://example.com/alpha.jpg",
                attribution_text: "Alpha by User, CC BY 4.0 via Wikimedia Commons",
                license: "CC BY 4.0",
                source_url: "https://commons.wikimedia.org/wiki/File:Alpha.jpg",
              },
            },
          ],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadArtistImage(
      new ApiClient({ baseUrl: "https://api.example.test" }),
      "mbid-1",
      "Alpha",
    );

    expect(result?.thumbnailUrl).toBe("https://example.com/alpha.jpg");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/v1/artists/images");
  });
});
