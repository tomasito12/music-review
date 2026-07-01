import type { ReactElement } from "react";

interface HighlightAccentPanelProps {
  fitLabel: string;
  fitPercent: number;
  rating: number;
}

/** Visual anchor panel used when a highlight has no artist photo. */
export function HighlightAccentPanel({
  fitLabel,
  fitPercent,
  rating,
}: HighlightAccentPanelProps): ReactElement {
  return (
    <div aria-hidden="true" className="highlight-tile-accent-panel">
      <p className="highlight-tile-accent-rating">
        <span className="highlight-tile-accent-rating-value">{rating}</span>
        <span className="highlight-tile-accent-rating-suffix">/10</span>
      </p>
      <p className="highlight-tile-accent-fit">{fitPercent}%</p>
      <p className="highlight-tile-accent-fit-label">{fitLabel}</p>
    </div>
  );
}
