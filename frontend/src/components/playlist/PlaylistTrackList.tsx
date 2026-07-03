import type { ReactElement } from "react";

import { artistImageLookupKey } from "../../lib/artistImageLookupKey";
import type { PlaylistExportItem } from "../../lib/playlistExport";
import { uniquePlaylistArtistLookups } from "../../lib/playlistResults";
import { limitPlaylistItemsForVisualTest } from "../../lib/visualTestListLimit";
import { useArtistImagesBatch } from "../../lib/useArtistImagesBatch";

import { PlaylistTrackRow } from "./PlaylistTrackRow";

interface PlaylistTrackListProps {
  items: PlaylistExportItem[];
}

/** Hybrid playlist result list with artist photos or initials and review links. */
export function PlaylistTrackList({ items }: PlaylistTrackListProps): ReactElement {
  const visibleItems = limitPlaylistItemsForVisualTest(items);
  const artistLookups = uniquePlaylistArtistLookups(visibleItems);
  const { imagesByLookupKey, imagesSettled } = useArtistImagesBatch(artistLookups);

  return (
    <section
      aria-label="Playlist-Titel"
      className="playlist-track-list"
      data-visual-images={imagesSettled ? "ready" : "pending"}
    >
      <div className="playlist-track-rows">
        {visibleItems.map((item, index) => {
          const lookupKey = artistImageLookupKey({
            artistMbid: item.artist_mbid?.trim() ?? undefined,
            artistName: item.artist,
          });
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
