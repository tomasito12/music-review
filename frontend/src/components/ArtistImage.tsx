import type { ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";
import { isVisualTestMode } from "../lib/visualTestMode";

interface ArtistImageProps {
  artistName: string;
  image: ArtistImageData;
}

/** Renders a highlight tile photo with a discrete source attribution control. */
export function ArtistImage({
  artistName,
  image,
}: ArtistImageProps): ReactElement {
  return (
    <figure className="highlight-tile-figure">
      <img
        alt={artistName}
        className="highlight-tile-photo"
        decoding="async"
        loading={isVisualTestMode() ? "eager" : "lazy"}
        src={image.thumbnailUrl}
      />
      <details className="artist-image-source">
        <summary>Quelle</summary>
        <div className="artist-image-source-panel">
          <p>{image.attributionText}</p>
          <a href={image.sourceUrl} rel="noreferrer" target="_blank">
            Bild auf Wikimedia Commons
          </a>
        </div>
      </details>
    </figure>
  );
}
