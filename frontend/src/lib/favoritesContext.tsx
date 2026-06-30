import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";

import type { Recommendation, SavedAlbum } from "../types";

import { useApiClient } from "./apiClientContext";
import { ApiClient } from "./apiClient";
import { createFavoritesSyncQueue } from "./favoritesSyncQueue";
import {
  addLocalFavorite,
  clearLocalFavorites,
  localFavoritesToSavedAlbums,
  readLocalFavorites,
  removeLocalFavorite,
} from "./localFavoritesStorage";
import {
  fetchFavorites,
  mergeFavorites,
  recommendationSourceToApiSource,
  removeFavorite,
  saveFavorite,
} from "./plattenradarApi";
import {
  addRemovedFavoriteId,
  readRemovedFavoriteIds,
  removeRemovedFavoriteId,
} from "./removedFavoritesStorage";

interface FavoritesContextValue {
  favorites: SavedAlbum[];
  isAuthenticated: boolean;
  isLoading: boolean;
  isSaved: (reviewId: number) => boolean;
  isToggling: (reviewId: number) => boolean;
  removeSavedAlbum: (reviewId: number) => Promise<void>;
  savedCount: number;
  toggleSave: (recommendation: Recommendation) => Promise<void>;
}

const FavoritesContext = createContext<FavoritesContextValue | null>(null);

interface FavoritesProviderProps {
  accessToken: string | null;
  children: ReactNode;
}

