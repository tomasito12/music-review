import { useEffect, useState } from "react";

import { ApiClient } from "./apiClient";
import {
  loadArtistImagesBatch,
  type ArtistImageData,
} from "./artistImageApi";

export interface ArtistImageLookup {
  artistMbid?: string;
  artistName: string;
}

export interface UseArtistImagesBatchResult {
  imagesByMbid: Map<string, ArtistImageData | null>;
  loading: boolean;
}

/** Loads highlight artist thumbnails in one batch request. */
export function useArtistImagesBatch(
  artists: ArtistImageLookup[],
): UseArtistImagesBatchResult {
  const [imagesByMbid, setImagesByMbid] = useState<
    Map<string, ArtistImageData | null>
  >(new Map());
  const [loading, setLoading] = useState(
    artists.some((artist) => Boolean(artist.artistMbid?.trim())),
  );

  useEffect(() => {
    const lookups = artists
      .map((artist) => ({
        artistMbid: artist.artistMbid?.trim() ?? "",
        artistName: artist.artistName,
      }))
      .filter((artist) => artist.artistMbid.length > 0);

    if (lookups.length === 0) {
      setImagesByMbid(new Map());
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
        setImagesByMbid(results);
      } catch {
        if (!active) {
          return;
        }
        setImagesByMbid(new Map());
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

  return { imagesByMbid, loading };
}
