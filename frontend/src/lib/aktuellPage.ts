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

export const NEW_REVIEWS_PER_ROUND = 20;

export interface AktuellBriefing {
  description: string;
  kicker: string;
  title: string;
}

/** Estimate pool size when batch history is unavailable (fallback only). */
export function newestCountFromUpdateRounds(rounds: number): number {
  return Math.min(200, Math.max(1, rounds) * NEW_REVIEWS_PER_ROUND);
}

/** Builds the personal briefing copy for the Aktuell reference screen. */
export function buildAktuellBriefing(
  total: number,
  shownCount: number,
  _updateRoundLabel: string,
): AktuellBriefing {
  const effectiveTotal = Math.max(total, shownCount);
  if (effectiveTotal === 0) {
    return {
      kicker: "Dein Update",
      title: "Diesmal gab es keine sicheren Treffer.",
      description:
        "Wenn neue Rezensionen nah an deinem Musikprofil liegen, tauchen sie hier zuerst auf.",
    };
  }
  if (effectiveTotal <= 3) {
    return {
      kicker: "Dein Update",
      title: "Ein kleiner Schwung, aber ein paar Fundstücke sind nah dran.",
      description:
        "Nicht viel lag diesmal genau auf deiner Linie. Die besten Einstiege stehen trotzdem direkt oben.",
    };
  }
  return {
    kicker: "Schön, dass du zurück bist",
    title: `${effectiveTotal} neue Rezensionen liegen nah an deinem Musikprofil.`,
    description:
      "Starte mit den stärksten Fundstücken und scanne danach den restlichen Update-Schwung.",
  };
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
    title: "Drei Einstiege für deinen ersten Klick.",
    description:
      "Diese Fundstücke liegen nah an deinem Profil, sind stark bewertet oder öffnen eine spannende Abzweigung.",
  };
}

/** Profile-fit scores below this threshold qualify for the outside-profile highlight. */
export const OUTSIDE_PROFILE_SCORE_MAX = 0.7;

/** Derives editorial highlight cards from a ranked new-reviews list. */
export function buildAktuellHighlights(
  recommendations: Recommendation[],
): RecommendationHighlight[] {
  if (recommendations.length === 0) {
    return [];
  }

  const bestFit = pickTopBy(recommendations, compareByScoreThenRating);
  const remainingAfterBestFit = excludeRecommendations(recommendations, bestFit);
  const criticFavorite = pickTopBy(remainingAfterBestFit, compareByRatingThenScore);
  const outsidePool = excludeRecommendations(
    remainingAfterBestFit,
    criticFavorite,
  ).filter((item) => item.score < OUTSIDE_PROFILE_SCORE_MAX);
  const outsideProfile = pickTopBy(outsidePool, compareByRatingThenLowestScore);

  const highlights: RecommendationHighlight[] = [];
  const addHighlight = (
    label: string,
    description: string,
    recommendation: Recommendation | undefined,
  ): void => {
    if (recommendation === undefined) {
      return;
    }
    const duplicate = highlights.some((item) =>
      isSameRecommendation(item.recommendation, recommendation),
    );
    if (duplicate) {
      return;
    }
    highlights.push({ label, description, recommendation });
  };

  addHighlight(
    "Beste Passung",
    "Das Album mit dem höchsten Gesamtscore in diesem Update-Schwung.",
    bestFit,
  );
  addHighlight(
    "Kritikerfavorit",
    "Die höchste Plattentests-Bewertung unter den übrigen Neuerscheinungen.",
    criticFavorite,
  );
  addHighlight(
    "Außerhalb deines Profils",
    "Hoch bewertet, aber deutlich unter deiner üblichen Passung.",
    outsideProfile,
  );

  return highlights;
}

function isSameRecommendation(
  left: Recommendation,
  right: Recommendation,
): boolean {
  return left.artist === right.artist && left.album === right.album;
}

function excludeRecommendations(
  recommendations: Recommendation[],
  ...excluded: Array<Recommendation | undefined>
): Recommendation[] {
  const excludedItems = excluded.filter(
    (item): item is Recommendation => item !== undefined,
  );
  return recommendations.filter(
    (item) =>
      !excludedItems.some((excludedItem) =>
        isSameRecommendation(item, excludedItem),
      ),
  );
}

function compareByScoreThenRating(
  left: Recommendation,
  right: Recommendation,
): number {
  if (right.score !== left.score) {
    return right.score - left.score;
  }
  return right.rating - left.rating;
}

function compareByRatingThenScore(
  left: Recommendation,
  right: Recommendation,
): number {
  if (right.rating !== left.rating) {
    return right.rating - left.rating;
  }
  return right.score - left.score;
}

function compareByRatingThenLowestScore(
  left: Recommendation,
  right: Recommendation,
): number {
  if (right.rating !== left.rating) {
    return right.rating - left.rating;
  }
  return left.score - right.score;
}

function pickTopBy(
  recommendations: Recommendation[],
  compare: (left: Recommendation, right: Recommendation) => number,
): Recommendation | undefined {
  if (recommendations.length === 0) {
    return undefined;
  }
  return [...recommendations].sort(compare)[0];
}
