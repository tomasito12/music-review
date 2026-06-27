import type { Recommendation } from "../types";

/** Build the primary metadata line for a recommendation card. */
export function recommendationCardMetaParts(
  recommendation: Pick<Recommendation, "year" | "rating" | "recordLabel">,
): string[] {
  const parts = [
    String(recommendation.year),
    `${recommendation.rating}/10 bei plattentests.de`,
  ];
  if (recommendation.recordLabel !== undefined && recommendation.recordLabel !== "") {
    parts.push(recommendation.recordLabel);
  }
  return parts;
}
