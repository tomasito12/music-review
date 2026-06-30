import { useEffect, useRef, useState } from "react";

import { useApiClient } from "./apiClientContext";
import {
  loadArtistImagesBatch,
  type ArtistImageData,
} from "./artistImageApi";
import { artistImageLookupKey } from "./artistImageLookupKey";
import { isVisualTestMode } from "./visualTestMode";

export interface ArtistImageLookup {
  artistMbid?: string;
  artistName: string;
}

export interface UseArtistImagesBatchResult {
  imagesByLookupKey: Map<string, ArtistImageData | null>;
  loading: boolean;
}

function normalizeArtistLookups(
  artists: ArtistImageLookup[],
): Array<{ artistMbid: string; artistName: string }> {
  return artists
    .map((artist) => ({
      artistMbid: artist.artistMbid?.trim() ?? "",
      artistName: artist.artistName,
    }))
    .filter((artist) => artistImageLookupKey(artist).length > 0);
}

/** Return artist lookups that still need an image batch request. */
export function pendingArtistImageLookups(
  artists: ArtistImageLookup[],
  resolved: ReadonlyMap<string, ArtistImageData | null>,
): Array<{ artistMbid: string; artistName: string }> {
  return normalizeArtistLookups(artists).filter((artist) => {
    const lookupKey = artistImageLookupKey(artist);
    return lookupKey.length > 0 && !resolved.has(lookupKey);
  });
}

const ARTIST_IMAGE_BATCH_SIZE = 10;

/** Split artist lookups into API-sized chunks. */
export function chunkArtistImageLookups<T>(lookups: T[]): T[][] {
  const chunks: T[][] = [];
  for (let offset = 0; offset < lookups.length; offset += ARTIST_IMAGE_BATCH_SIZE) {
    chunks.push(lookups.slice(offset, offset + ARTIST_IMAGE_BATCH_SIZE));
  }
  return chunks;
}

/** Mark pending artist lookups as resolved without an image. */
export function markPendingArtistImagesUnavailable(
  pendingLookups: ArtistImageLookup[],
  current: ReadonlyMap<string, ArtistImageData | null>,
): Map<string, ArtistImageData | null> {
  const merged = new Map(current);
  for (const lookup of pendingLookups) {
    const lookupKey = artistImageLookupKey(lookup);
    if (lookupKey.length > 0 && !merged.has(lookupKey)) {
      merged.set(lookupKey, null);
    }
  }
  return merged;
}

/** Loads highlight artist thumbnails in one batch request. */
export function useArtistImagesBatch(
  artists: ArtistImageLookup[],
): UseArtistImagesBatchResult {
  const apiClient = useApiClient();
  const [imagesByLookupKey, setImagesByLookupKey] = useState<
    Map<string, ArtistImageData | null>
  >(new Map());
  const [loading, setLoading] = useState(
    artists.some((artist) => artistImageLookupKey(artist).length > 0),
  );
  const imagesRef = useRef(imagesByLookupKey);
  imagesRef.current = imagesByLookupKey;

  const artistSignature = artists
    .map((artist) => `${artist.artistMbid ?? ""}:${artist.artistName}`)
    .join("|");

  useEffect(() => {
    const lookups = normalizeArtistLookups(artists);

    if (lookups.length === 0) {
      setImagesByLookupKey(new Map());
      setLoading(false);
      return;
    }

    const pendingLookups = pendingArtistImageLookups(artists, imagesRef.current);

    if (pendingLookups.length === 0) {
      setLoading(false);
      return;
    }

    let active = true;
    const deferProgressiveUpdates = isVisualTestMode();
    if (!deferProgressiveUpdates) {
      setLoading(true);
    }

    async function fetchImages(): Promise<void> {
      const mergedResults = new Map<string, ArtistImageData | null>();

      try {
        const client = apiClient();
        for (const chunk of chunkArtistImageLookups(pendingLookups)) {
          const results = await loadArtistImagesBatch(client, chunk);
          if (!active) {
            return;
          }
          for (const [lookupKey, image] of results) {
            mergedResults.set(lookupKey, image);
          }
          if (!deferProgressiveUpdates) {
            setImagesByLookupKey((current) => {
              const merged = new Map(current);
              for (const [lookupKey, image] of mergedResults) {
                merged.set(lookupKey, image);
              }
              return merged;
            });
          }
        }
        if (!active) {
          return;
        }
        setImagesByLookupKey((current) => {
          const merged = new Map(current);
          for (const [lookupKey, image] of mergedResults) {
            merged.set(lookupKey, image);
          }
          return merged;
        });
      } catch {
        if (!active) {
          return;
        }
        setImagesByLookupKey((current) =>
          markPendingArtistImagesUnavailable(pendingLookups, current),
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void fetchImages();

    return () => {
      active = false;
    };
  }, [apiClient, artistSignature]);

  return { imagesByLookupKey, loading };
}
