import type {
  Recommendation,
  RecommendationHighlight,
  UpdateSummary,
} from "../types";

export const UPDATE_ROUND_OPTIONS = [
  { value: "1", label: "Letzte Update-Runde" },
  { value: "4", label: "Letzte 4 Update-Runden" },
  { value: "8", label: "Letzte 8 Update-Runden" },
] as const;

export const NEW_REVIEWS_PER_ROUND = 30;

/** Maps UI update-round selection to the API newest_count parameter. */
export function newestCountFromUpdateRounds(rounds: number): number {
  return Math.min(200, Math.max(1, rounds) * NEW_REVIEWS_PER_ROUND);
}

/** Builds a short summary for the Aktuell highlight section. */
export function buildAktuellSummary(total: number): UpdateSummary {
  if (total === 0) {
    return {
      title: "Noch keine neuen Rezensionen im gewählten Zeitraum.",
      description:
        "Sobald frische Rezensionen verfügbar sind, erscheinen sie hier sortiert nach Passung.",
    };
  }
  return {
    title: `${total} neue Rezensionen im gewählten Zeitraum.`,
    description:
      "Plattenradar sortiert sie nach Passung zu deinem Musikprofil. Die Hervorhebungen darunter zeigen besonders lohnende Einstiege.",
  };
}

/** Derives editorial highlight cards from a ranked new-reviews list. */
export function buildAktuellHighlights(
  recommendations: Recommendation[],
): RecommendationHighlight[] {
  if (recommendations.length === 0) {
    return [];
  }

  const matched = recommendations.filter((item) =>
    item.tags.some((tag) => tag.matchesProfile),
  );
  const bestFit = pickTop(
    matched.length > 0 ? matched : recommendations,
    (item) => item.score,
  );
  const topRated = pickTop(recommendations, (item) => item.rating);
  const outsidePool = recommendations.filter(
    (item) => !item.tags.some((tag) => tag.matchesProfile),
  );
  const outside =
    pickTop(outsidePool, (item) => item.rating) ??
    recommendations.find((item) => item !== bestFit && item !== topRated) ??
    topRated;

  const highlights: RecommendationHighlight[] = [];
  const addHighlight = (
    label: string,
    description: string,
    recommendation: Recommendation,
  ): void => {
    const duplicate = highlights.some(
      (item) =>
        item.recommendation.artist === recommendation.artist &&
        item.recommendation.album === recommendation.album,
    );
    if (duplicate) {
      return;
    }
    highlights.push({ label, description, recommendation });
  };

  addHighlight(
    "Beste Passung",
    "Die stärkste Verbindung zu deinem aktuellen Musikprofil.",
    bestFit,
  );
  addHighlight(
    "Kritikerfavorit",
    "Besonders hoch bewertet in diesem Update-Schwung.",
    topRated,
  );
  addHighlight(
    "Außerhalb deines Profils",
    "Hoch bewertet, auch wenn es deinen Vorlieben weniger nahe ist.",
    outside,
  );

  return highlights.slice(0, 3);
}

function pickTop(
  recommendations: Recommendation[],
  scoreFor: (item: Recommendation) => number,
): Recommendation {
  return [...recommendations].sort((left, right) => scoreFor(right) - scoreFor(left))[0];
}
