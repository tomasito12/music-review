import { useCallback, useEffect, useState } from "react";
import type { ReactElement } from "react";

import { PlaylistDualSlider } from "./playlist/PlaylistDualSlider";
import { PlaylistTrackList } from "./playlist/PlaylistTrackList";
import { TuneMyMusicGuide } from "./playlist/TuneMyMusicGuide";
import { UPDATE_ROUND_OPTIONS } from "../lib/aktuellPage";
import type { ApiClient } from "../lib/apiClient";
import {
  archiveAlbumLimitBounds,
  archivePoolChipLimits,
  archivePoolSummary,
  clampArchiveAlbumLimit,
  clampTrackCount,
  defaultArchiveAlbumLimit,
  PLAYLIST_DEFAULT_TRACK_COUNT,
  PLAYLIST_TRACK_MAX,
  PLAYLIST_TRACK_MIN,
  PLAYLIST_TRACK_PRESETS,
  playlistSourceContextLine,
  trackCountHint,
} from "../lib/playlistForm";
import { exportPlaylist, loadArchiveRecommendations } from "../lib/plattenradarApi";
import type { TemporaryTasteProfile } from "../lib/plattenradarApi";
import {
  bumpPlaylistNameSuffix,
  defaultPlaylistNameForSource,
  downloadPlaylistContent,
  playlistItemsToTxt,
  playlistTxtFilename,
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
  const [entrySource] = useState(initialSource);
  const [source, setSource] = useState<RecommendationSource>(initialSource);
  const [updateRounds, setUpdateRounds] = useState(initialUpdateRounds);
  const [trackCount, setTrackCount] = useState(PLAYLIST_DEFAULT_TRACK_COUNT);
  const [customTrackCount, setCustomTrackCount] = useState(false);
  const [newestTasteFocus, setNewestTasteFocus] = useState(0.25);
  const [archiveDepth, setArchiveDepth] = useState(0.35);
  const [archivePoolSize, setArchivePoolSize] = useState<number | null>(null);
  const [archiveAlbumLimit, setArchiveAlbumLimit] = useState(200);
  const [archivePoolLoading, setArchivePoolLoading] = useState(false);
  const [name, setName] = useState(() => defaultPlaylistNameForSource(initialSource));
  const [nameTouched, setNameTouched] = useState(false);
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

  useEffect(() => {
    if (!nameTouched) {
      setName(defaultPlaylistNameForSource(source));
    }
  }, [nameTouched, source]);

  useEffect(() => {
    if (profile === null || source !== "entdecken") {
      return;
    }

    let cancelled = false;
    setArchivePoolLoading(true);

    void loadArchiveRecommendations(apiClient(), profile, { limit: 1, offset: 0 })
      .then(({ total }) => {
        if (cancelled) {
          return;
        }
        setArchivePoolSize(total);
        setArchiveAlbumLimit((current) =>
          clampArchiveAlbumLimit(total, defaultArchiveAlbumLimit(total) || current),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setArchivePoolSize(0);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setArchivePoolLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, profile, source]);

  const generatePlaylist = useCallback(
    async (nameOverride?: string) => {
      if (profile === null) {
        return;
      }

      const playlistName = nameOverride ?? name;

      setIsGenerating(true);
      setError(null);
      setCopyMessage(null);

      try {
        const result = await exportPlaylist(apiClient(), {
          source,
          profile,
          name: playlistName,
          targetCount: trackCount,
          newestTasteFocus,
          archiveDepth,
          archiveAlbumLimit,
          updateRounds,
          format: "csv",
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
    },
    [
      apiClient,
      archiveAlbumLimit,
      archiveDepth,
      name,
      newestTasteFocus,
      profile,
      source,
      trackCount,
      updateRounds,
    ],
  );

  const remixPlaylist = useCallback(() => {
    const nextName = bumpPlaylistNameSuffix(name);
    setName(nextName);
    setNameTouched(true);
    void generatePlaylist(nextName);
  }, [generatePlaylist, name]);

  const showEntryContext = source === entrySource;
  const archivePoolReady = archivePoolSize !== null && archivePoolSize > 0;
  const archiveChips =
    archivePoolSize === null ? [] : archivePoolChipLimits(archivePoolSize);
  const archiveBounds =
    archivePoolSize === null
      ? { min: 0, max: 0 }
      : archiveAlbumLimitBounds(archivePoolSize);
  const txtContent =
    exportResult === null || exportResult.items.length === 0
      ? ""
      : playlistItemsToTxt(exportResult.items);

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
          kannst du sie als CSV oder Text in deinen Musikdienst übertragen.
        </p>
      </header>

      <p className="playlist-profile-line">
        Basierend auf deinem Musikprofil.{" "}
        <button className="text-button" onClick={onEditProfile} type="button">
          Profil bearbeiten
        </button>
      </p>

      {showEntryContext && (
        <p className="playlist-entry-context">{playlistSourceContextLine(source, updateRounds)}</p>
      )}

      <div className="generator-card">
        <fieldset className="playlist-fieldset">
          <legend>Musik auswählen aus</legend>
          <div className="choice-grid choice-grid-broad playlist-mode-grid" role="group">
            <button
              className={`choice-card${source === "aktuell" ? " selected" : ""}`}
              onClick={() => {
                setSource("aktuell");
                setExportResult(null);
              }}
              type="button"
            >
              Neuheiten
              <small>Neueste Rezensionen</small>
            </button>
            <button
              className={`choice-card${source === "entdecken" ? " selected" : ""}`}
              onClick={() => {
                setSource("entdecken");
                setExportResult(null);
              }}
              type="button"
            >
              Archiv
              <small>Plattentests-Archiv</small>
            </button>
          </div>
        </fieldset>

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

        {source === "aktuell" && (
          <div className="playlist-fieldset">
            <span className="playlist-field-label">Fokus</span>
            <PlaylistDualSlider
              ariaLabel="Fokus oder Entdecken bei Neuheiten"
              leftLabel="Entdecken"
              onChange={setNewestTasteFocus}
              rightLabel="Fokus"
              value={newestTasteFocus}
            />
          </div>
        )}

        {source === "entdecken" && (
          <div className="playlist-fieldset">
            <span className="playlist-field-label">Top-Alben aus deinem Profil</span>
            {archivePoolLoading && (
              <p className="field-hint">Passende Alben werden geladen …</p>
            )}
            {!archivePoolLoading && archivePoolSize !== null && (
              <>
                <p className="playlist-pool-summary">
                  {archivePoolSummary(archivePoolSize, archiveAlbumLimit)}
                </p>
                {archivePoolReady && (
                  <>
                    <div className="filter-segmented playlist-pool-chips">
                      {archiveChips.map((chipValue) => (
                        <button
                          className={
                            archiveAlbumLimit === chipValue ? "selected" : undefined
                          }
                          key={chipValue}
                          onClick={() => {
                            setArchiveAlbumLimit(chipValue);
                          }}
                          type="button"
                        >
                          {chipValue >= archivePoolSize ? "Alle" : chipValue}
                        </button>
                      ))}
                    </div>
                    <input
                      aria-label="Wie viele Top-Alben"
                      className="playlist-dual-slider-input"
                      max={archiveBounds.max}
                      min={archiveBounds.min}
                      onChange={(event) => {
                        setArchiveAlbumLimit(
                          clampArchiveAlbumLimit(archivePoolSize, Number(event.target.value)),
                        );
                      }}
                      step={1}
                      type="range"
                      value={archiveAlbumLimit}
                    />
                  </>
                )}
              </>
            )}
          </div>
        )}

        {source === "entdecken" && archivePoolReady && (
          <div className="playlist-fieldset">
            <span className="playlist-field-label">Titel pro Album</span>
            <PlaylistDualSlider
              ariaLabel="Breit streuen oder Alben vertiefen"
              leftLabel="Breit streuen"
              onChange={setArchiveDepth}
              rightLabel="Alben vertiefen"
              value={archiveDepth}
            />
          </div>
        )}

        <fieldset className="playlist-fieldset">
          <legend>Anzahl Tracks</legend>
          <div className="filter-segmented">
            {PLAYLIST_TRACK_PRESETS.map((preset) => (
              <button
                className={
                  !customTrackCount && trackCount === preset ? "selected" : undefined
                }
                key={preset}
                onClick={() => {
                  setCustomTrackCount(false);
                  setTrackCount(preset);
                }}
                type="button"
              >
                {preset}
              </button>
            ))}
            <button
              className={customTrackCount ? "selected" : undefined}
              onClick={() => {
                setCustomTrackCount(true);
              }}
              type="button"
            >
              Eigene
            </button>
          </div>
          {customTrackCount ? (
            <label>
              Eigene Anzahl
              <input
                max={PLAYLIST_TRACK_MAX}
                min={PLAYLIST_TRACK_MIN}
                onChange={(event) => {
                  setTrackCount(clampTrackCount(Number(event.target.value)));
                }}
                type="number"
                value={trackCount}
              />
              <span className="field-hint">
                Zwischen {PLAYLIST_TRACK_MIN} und {PLAYLIST_TRACK_MAX} Titeln.
              </span>
            </label>
          ) : (
            <p className="field-hint">{trackCountHint(trackCount)}</p>
          )}
        </fieldset>

        <label>
          Playlist-Name
          <input
            onChange={(event) => {
              setNameTouched(true);
              setName(event.target.value);
            }}
            type="text"
            value={name}
          />
        </label>
        <button
          className="primary-button"
          disabled={
            isGenerating || (source === "entdecken" && (!archivePoolReady || archivePoolLoading))
          }
          onClick={() => void generatePlaylist()}
          type="button"
        >
          {isGenerating ? "Playlist wird erzeugt …" : "Playlist vorbereiten"}
        </button>
        {exportResult === null && (
          <p className="playlist-export-hint">
            Export über TuneMyMusic — Anleitung und Download erscheinen nach der Generierung.
          </p>
        )}
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
          <div className="playlist-results-head">
            <div className="playlist-results-title">
              <h2>{exportResult.name}</h2>
              {exportResult.items.length < trackCount && (
                <p className="playlist-warning">
                  Es wurden {exportResult.items.length} von {trackCount} gewünschten Titeln
                  gefunden (wenige eindeutige Tracks im Pool).
                </p>
              )}
            </div>
            {exportResult.items.length > 0 && (
              <div className="playlist-export-bar playlist-actions">
                <button
                  className="primary-button"
                  onClick={() =>
                    downloadPlaylistContent(
                      exportResult.filename,
                      exportResult.content,
                      exportResult.content_type,
                    )
                  }
                  type="button"
                >
                  Als CSV herunterladen
                </button>
                <button
                  className="secondary-button"
                  disabled={isGenerating}
                  onClick={() => remixPlaylist()}
                  type="button"
                >
                  {isGenerating ? "Wird gemischt …" : "Nochmal mischen"}
                </button>
                <button
                  className="secondary-button"
                  onClick={() => {
                    void navigator.clipboard.writeText(txtContent).then(() => {
                      setCopyMessage("Text in die Zwischenablage kopiert.");
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
                      playlistTxtFilename(exportResult.filename),
                      txtContent,
                      "text/plain;charset=utf-8",
                    )
                  }
                  type="button"
                >
                  Als TXT herunterladen
                </button>
              </div>
            )}
          </div>
          {copyMessage !== null && <p className="field-hint">{copyMessage}</p>}
          {exportResult.items.length === 0 ? (
            <p>
              Es konnten keine Playlist-Vorschläge erzeugt werden. Bitte Pool oder
              Einstellungen prüfen.
            </p>
          ) : (
            <>
              <PlaylistTrackList items={exportResult.items} />
              <TuneMyMusicGuide txtContent={txtContent} />
            </>
          )}
        </div>
      )}
    </section>
  );
}
