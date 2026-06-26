import { ApiClient } from "./apiClient";

import type { Recommendation, RecommendationTag } from "../types";

export interface TasteCommunityOption {
  broad_categories: string[];
  id: string;
  label: string;
}

export interface TemporaryTasteProfile {
  community_weights_raw: Record<string, number>;
  filter_settings: {
    overall_weight_alpha: number;
    overall_weight_beta: number;
    overall_weight_gamma: number;
    rating_min: number;
    rating_max: number;
    score_min: number;
    score_max: number;
  };
  name: string;
  selected_communities: string[];
}

interface ApiCommunityMatch {
  affinity: number;
  id: string;
  label: string;
  matched: boolean;
}

interface ApiRecommendation {
  album: string;
  artist: string;
  labels: string;
  matched_tags: ApiCommunityMatch[];
  overall_score: number;
  rank: number;
  rating: number | null;
  source: "archive" | "new_reviews";
  text_excerpt: string;
  url: string | null;
  year: number | null;
}

interface ApiRecommendationSet {
  items: ApiRecommendation[];
  total: number;
}

/** Loads selectable music styles from the Plattenradar API. */
export async function loadTasteCommunities(
  client: ApiClient,
): Promise<TasteCommunityOption[]> {
  return client.get<TasteCommunityOption[]>("/v1/taste-communities");
}

/** Loads one page of archive recommendations for a temporary taste profile. */
export async function loadArchiveRecommendations(
  client: ApiClient,
  profile: TemporaryTasteProfile,
): Promise<{ recommendations: Recommendation[]; total: number }> {
  const response = await client.post<ApiRecommendationSet>(
    "/v1/recommendations/archive",
    { profile, limit: 20, offset: 0 },
  );
  return {
    recommendations: response.items.map(toRecommendation),
    total: response.total,
  };
}

/** Creates the balanced temporary profile used before a user saves an account. */
export function createTemporaryTasteProfile(
  selectedCommunities: string[],
): TemporaryTasteProfile {
  return {
    name: "Temporäres Musikprofil",
    selected_communities: selectedCommunities,
    community_weights_raw: Object.fromEntries(
      selectedCommunities.map((communityId) => [communityId, 1]),
    ),
    filter_settings: {
      rating_min: 6,
      rating_max: 10,
      score_min: 0.4,
      score_max: 1,
      overall_weight_alpha: 0.4,
      overall_weight_beta: 0.3,
      overall_weight_gamma: 0.3,
    },
  };
}

function toRecommendation(item: ApiRecommendation): Recommendation {
  const tags = item.matched_tags.map(toRecommendationTag);
  const fitPercent = Math.round(item.overall_score * 100);
  return {
    rank: item.rank,
    artist: item.artist,
    album: item.album,
    year: item.year ?? 0,
    rating: item.rating ?? 0,
    score: item.overall_score,
    fitLabel: fitLabel(item.overall_score),
    fitPercent,
    recordLabel: item.labels || undefined,
    excerpt: item.text_excerpt,
    reviewUrl: item.url ?? "https://www.plattentests.de/",
    tags,
    source: "entdecken",
  };
}

function toRecommendationTag(tag: ApiCommunityMatch): RecommendationTag {
  return {
    label: tag.label,
    matchesProfile: tag.matched,
    strength: tag.affinity >= 0.7 ? "high" : tag.affinity >= 0.35 ? "medium" : "low",
  };
}

function fitLabel(score: number): string {
  if (score >= 0.75) {
    return "Sehr passend";
  }
  if (score >= 0.4) {
    return "Passend";
  }
  return "Interessanter Randbereich";
}
