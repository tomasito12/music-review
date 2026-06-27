import type { ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";

interface ArtistImageProps {
  artistName: string;
  image: ArtistImageData;
}

/** Renders a highlight tile photo with required attribution. */
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
        loading="lazy"
        src={image.thumbnailUrl}
      />
      <figcaption className="artist-attribution">{image.attributionText}</figcaption>
    </figure>
  );
}
