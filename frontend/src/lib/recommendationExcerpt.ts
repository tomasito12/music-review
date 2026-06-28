import { repairPlattentestsText } from "./plattentestsTextEncoding";

export const EXCERPT_PREVIEW_LINE_COUNT = 3;
export const EXCERPT_PREVIEW_MARKER = " [...]";

export interface ExcerptPreviewOptions {
  /** The API excerpt continues beyond the returned snippet. */
  continues?: boolean;
}

/** Normalize review excerpt whitespace for card previews. */
export function normalizeExcerptText(text: string): string {
  return repairPlattentestsText(text).trim().replace(/\s+/g, " ");
}

function appendPreviewMarker(text: string): string {
  if (text.length === 0 || text.endsWith("[...]")) {
    return text;
  }
  return `${text}${EXCERPT_PREVIEW_MARKER}`;
}

function longestFittingPreview(
  normalized: string,
  fits: (preview: string) => boolean,
): string {
  const words = normalized.split(" ");
  let bestFitLength = 0;
  let low = 1;
  let high = words.length;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const candidate = appendPreviewMarker(words.slice(0, mid).join(" "));
    if (fits(candidate)) {
      bestFitLength = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  if (bestFitLength <= 0) {
    return appendPreviewMarker("");
  }

  return appendPreviewMarker(words.slice(0, bestFitLength).join(" "));
}

/**
 * Fit excerpt copy into a container using a caller-provided predicate.
 * Appends ``[...]`` when the source continues or the text does not fit.
 */
export function buildExcerptPreview(
  text: string,
  fits: (preview: string) => boolean,
  options: ExcerptPreviewOptions = {},
): string {
  const normalized = normalizeExcerptText(text);
  if (normalized.length === 0) {
    return "";
  }

  const continues = options.continues ?? false;
  if (!continues && fits(normalized)) {
    return normalized;
  }

  const markedFull = appendPreviewMarker(normalized);
  if (fits(markedFull)) {
    return markedFull;
  }

  return longestFittingPreview(normalized, fits);
}
