import { artistDedupeKeys, artistImageLookupKey } from "./artistImageLookupKey";
import type { ArtistImageData } from "./artistImageApi";
import type { PlaylistExportItem } from "./playlistExport";
import type { ArtistImageLookup } from "./useArtistImagesBatch";

const PLATTENTESTS_REVIEW_URL = "https://www.plattentests.de/rezi.php?show=";
const DEFAULT_MOSAIC_LIMIT = 6;

/** Build the public plattentests.de review URL for one review id. */
export function playlistReviewUrl(reviewId: number): string {
  return `${PLATTENTESTS_REVIEW_URL}${reviewId}`;
}

/** Return unique artist lookups for playlist image batch requests. */
export function uniquePlaylistArtistLookups(
  items: PlaylistExportItem[],
): ArtistImageLookup[] {
  const seen = new Set<string>();
  const lookups: ArtistImageLookup[] = [];

  for (const item of items) {
    const artistName = item.artist.trim();
    const artistMbid = item.artist_mbid?.trim() ?? undefined;
    const keys = artistDedupeKeys({ artistMbid, artistName });
    if (keys.length === 0 || keys.some((key) => seen.has(key))) {
      continue;
    }
    for (const key of keys) {
      seen.add(key);
    }
    lookups.push({ artistName, artistMbid });
  }

  return lookups;
}

/** Pick artist image lookups for the optional playlist mosaic header. */
export function selectPlaylistMosaicLookups(
  items: PlaylistExportItem[],
  imagesByLookupKey: ReadonlyMap<string, ArtistImageData | null>,
  limit = DEFAULT_MOSAIC_LIMIT,
): Array<{ artistName: string; lookupKey: string }> {
  const selected: Array<{ artistName: string; lookupKey: string }> = [];
  const seen = new Set<string>();

  for (const item of items) {
    const artistName = item.artist.trim();
    const artistMbid = item.artist_mbid?.trim() ?? undefined;
    const lookupKey = artistImageLookupKey({ artistMbid, artistName });
    if (!lookupKey || seen.has(lookupKey)) {
      continue;
    }
    seen.add(lookupKey);

    const image = imagesByLookupKey.get(lookupKey);
    if (image === null || image === undefined) {
      continue;
    }

    selected.push({ artistName, lookupKey });
    if (selected.length >= limit) {
      break;
    }
  }

  return selected;
}
