import type { ReactElement } from "react";

import type { ArtistImageData } from "../../lib/artistImageApi";
import { isVisualTestMode } from "../../lib/visualTestMode";

interface PlaylistArtistMosaicProps {
  imagesByLookupKey: ReadonlyMap<string, ArtistImageData | null>;
  tiles: Array<{ artistName: string; lookupKey: string }>;
}

/** Small overlapping artist photo strip above the playlist track list. */
export function PlaylistArtistMosaic({
  imagesByLookupKey,
  tiles,
}: PlaylistArtistMosaicProps): ReactElement | null {
  if (tiles.length === 0) {
    return null;
  }

  return (
    <div aria-label="Künstler in dieser Playlist" className="playlist-artist-mosaic" role="list">
      {tiles.map((tile) => {
        const image = imagesByLookupKey.get(tile.lookupKey);
        if (image === null || image === undefined) {
          return null;
        }

        return (
          <img
            alt={tile.artistName}
            className="playlist-artist-mosaic-tile"
            decoding="async"
            key={tile.lookupKey}
            loading={isVisualTestMode() ? "eager" : "lazy"}
            role="listitem"
            src={image.thumbnailUrl}
          />
        );
      })}
    </div>
  );
}
