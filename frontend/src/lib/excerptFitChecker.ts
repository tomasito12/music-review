import { EXCERPT_PREVIEW_LINE_COUNT } from "./recommendationExcerpt";

export interface ExcerptFitChecker {
  fits: (candidate: string) => boolean;
  destroy: () => void;
}

/**
 * Build a line-count fit predicate using an off-screen clone of the excerpt styles.
 * Avoids flex-stretched client heights on the visible element.
 */
export function createExcerptFitChecker(
  referenceElement: HTMLElement,
  lineCount: number = EXCERPT_PREVIEW_LINE_COUNT,
): ExcerptFitChecker {
  const measureElement = document.createElement("p");
  measureElement.setAttribute("aria-hidden", "true");
  measureElement.style.position = "fixed";
  measureElement.style.left = "-9999px";
  measureElement.style.top = "0";
  measureElement.style.visibility = "hidden";
  measureElement.style.pointerEvents = "none";
  measureElement.style.overflow = "visible";
  measureElement.style.maxHeight = "none";
  measureElement.style.height = "auto";
  measureElement.style.flex = "none";
  measureElement.style.margin = "0";
  measureElement.style.padding = "0";
  measureElement.style.border = "0";
  document.body.appendChild(measureElement);

  const syncMeasureStyles = (): void => {
    const styles = window.getComputedStyle(referenceElement);
    measureElement.style.width = `${referenceElement.clientWidth}px`;
    measureElement.style.font = styles.font;
    measureElement.style.lineHeight = styles.lineHeight;
    measureElement.style.letterSpacing = styles.letterSpacing;
    measureElement.style.wordSpacing = styles.wordSpacing;
    measureElement.style.whiteSpace = styles.whiteSpace;
    measureElement.style.wordBreak = styles.wordBreak;
    measureElement.style.hyphens = styles.hyphens;
  };

  const maxContentHeight = (): number => {
    const styles = window.getComputedStyle(referenceElement);
    const lineHeight = Number.parseFloat(styles.lineHeight);
    if (!Number.isFinite(lineHeight) || lineHeight <= 0) {
      return 0;
    }
    return lineHeight * lineCount;
  };

  const fits = (candidate: string): boolean => {
    if (referenceElement.clientWidth <= 0) {
      return true;
    }

    syncMeasureStyles();
    measureElement.textContent = candidate;

    const allowedHeight = maxContentHeight();
    if (allowedHeight <= 0) {
      return candidate.length === 0;
    }

    return measureElement.scrollHeight <= allowedHeight + 0.5;
  };

  const destroy = (): void => {
    measureElement.remove();
  };

  return { fits, destroy };
}
