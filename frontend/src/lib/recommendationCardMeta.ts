import type { Recommendation } from "../types";

/** Format API release dates for German card meta lines. */
export function formatReleaseDate(
  releaseDate: string | undefined,
  year: number,
): string {
  if (releaseDate !== undefined && releaseDate !== "") {
    const isoMatch = /^(\d{4})-(\d{2})-(\d{2})/.exec(releaseDate);
    if (isoMatch !== null) {
      return `${isoMatch[3]}.${isoMatch[2]}.${isoMatch[1]}`;
    }
  }
  if (year > 0) {
    return String(year);
  }
  return "";
}

/** Build the primary metadata line for a recommendation card. */
export function recommendationCardMetaParts(
  recommendation: Pick<
    Recommendation,
    "year" | "rating" | "recordLabel" | "score" | "releaseDate"
  >,
): string[] {
  const parts: string[] = [];
  const release = formatReleaseDate(recommendation.releaseDate, recommendation.year);
  if (release !== "") {
    parts.push(release);
  }
  parts.push(`${recommendation.rating}/10 bei plattentests.de`);
  parts.push(`Score ${recommendation.score.toFixed(2)}`);
  if (recommendation.recordLabel !== undefined && recommendation.recordLabel.trim() !== "") {
    parts.push(`Plattenlabel: ${recommendation.recordLabel.trim()}`);
  }
  return parts;
}
