import { ApiClient } from "./apiClient";
import { artistImageLookupKey } from "./artistImageLookupKey";

export interface ArtistImageData {
  artistMbid: string;
  artistName: string;
  thumbnailUrl: string;
  attributionText: string;
  license: string;
  sourceUrl: string;
}

export interface ArtistImageLookup {
  artistMbid?: string;
  artistName?: string;
}

interface ApiArtistImageResponse {
  artist_mbid: string;
  artist_name: string;
  thumbnail_url: string;
  attribution_text: string;
  license: string;
  source_url: string;
}

interface ApiArtistImageBatchResult {
  artist_mbid: string;
  image: ApiArtistImageResponse | null;
}

interface ApiArtistImagesBatchResponse {
  items: ApiArtistImageBatchResult[];
}

const artistImageCache = new Map<string, ArtistImageData | null>();

/** Clears the in-memory artist image cache (for tests). */
export function clearArtistImageCache(): void {
  artistImageCache.clear();
}

/** Resolve API-relative thumbnail URLs against the Plattenradar API base URL. */
export function resolveArtistImageUrl(client: ApiClient, thumbnailUrl: string): string {
  if (/^(https?:|data:)/i.test(thumbnailUrl)) {
    return thumbnailUrl;
  }
  const base = client.getBaseUrl().replace(/\/$/, "");
  const path = thumbnailUrl.startsWith("/") ? thumbnailUrl : `/${thumbnailUrl}`;
  return `${base}${path}`;
}

/** Loads licensed artist thumbnail metadata for one MusicBrainz artist ID. */
export async function loadArtistImage(
  client: ApiClient,
  artistMbid: string,
  artistName?: string,
): Promise<ArtistImageData | null> {
  const lookupKey = artistImageLookupKey({ artistMbid, artistName });
  const results = await loadArtistImagesBatch(client, [
    { artistMbid, artistName },
  ]);
  return results.get(lookupKey) ?? null;
}

/** Loads licensed thumbnails for multiple highlight artists in one request. */
export async function loadArtistImagesBatch(
  client: ApiClient,
  artists: ArtistImageLookup[],
): Promise<Map<string, ArtistImageData | null>> {
  const normalized = artists
    .map((artist) => ({
      artistMbid: artist.artistMbid?.trim() ?? "",
      artistName: artist.artistName,
      lookupKey: artistImageLookupKey(artist),
    }))
    .filter((artist) => artist.lookupKey.length > 0);

  const pending = normalized.filter(
    (artist) => !artistImageCache.has(artist.lookupKey),
  );

  if (pending.length > 0) {
    const response = await client.post<ApiArtistImagesBatchResponse>(
      "/v1/artists/images",
      {
        artists: pending.map((artist) => ({
          artist_mbid: artist.artistMbid,
          artist_name: artist.artistName ?? null,
        })),
      },
    );
    for (const item of response.items) {
      const mapped =
        item.image === null
          ? null
          : toArtistImageData(item.image, client);
      artistImageCache.set(item.artist_mbid, mapped);
    }
    for (const artist of pending) {
      if (!artistImageCache.has(artist.lookupKey)) {
        artistImageCache.set(artist.lookupKey, null);
      }
    }
  }

  const results = new Map<string, ArtistImageData | null>();
  for (const artist of normalized) {
    results.set(artist.lookupKey, artistImageCache.get(artist.lookupKey) ?? null);
  }
  return results;
}

function toArtistImageData(
  response: ApiArtistImageResponse,
  client: ApiClient,
): ArtistImageData {
  return {
    artistMbid: response.artist_mbid,
    artistName: response.artist_name,
    thumbnailUrl: resolveArtistImageUrl(client, response.thumbnail_url),
    attributionText: response.attribution_text,
    license: response.license,
    sourceUrl: response.source_url,
  };
}
