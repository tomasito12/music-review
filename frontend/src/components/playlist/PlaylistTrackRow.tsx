import { useEffect, useState, type ReactElement } from "react";

import type { ArtistImageData } from "../../lib/artistImageApi";
import { artistInitials } from "../../lib/artistInitials";
import type { PlaylistExportItem } from "../../lib/playlistExport";
import { playlistReviewUrl, playlistTrackAsideParts } from "../../lib/playlistResults";

import { ArtistListThumbnail } from "../ArtistListThumbnail";

interface PlaylistTrackRowProps {
  artistImage?: ArtistImageData | null;
  index: number;
  item: PlaylistExportItem;
}

/** Compact hybrid playlist track row with artist photo or initials and review link. */
export function PlaylistTrackRow({
  artistImage = null,
  index,
  item,
}: PlaylistTrackRowProps): ReactElement {
  const [thumbnailVisible, setThumbnailVisible] = useState(artistImage !== null);
  const reviewUrl = playlistReviewUrl(item.review_id);
  const showThumbnail = artistImage !== null && thumbnailVisible;
  const aside = playlistTrackAsideParts(item);
  const hasAside = aside.year !== null || aside.label !== null;

  useEffect(() => {
    setThumbnailVisible(artistImage !== null);
  }, [artistImage]);

  return (
    <article
      className={`playlist-track-row${hasAside ? " playlist-track-row-with-aside" : ""}`}
    >
      <div aria-label={`Titel ${index + 1}`} className="rank">
        <span>{(index + 1).toString().padStart(2, "0")}</span>
      </div>
      <div aria-hidden={showThumbnail ? undefined : true} className="playlist-track-media">
        {showThumbnail && artistImage !== null ? (
          <ArtistListThumbnail
            artistName={item.artist}
            image={artistImage}
            onFailed={() => {
              setThumbnailVisible(false);
            }}
          />
        ) : (
          <span className="playlist-track-initials">{artistInitials(item.artist)}</span>
        )}
      </div>
      <div className="playlist-track-main">
        <h3 className="playlist-track-title">
          <a href={reviewUrl} rel="noreferrer" target="_blank">
            {item.track_title}
          </a>
        </h3>
        <p className="playlist-track-meta">
          {item.artist} · {item.album}
        </p>
        <a className="playlist-track-review-link" href={reviewUrl} rel="noreferrer" target="_blank">
          Zur Rezension
        </a>
      </div>
      {hasAside && (
        <div className="playlist-track-aside">
          {aside.year !== null && <span className="playlist-track-year">{aside.year}</span>}
          {aside.label !== null && <span className="playlist-track-label">{aside.label}</span>}
        </div>
      )}
    </article>
  );
}
