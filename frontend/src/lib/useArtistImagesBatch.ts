import { useEffect, useState } from "react";

import { ApiClient } from "./apiClient";
import {
  loadArtistImagesBatch,
  type ArtistImageData,
} from "./artistImageApi";
import { artistImageLookupKey } from "./artistImageLookupKey";

export interface ArtistImageLookup {
  artistMbid?: string;
  artistName: string;
}

export interface UseArtistImagesBatchResult {
  imagesByLookupKey: Map<string, ArtistImageData | null>;
  loading: boolean;
}

/** Loads highlight artist thumbnails in one batch request. */
export function useArtistImagesBatch(
  artists: ArtistImageLookup[],
): UseArtistImagesBatchResult {
  const [imagesByLookupKey, setImagesByLookupKey] = useState<
    Map<string, ArtistImageData | null>
  >(new Map());
  const [loading, setLoading] = useState(
    artists.some((artist) => artistImageLookupKey(artist).length > 0),
  );

  useEffect(() => {
    const lookups = artists
      .map((artist) => ({
        artistMbid: artist.artistMbid?.trim() ?? "",
        artistName: artist.artistName,
      }))
      .filter((artist) => artistImageLookupKey(artist).length > 0);

    if (lookups.length === 0) {
      setImagesByLookupKey(new Map());
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);

    async function fetchImages(): Promise<void> {
      try {
        const results = await loadArtistImagesBatch(new ApiClient(), lookups);
        if (!active) {
          return;
        }
        setImagesByLookupKey(results);
      } catch {
        if (!active) {
          return;
        }
        setImagesByLookupKey(new Map());
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
  }, [artists.map((artist) => `${artist.artistMbid ?? ""}:${artist.artistName}`).join("|")]);

  return { imagesByLookupKey, loading };
}
