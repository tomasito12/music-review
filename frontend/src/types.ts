export type AppRoute =
  | "willkommen"
  | "aktuell"
  | "entdecken"
  | "playlists"
  | "musikprofil"
  | "konto";

export type UserState =
  | "anonymous_no_profile"
  | "anonymous_temporary_profile"
  | "authenticated_no_profile"
  | "authenticated_saved_profile"
  | "authenticated_unsaved_changes";

export type RecommendationSource = "aktuell" | "entdecken";

export interface RecommendationTag {
  label: string;
  affinity: number;
  matchesProfile: boolean;
}

export interface Recommendation {
  rank: number;
  reviewId: number;
  artist: string;
  album: string;
  year: number;
  rating: number;
  score: number;
  styleFit: number;
  albumStyleBreadth: number;
  fitLabel: string;
  fitPercent: number;
  releaseDate?: string;
  recordLabel?: string;
  excerpt: string;
  excerptContinues?: boolean;
  reviewUrl: string;
  tags: RecommendationTag[];
  source: RecommendationSource;
  artistMbid?: string;
}

export interface RecommendationHighlight {
  description: string;
  label: string;
  recommendation: Recommendation;
}

export interface SavedAlbum {
  reviewId: number;
  artist: string;
  album: string;
  reviewUrl: string;
  source: RecommendationSource | null;
  savedAt: string;
}

export interface UpdateSummary {
  description: string;
  title: string;
}

export interface PlaylistSettings {
  source: RecommendationSource;
  trackCount: number;
  focus: "balanced" | "top";
  variation: number;
  name: string;
}
