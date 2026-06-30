import type { ReactElement } from "react";

import type { ArtistImageData } from "../lib/artistImageApi";
import { isVisualTestMode } from "../lib/visualTestMode";

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
      loading={isVisualTestMode() ? "eager" : "lazy"}
      onError={() => {
        onFailed?.();
      }}
      src={image.thumbnailUrl}
    />
  );
}
