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

export interface AktuellBriefing {
  description: string;
  kicker: string;
  title: string;
}

/** Maps UI update-round selection to the API newest_count parameter. */
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