/** Provides saved-album state for cards and the account page. */
export function FavoritesProvider({
  accessToken,
  children,
}: FavoritesProviderProps): ReactElement {
  const createClient = useApiClient();
  const isAuthenticated = accessToken !== null;
  const [serverFavorites, setServerFavorites] = useState<SavedAlbum[]>([]);
  const [localFavorites, setLocalFavorites] = useState<SavedAlbum[]>(() =>
    localFavoritesToSavedAlbums(readLocalFavorites()),
  );
  const [isLoading, setIsLoading] = useState(false);
  const [togglingIds, setTogglingIds] = useState<Set<number>>(() => new Set());
  const enqueueSync = useMemo(() => createFavoritesSyncQueue(), []);
  const hadAccessTokenRef = useRef(false);

  const refreshLocalFavorites = useCallback((): void => {
    setLocalFavorites(localFavoritesToSavedAlbums(readLocalFavorites()));
  }, []);

  const loadServerFavorites = useCallback(
    async (options: { mergeGuest: boolean }): Promise<void> => {
      if (accessToken === null) {
        setServerFavorites([]);
        return;
      }
      setIsLoading(true);
      try {
        const client = createClient();
        if (options.mergeGuest) {
          await mergeLocalFavoritesAfterLogin(client);
          refreshLocalFavorites();
        }
        const items = await fetchFavorites(client);
        setServerFavorites(items);
      } catch {
        setServerFavorites([]);
      } finally {
        setIsLoading(false);
      }
    },
    [accessToken, createClient, refreshLocalFavorites],
  );

  useEffect(() => {
    if (accessToken === null) {
      hadAccessTokenRef.current = false;
      setServerFavorites([]);
      return;
    }

    const shouldMergeGuest = !hadAccessTokenRef.current;
    hadAccessTokenRef.current = true;
    void enqueueSync(() => loadServerFavorites({ mergeGuest: shouldMergeGuest }));
  }, [accessToken, enqueueSync, loadServerFavorites]);

  const favorites = isAuthenticated ? serverFavorites : localFavorites;
  const savedIds = useMemo(
    () => new Set(favorites.map((item) => item.reviewId)),
    [favorites],
  );

  const setToggling = useCallback((reviewId: number, active: boolean): void => {
    setTogglingIds((current) => {
      const next = new Set(current);
      if (active) {
        next.add(reviewId);
      } else {
        next.delete(reviewId);
      }
      return next;
    });
  }, []);

  const toggleSave = useCallback(
    async (recommendation: Recommendation): Promise<void> => {
      const reviewId = recommendation.reviewId;
      const currentlySaved = savedIds.has(reviewId);
      setToggling(reviewId, true);

      try {
        await enqueueSync(async () => {
          if (!isAuthenticated) {
            if (currentlySaved) {
              removeLocalFavorite(reviewId);
            } else {
              addLocalFavorite(recommendation);
            }
            refreshLocalFavorites();
            return;
          }

          const client = createClient();
          if (currentlySaved) {
            removeLocalFavorite(reviewId);
            addRemovedFavoriteId(reviewId);
            setServerFavorites((current) =>
              current.filter((item) => item.reviewId !== reviewId),
            );
            await removeFavorite(client, reviewId);
            return;
          }

          removeRemovedFavoriteId(reviewId);
          removeLocalFavorite(reviewId);
          const optimistic: SavedAlbum = {
            reviewId,
            artist: recommendation.artist,
            album: recommendation.album,
            reviewUrl: recommendation.reviewUrl,
            source: recommendation.source,
            savedAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
          };
          setServerFavorites((current) => [optimistic, ...current]);
          const saved = await saveFavorite(client, reviewId, {
            artist: recommendation.artist,
            album: recommendation.album,
            review_url: recommendation.reviewUrl,
            source: recommendationSourceToApiSource(recommendation.source),
          });
          setServerFavorites((current) => {
            const withoutCurrent = current.filter((item) => item.reviewId !== reviewId);
            return [saved, ...withoutCurrent];
          });
        });
      } catch {
        if (isAuthenticated) {
          await enqueueSync(() => loadServerFavorites({ mergeGuest: false }));
        } else {
          refreshLocalFavorites();
        }
      } finally {
        setToggling(reviewId, false);
      }
    },
    [
      createClient,
      enqueueSync,
      isAuthenticated,
      loadServerFavorites,
      refreshLocalFavorites,
      savedIds,
      setToggling,
    ],
  );

  const removeSavedAlbum = useCallback(
    async (reviewId: number): Promise<void> => {
      setToggling(reviewId, true);
      try {
        await enqueueSync(async () => {
          if (!isAuthenticated) {
            removeLocalFavorite(reviewId);
            refreshLocalFavorites();
            return;
          }

          removeLocalFavorite(reviewId);
          addRemovedFavoriteId(reviewId);
          setServerFavorites((current) =>
            current.filter((item) => item.reviewId !== reviewId),
          );
          const client = createClient();
          await removeFavorite(client, reviewId);
        });
      } catch {
        if (isAuthenticated) {
          await enqueueSync(() => loadServerFavorites({ mergeGuest: false }));
        } else {
          refreshLocalFavorites();
        }
      } finally {
        setToggling(reviewId, false);
      }
    },
    [createClient, enqueueSync, isAuthenticated, loadServerFavorites, refreshLocalFavorites, setToggling],
  );

  const value = useMemo(
    () => ({
      favorites,
      isAuthenticated,
      isLoading,
      isSaved: (reviewId: number) => savedIds.has(reviewId),
      isToggling: (reviewId: number) => togglingIds.has(reviewId),
      removeSavedAlbum,
      savedCount: favorites.length,
      toggleSave,
    }),
    [
      favorites,
      isAuthenticated,
      isLoading,
      removeSavedAlbum,
      savedIds,
      toggleSave,
      togglingIds,
    ],
  );

  return (
    <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>
  );
}

/** Returns saved-album helpers for recommendation cards and account UI. */
export function useFavorites(): FavoritesContextValue {
  const context = useContext(FavoritesContext);
  if (context === null) {
    throw new Error("useFavorites must be used within FavoritesProvider.");
  }
  return context;
}

/** Merges guest favorites into the authenticated account after login. */
export async function mergeLocalFavoritesAfterLogin(client: ApiClient): Promise<number> {
  const removedIds = readRemovedFavoriteIds();
  const localItems = readLocalFavorites().filter(
    (item) => !removedIds.has(item.reviewId),
  );
  if (localItems.length === 0) {
    return 0;
  }
  const mergedCount = await mergeFavorites(
    client,
    localItems.map((item) => ({
      review_id: item.reviewId,
      artist: item.artist,
      album: item.album,
      review_url: item.reviewUrl,
      source:
        item.source === null ? null : recommendationSourceToApiSource(item.source),
      saved_at: item.savedAt,
    })),
  );
  clearLocalFavorites();
  return mergedCount;
}
