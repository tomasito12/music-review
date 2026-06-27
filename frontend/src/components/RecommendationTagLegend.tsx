import type { ReactElement } from "react";

import {
  recommendationTagLegendSwatchStyle,
  recommendationTagStyle,
} from "../lib/recommendationTagStyles";

/** Compact legend for tag color intensity and profile matches. */
export function RecommendationTagLegend(): ReactElement {
  return (
    <p className="tag-legend" id="recommendation-tag-legend">
      <span className="tag-legend-label">Stil-Tags:</span>
      <span className="tag-legend-items">
        <span
          className="tag tag-legend-swatch"
          style={recommendationTagLegendSwatchStyle(0.75)}
        >
          stark
        </span>
        <span
          className="tag tag-legend-swatch"
          style={recommendationTagLegendSwatchStyle(0.35)}
        >
          mittel
        </span>
        <span
          className="tag tag-legend-swatch"
          style={recommendationTagLegendSwatchStyle(0.12)}
        >
          leicht
        </span>
        <span
          className="tag tag-legend-swatch tag-match"
          style={recommendationTagStyle({
            label: "Profil",
            affinity: 0.5,
            matchesProfile: true,
          })}
        >
          Profil
        </span>
      </span>
      <span className="tag-legend-copy">
        Dunkleres Rot = stärkere Stilnähe zum Album. Der Ring markiert Übereinstimmung
        mit deinem Musikprofil.
      </span>
    </p>
  );
}
