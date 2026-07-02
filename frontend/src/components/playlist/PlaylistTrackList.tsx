import type { ReactElement } from "react";

import { artistImageLookupKey } from "../../lib/artistImageLookupKey";
import type { PlaylistExportItem } from "../../lib/playlistExport";
import {
  selectPlaylistMosaicLookups,
  uniquePlaylistArtistLookups,
} from "../../lib/playlistResults";
import { useArtistImagesBatch } from "../../lib/useArtistImagesBatch";

import { PlaylistArtistMosaic } from "./PlaylistArtistMosaic";
import { PlaylistTrackRow } from "./PlaylistTrackRow";

interface PlaylistTrackListProps {
  items: PlaylistExportItem[];
}

/** Hybrid playlist result list with artist photos and review links. */
export function PlaylistTrackList({ items }: PlaylistTrackListProps): ReactElement {
  const artistLookups = uniquePlaylistArtistLookups(items);
  const { imagesByLookupKey, imagesSettled } = useArtistImagesBatch(artistLookups);
  const mosaicTiles = imagesSettled
    ? selectPlaylistMosaicLookups(items, imagesByLookupKey)
    : [];

  return (
    <section
      aria-label="Playlist-Titel"
      className="playlist-track-list"
      data-visual-images={imagesSettled ? "ready" : "pending"}
    >
      <PlaylistArtistMosaic imagesByLookupKey={imagesByLookupKey} tiles={mosaicTiles} />
      <div className="playlist-track-rows">
        {items.map((item, index) => {
          const lookupKey = artistImageLookupKey({ artistName: item.artist });
          const artistImage =
            lookupKey.length > 0 ? imagesByLookupKey.get(lookupKey) ?? null : null;

          return (
            <PlaylistTrackRow
              artistImage={artistImage}
              index={index}
              item={item}
              key={`${item.review_id}-${item.track_title}-${index}`}
            />
          );
        })}
      </div>
    </section>
  );
}
