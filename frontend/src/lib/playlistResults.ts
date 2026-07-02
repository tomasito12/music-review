import { artistImageLookupKey } from "./artistImageLookupKey";
import type { ArtistImageData } from "./artistImageApi";
import type { PlaylistExportItem } from "./playlistExport";

const PLATTENTESTS_REVIEW_URL = "https://www.plattentests.de/rezi.php?show=";
const DEFAULT_MOSAIC_LIMIT = 6;

/** Build the public plattentests.de review URL for one review id. */
export function playlistReviewUrl(reviewId: number): string {
  return `${PLATTENTESTS_REVIEW_URL}${reviewId}`;
}

/** Return unique artist lookups for playlist image batch requests. */
export function uniquePlaylistArtistLookups(
  items: PlaylistExportItem[],
): Array<{ artistName: string }> {
  const seen = new Set<string>();
  const lookups: Array<{ artistName: string }> = [];

  for (const item of items) {
    const artistName = item.artist.trim();
    const key = artistName.toLowerCase();
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    lookups.push({ artistName });
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
    const lookupKey = artistImageLookupKey({ artistName });
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
