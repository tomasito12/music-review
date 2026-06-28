import { repairPlattentestsText } from "./plattentestsTextEncoding";

export const EXCERPT_PREVIEW_LINE_COUNT = 3;

/** Normalize review excerpt whitespace for card previews. */
export function normalizeExcerptText(text: string): string {
  return repairPlattentestsText(text).trim().replace(/\s+/g, " ");
}

/**
 * Fit excerpt copy into a container using a caller-provided predicate.
 * Appends ``[...]`` only when the full text does not fit.
 */
export function buildExcerptPreview(
  text: string,
  fits: (preview: string) => boolean,
): string {
  const normalized = normalizeExcerptText(text);
  if (normalized.length === 0) {
    return "";
  }
  if (fits(normalized)) {
    return normalized;
  }

  const words = normalized.split(" ");
  let bestFitLength = 0;
  let low = 1;
  let high = words.length;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const candidate = `${words.slice(0, mid).join(" ")} [...]`;
    if (fits(candidate)) {
      bestFitLength = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  if (bestFitLength >= words.length) {
    return normalized;
  }

  return `${words.slice(0, bestFitLength).join(" ")} [...]`;
}
