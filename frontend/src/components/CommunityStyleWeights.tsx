import type { ReactElement } from "react";

import {
  communityWeightBiasFromStored,
  updateCommunityWeightBias,
} from "../lib/communityWeightMapping";
import { formatCommunityExampleArtists } from "../lib/profileFormatting";
import type { TasteCommunityOption } from "../lib/plattenradarApi";
import { BalanceSlider } from "./BalanceSlider";

interface CommunityStyleWeightsProps {
  applyMode?: "immediate" | "commit";
  communities: TasteCommunityOption[];
  selectedCommunityIds: string[];
  weights: Record<string, number>;
  onChange: (weights: Record<string, number>) => void;
}

export function CommunityStyleWeights({
  applyMode = "immediate",
  communities,
  selectedCommunityIds,
  weights,
  onChange,
}: CommunityStyleWeightsProps): ReactElement {
  const communityById = new Map(communities.map((community) => [community.id, community]));
  const selectedCommunities = [...selectedCommunityIds]
    .sort((left, right) => {
      const leftLabel = communityById.get(left)?.label ?? left;
      const rightLabel = communityById.get(right)?.label ?? right;
      return leftLabel.localeCompare(rightLabel, "de");
    })
    .map((communityId) => ({
      communityId,
      community: communityById.get(communityId),
    }));

  if (selectedCommunities.length === 0) {
    return (
      <p className="filter-muted-copy">
        Wähle zuerst Detailstile aus, um einzelne Stilrichtungen zu gewichten.
      </p>
    );
  }

  return (
    <div className="style-weight-grid">
      {selectedCommunities.map(({ communityId, community }) => {
        const storedWeight = weights[communityId] ?? 0.5;
        const bias = communityWeightBiasFromStored(storedWeight);
        const exampleCaption = formatCommunityExampleArtists(
          community?.example_artists ?? [],
        );

        return (
          <article className="style-weight-card" key={communityId}>
            <p className="style-weight-name">{community?.label ?? communityId}</p>
            {exampleCaption !== "" && (
              <p className="style-weight-artists">{exampleCaption}</p>
            )}
            <div className="style-weight-slider-row">
              <span
                aria-hidden="true"
                className="style-weight-cap"
                title="Geringeres Gewicht für diese Stilrichtung"
              >
                −
              </span>
              <BalanceSlider
                applyMode={applyMode}
                ariaLabel={`Gewicht für ${community?.label ?? communityId}`}
                onChange={(bias) => {
                  onChange(
                    updateCommunityWeightBias(weights, communityId, bias),
                  );
                }}
                value={bias}
              />
              <span
                aria-hidden="true"
                className="style-weight-cap"
                title="Stärkeres Gewicht für diese Stilrichtung"
              >
                +
              </span>
            </div>
          </article>
        );
      })}
    </div>
  );
}
