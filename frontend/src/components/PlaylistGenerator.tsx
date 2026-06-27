import { useCallback, useEffect, useState } from "react";
import type { ReactElement } from "react";

import { UPDATE_ROUND_OPTIONS } from "../lib/aktuellPage";
import type { ApiClient } from "../lib/apiClient";
import { exportPlaylist } from "../lib/plattenradarApi";
import type { TemporaryTasteProfile } from "../lib/plattenradarApi";
import {
  defaultPlaylistName,
  downloadPlaylistContent,
  playlistItemsToCsv,
} from "../lib/playlistExport";
import type { PlaylistExportResult } from "../lib/playlistExport";
import type { RecommendationSource } from "../types";

interface PlaylistGeneratorProps {
  apiClient: () => ApiClient;
  initialSource: RecommendationSource;
  onEditProfile: () => void;
  profile: TemporaryTasteProfile | null;
  updateRounds: string;
}

export function PlaylistGenerator({
  apiClient,
  initialSource,
  onEditProfile,
  profile,
  updateRounds: initialUpdateRounds,
}: PlaylistGeneratorProps): ReactElement {
  const [source, setSource] = useState<RecommendationSource>(initialSource);
  const [updateRounds, setUpdateRounds] = useState(initialUpdateRounds);
  const [trackCount, setTrackCount] = useState(30);
  const [focus, setFocus] = useState<"balanced" | "top">("balanced");
  const [variation, setVariation] = useState(0.35);
  const [name, setName] = useState(() => defaultPlaylistName());
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<PlaylistExportResult | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

  useEffect(() => {
    setSource(initialSource);
  }, [initialSource]);

  useEffect(() => {
    setUpdateRounds(initialUpdateRounds);
  }, [initialUpdateRounds]);

  const generatePlaylist = useCallback(async () => {
    if (profile === null) {
      return;
    }

    setIsGenerating(true);
    setError(null);
    setCopyMessage(null);

    try {
      const result = await exportPlaylist(apiClient(), {
        source,
        profile,
        name,
        targetCount: trackCount,
        focus,
        variation,
        updateRounds,
        format: "txt",
      });
      setExportResult(result);
    } catch (generateError) {
      const message =
        generateError instanceof Error
          ? generateError.message
          : "Die Playlist konnte nicht erzeugt werden.";
      setError(message);
      setExportResult(null);
    } finally {
      setIsGenerating(false);
    }
  }, [
    apiClient,
    focus,
    name,
    profile,
    source,
    trackCount,
    updateRounds,
    variation,
  ]);

  if (profile === null) {
    return (
      <section className="playlist-page page-shell">
        <header className="page-header">
          <p className="eyebrow">Playlists</p>
          <h1>Neue Playlist erzeugen</h1>
        </header>
        <div className="empty-results">
          <p>
            Für Playlist-Vorschläge brauchst du zuerst ein Musikprofil mit
            Stilrichtungen und Filtern.
          </p>
          <button className="primary-button" onClick={onEditProfile} type="button">
            Musikprofil anlegen
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="playlist-page page-shell">
      <header className="page-header">
        <p className="eyebrow">Playlists</p>
        <h1>Neue Playlist erzeugen</h1>
        <p>
          Stelle die Playlist passend zu deinem Hörmoment zusammen. Anschließend
          kannst du sie als Text, TXT oder CSV in deinen Musikdienst übertragen.
        </p>
      </header>
      <div className="generator-card">
        <label>
          Musik auswählen aus
          <select
            onChange={(event) => {
              setSource(event.target.value as RecommendationSource);
              setExportResult(null);
            }}
            value={source}
          >
            <option value="aktuell">Den letzten Updates</option>
            <option value="entdecken">Dem Plattentests-Archiv</option>
          </select>
        </label>
        {source === "aktuell" && (
          <label>
            Zeitraum
            <select
              onChange={(event) => setUpdateRounds(event.target.value)}
              value={updateRounds}
            >
              {UPDATE_ROUND_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Anzahl Tracks
          <input
            max="100"
            min="5"
            onChange={(event) => setTrackCount(Number(event.target.value))}
            step="1"
            type="number"
            value={trackCount}
          />
        </label>
        <label>
          Fokus
          <select
            onChange={(event) => setFocus(event.target.value as "balanced" | "top")}
            value={focus}
          >
            <option value="balanced">Breit über die Liste</option>
            <option value="top">Stärker auf Top-Treffer</option>
          </select>
        </label>
        {source === "entdecken" && (
          <label>
            Abwechslung
            <input
              aria-label="Abwechslung in der Archiv-Playlist"
              max="1"
              min="0"
              onChange={(event) => setVariation(Number(event.target.value))}
              step="0.05"
              type="range"
              value={variation}
            />
            <span className="field-hint">
              Mehr Abwechslung verteilt die Auswahl stärker über die Rangliste.
            </span>
          </label>
        )}
        <label>
          Playlist-Name
          <input onChange={(event) => setName(event.target.value)} type="text" value={name} />
        </label>
        <button
          className="primary-button"
          disabled={isGenerating}
          onClick={() => void generatePlaylist()}
          type="button"
        >
          {isGenerating ? "Playlist wird erzeugt …" : "Playlist vorbereiten"}
        </button>
        {error !== null && (
          <div className="playlist-error" role="alert">
            <p>{error}</p>
            <button
              className="secondary-button"
              disabled={isGenerating}
              onClick={() => void generatePlaylist()}
              type="button"
            >
              Erneut versuchen
            </button>
          </div>
        )}
      </div>
      {exportResult !== null && (
        <div className="playlist-results">
          <h2>{exportResult.name}</h2>
          {exportResult.items.length < trackCount && (
            <p className="playlist-warning">
              Es wurden {exportResult.items.length} von {trackCount} gewünschten Titeln
              gefunden (wenige eindeutige Tracks im Pool).
            </p>
          )}
          {exportResult.items.length === 0 ? (
            <p>
              Es konnten keine Playlist-Vorschläge erzeugt werden. Bitte Pool oder
              Einstellungen prüfen.
            </p>
          ) : (
            <>
              <div className="playlist-actions">
                <button
                  className="secondary-button"
                  onClick={() => {
                    void navigator.clipboard.writeText(exportResult.content).then(() => {
                      setCopyMessage("In die Zwischenablage kopiert.");
                    });
                  }}
                  type="button"
                >
                  Text kopieren
                </button>
                <button
                  className="secondary-button"
                  onClick={() =>
                    downloadPlaylistContent(
                      exportResult.filename,
                      exportResult.content,
                      exportResult.content_type,
                    )
                  }
                  type="button"
                >
                  Als TXT herunterladen
                </button>
                <button
                  className="secondary-button"
                  onClick={() => {
                    const csv = playlistItemsToCsv(exportResult.items);
                    downloadPlaylistContent(
                      exportResult.filename.replace(/\.txt$/i, ".csv"),
                      csv,
                      "text/csv;charset=utf-8",
                    );
                  }}
                  type="button"
                >
                  Als CSV herunterladen
                </button>
              </div>
              {copyMessage !== null && <p className="field-hint">{copyMessage}</p>}
              <table className="playlist-table">
                <thead>
                  <tr>
                    <th>Künstler</th>
                    <th>Album</th>
                    <th>Track</th>
                  </tr>
                </thead>
                <tbody>
                  {exportResult.items.map((item) => (
                    <tr key={`${item.review_id}-${item.track_title}`}>
                      <td>{item.artist}</td>
                      <td>{item.album}</td>
                      <td>{item.track_title}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <label>
                Für TuneMyMusic (Freitext)
                <textarea readOnly rows={8} value={exportResult.content} />
              </label>
            </>
          )}
        </div>
      )}
      <aside className="import-note">
        <h2>Danach</h2>
        <p>
          Die fertige Liste wird hier angezeigt. Von dort kannst du den Text
          kopieren oder TXT/CSV herunterladen und in TuneMyMusic importieren.
        </p>
      </aside>
    </section>
  );
}
