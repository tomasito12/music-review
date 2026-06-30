import type { ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";

interface ArtistListThumbnailProps {
  artistName: string;
  image: ArtistImageData;
  onFailed?: () => void;
}

/** Compact artist photo for dense recommendation list rows. */
export function ArtistListThumbnail({
  artistName,
  image,
  onFailed,
}: ArtistListThumbnailProps): ReactElement {
  return (
    <img
      alt={artistName}
      className="recommendation-card-thumbnail"
      decoding="async"
      loading="lazy"
      onError={() => {
        onFailed?.();
      }}
      src={image.thumbnailUrl}
    />
  );
}
