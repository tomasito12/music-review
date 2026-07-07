import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactElement } from "react";

import { PlaylistDualSlider } from "./playlist/PlaylistDualSlider";
import { PlaylistTrackList } from "./playlist/PlaylistTrackList";
import { TuneMyMusicGuide } from "./playlist/TuneMyMusicGuide";
import type { ApiClient } from "../lib/apiClient";
import {
  archiveAlbumLimitBounds,
  archivePoolChipLabel,
  archivePoolChipLimits,
  archivePoolSummary,
  ARCHIVE_SPREAD_PRESETS,
  archiveSpreadHint,
  clampArchiveAlbumLimit,
  clampTrackCount,
  DEFAULT_ARCHIVE_SPREAD_PRESET,
  DEFAULT_NEWEST_MOOD_PRESET,
  defaultArchiveAlbumLimit,
  isNewestMoodPresetSelected,
  NEWEST_MOOD_PRESETS,
  newestMoodToTasteFocus,
  normalizePlaylistUpdateRounds,
  PLAYLIST_DEFAULT_TRACK_COUNT,
  PLAYLIST_TRACK_MAX,
  PLAYLIST_TRACK_MIN,
  PLAYLIST_TRACK_PRESETS,
  PLAYLIST_UPDATE_ROUND_OPTIONS,
  playlistSuccessHeadline,
  playlistUpdateRoundPoolHint,
  trackCountHint,
  type ArchiveSpreadPreset,
} from "../lib/playlistForm";
import { exportPlaylist, loadArchiveRecommendations } from "../lib/plattenradarApi";
import type { TemporaryTasteProfile } from "../lib/plattenradarApi";
import {
  defaultPlaylistNameForSource,
  downloadPlaylistContent,
  playlistItemsToCsv,
  playlistItemsToTxt,
  playlistNameForExportDownload,
  suggestedPlaylistExportFilename,
  TUNEMYMUSIC_FILE_UPLOAD_URL,
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
  const [updateRounds, setUpdateRounds] = useState(() =>
    normalizePlaylistUpdateRounds(initialUpdateRounds),
  );
  const [trackCount, setTrackCount] = useState(PLAYLIST_DEFAULT_TRACK_COUNT);
  const [customTrackCount, setCustomTrackCount] = useState(false);
  const [newestTasteFocus, setNewestTasteFocus] = useState(() =>
    newestMoodToTasteFocus(DEFAULT_NEWEST_MOOD_PRESET),
  );
  const [archiveSpread, setArchiveSpread] = useState<ArchiveSpreadPreset>(
    DEFAULT_ARCHIVE_SPREAD_PRESET,
  );
  const [archivePoolSize, setArchivePoolSize] = useState<number | null>(null);
  const [archiveAlbumLimit, setArchiveAlbumLimit] = useState(200);
  const [archivePoolLoading, setArchivePoolLoading] = useState(false);
  const [name, setName] = useState(() => defaultPlaylistNameForSource(initialSource));
  const [nameCustomized, setNameCustomized] = useState(false);
  const [exportDownloadCount, setExportDownloadCount] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<PlaylistExportResult | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [settingsExpanded, setSettingsExpanded] = useState(true);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSource(initialSource);
  }, [initialSource]);

  useEffect(() => {
    setUpdateRounds(normalizePlaylistUpdateRounds(initialUpdateRounds));
  }, [initialUpdateRounds]);

  useEffect(() => {
    if (!nameCustomized) {
      setName(defaultPlaylistNameForSource(source));
      setExportDownloadCount(0);
    }
  }, [nameCustomized, source]);

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

  useEffect(() => {
    if (exportResult === null) {
      return;
    }
    setSettingsExpanded(false);
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [exportResult]);

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
          archiveSpread,
          archiveAlbumLimit,
          updateRounds,
          format: "csv",
        });
        setExportResult(result);
        setExportDownloadCount(0);
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
      archiveSpread,
      name,
      newestTasteFocus,
      profile,
      source,
      trackCount,
      updateRounds,
    ],
  );

  const remixPlaylist = useCallback(() => {
    void generatePlaylist();
  }, [generatePlaylist]);

  const downloadCsvExport = useCallback(() => {
    if (exportResult === null) {
      return;
    }

    const exportName = playlistNameForExportDownload(name, exportDownloadCount + 1);
    downloadPlaylistContent(
      suggestedPlaylistExportFilename(exportName, ".csv"),
      playlistItemsToCsv(exportResult.items, exportName),
      exportResult.content_type,
    );
    setExportDownloadCount((current) => current + 1);
  }, [exportDownloadCount, exportResult, name]);

  const downloadCsvAndOpenTuneMyMusic = useCallback(() => {
    downloadCsvExport();
    window.open(TUNEMYMUSIC_FILE_UPLOAD_URL, "_blank", "noopener,noreferrer");
  }, [downloadCsvExport]);

  const downloadTxtExport = useCallback(() => {
    if (exportResult === null) {
      return;
    }

    const exportName = playlistNameForExportDownload(name, exportDownloadCount + 1);
    downloadPlaylistContent(
      suggestedPlaylistExportFilename(exportName, ".txt"),
      playlistItemsToTxt(exportResult.items),
      "text/plain;charset=utf-8",
    );
    setExportDownloadCount((current) => current + 1);
  }, [exportDownloadCount, exportResult, name]);

  const archivePoolReady = archivePoolSize !== null && archivePoolSize > 0;
  const archiveChips =
    archivePoolSize === null ? [] : archivePoolChipLimits(archivePoolSize);
  const archiveBoundsMax =
    archivePoolSize === null ? 0 : archivePoolChipLimits(archivePoolSize).at(-1) ?? 0;
  const archiveBounds =
    archivePoolSize === null
      ? { min: 0, max: 0 }
      : archiveAlbumLimitBounds(archivePoolSize);
  const txtContent =
    exportResult === null || exportResult.items.length === 0
      ? ""
      : playlistItemsToTxt(exportResult.items);
  const playlistVisualReady =
    exportResult !== null
      ? "results"
      : source === "entdecken" && (archivePoolLoading || !archivePoolReady)
        ? "pending"
        : "form";
  const showConfigureForm = exportResult === null || settingsExpanded;
  const hasResults = exportResult !== null;

  const configureForm = (
    <div className="generator-card">
      <fieldset className="playlist-fieldset">
        <legend>Musik auswählen aus</legend>
        <div className="choice-grid choice-grid-broad playlist-mode-grid" role="group">
          <button
            className={`choice-card${source === "aktuell" ? " selected" : ""}`}
            onClick={() => {
              setSource("aktuell");
              setExportResult(null);
              setSettingsExpanded(true);
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
              setSettingsExpanded(true);
            }}
            type="button"
          >
            Archiv
            <small>Plattentests-Archiv</small>
          </button>
        </div>
      </fieldset>

      {source === "aktuell" && (
        <fieldset className="playlist-fieldset">
          <legend>Zeitraum</legend>
          <div className="filter-segmented playlist-update-round-chips">
            {PLAYLIST_UPDATE_ROUND_OPTIONS.map((option) => (
              <button
                className={updateRounds === option.value ? "selected" : undefined}
                key={option.value}
                onClick={() => {
                  setUpdateRounds(option.value);
                }}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
          <p className="field-hint">{playlistUpdateRoundPoolHint(updateRounds)}</p>
        </fieldset>
      )}

      {source === "aktuell" && (
        <fieldset className="playlist-fieldset">
          <legend>Passung zum Musikprofil</legend>
          <div className="filter-segmented">
            {NEWEST_MOOD_PRESETS.map((preset) => (
              <button
                className={
                  isNewestMoodPresetSelected(newestTasteFocus, preset.id)
                    ? "selected"
                    : undefined
                }
                key={preset.id}
                onClick={() => {
                  setNewestTasteFocus(newestMoodToTasteFocus(preset.id));
                }}
                type="button"
              >
                {preset.label}
              </button>
            ))}
          </div>
          <p className="field-hint">
            {NEWEST_MOOD_PRESETS.find((preset) =>
              isNewestMoodPresetSelected(newestTasteFocus, preset.id),
            )?.hint ?? "Feinjustierung unter Erweitert."}
          </p>
        </fieldset>
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
                <div className="filter-segmented playlist-pool-chips">
                  {archiveChips.map((chipValue) => (
                    <button
                      className={archiveAlbumLimit === chipValue ? "selected" : undefined}
                      key={chipValue}
                      onClick={() => {
                        setArchiveAlbumLimit(chipValue);
                      }}
                      type="button"
                    >
                      {archivePoolChipLabel(chipValue, archivePoolSize, archiveBoundsMax)}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {source === "entdecken" && archivePoolReady && (
        <fieldset className="playlist-fieldset">
          <legend>Titel pro Album</legend>
          <div className="filter-segmented">
            {ARCHIVE_SPREAD_PRESETS.map((preset) => (
              <button
                className={archiveSpread === preset.id ? "selected" : undefined}
                key={preset.id}
                onClick={() => {
                  setArchiveSpread(preset.id);
                }}
                type="button"
              >
                {preset.label}
              </button>
            ))}
          </div>
          <p className="field-hint">{archiveSpreadHint(archiveSpread)}</p>
        </fieldset>
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

      <details className="playlist-advanced-options">
        <summary>Erweitert</summary>
        <label>
          Playlist-Name
          <input
            onChange={(event) => {
              setNameCustomized(true);
              setName(event.target.value);
            }}
            type="text"
            value={name}
          />
        </label>
        {source === "aktuell" && (
          <div className="playlist-fieldset">
            <span className="playlist-field-label">Passung fein einstellen</span>
            <PlaylistDualSlider
              ariaLabel="Feine Einstellung zwischen weiter weg und nah am Musikprofil"
              leftLabel="Weiter weg"
              onChange={setNewestTasteFocus}
              rightLabel="Nah am Profil"
              value={newestTasteFocus}
            />
          </div>
        )}
        {source === "entdecken" && archivePoolReady && (
          <div className="playlist-fieldset">
            <span className="playlist-field-label">Top-Alben genau wählen</span>
            <input
              aria-label="Wie viele Top-Alben"
              className="playlist-dual-slider-input"
              max={archiveBounds.max}
              min={archiveBounds.min}
              onChange={(event) => {
                if (archivePoolSize === null) {
                  return;
                }
                setArchiveAlbumLimit(
                  clampArchiveAlbumLimit(archivePoolSize, Number(event.target.value)),
                );
              }}
              step={1}
              type="range"
              value={archiveAlbumLimit}
            />
            <p className="field-hint">
              Zwischen {archiveBounds.min} und {archiveBounds.max} Top-Alben wählbar.
            </p>
          </div>
        )}
      </details>
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
      {!hasResults && (
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
  );

  if (profile === null) {
    return (
      <section className="playlist-page page-shell" data-visual-playlist-ready="gate">
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
    <section
      className="playlist-page page-shell"
      data-visual-playlist-ready={playlistVisualReady}
    >
      <header className="page-header">
        <p className="eyebrow">Playlists</p>
        <h1>Neue Playlist erzeugen</h1>
        {!hasResults && (
          <p>
            Stelle die Playlist passend zu deinem Hörmoment zusammen. Anschließend
            kannst du sie als CSV oder Text in deinen Musikdienst übertragen.
          </p>
        )}
      </header>

      <p className="playlist-profile-line">
        Basierend auf deinem Musikprofil.{" "}
        <button className="text-button" onClick={onEditProfile} type="button">
          Profil bearbeiten
        </button>
      </p>

      {hasResults && !settingsExpanded && (
        <button
          className="text-button playlist-settings-toggle"
          onClick={() => {
            setSettingsExpanded(true);
          }}
          type="button"
        >
          Einstellungen ändern
        </button>
      )}

      {showConfigureForm && configureForm}

      {exportResult !== null && (
        <div className="playlist-results" ref={resultsRef}>
          <header className="playlist-success-header">
            <p className="playlist-success-kicker">Nächster Schritt</p>
            <h2 className="playlist-success-title">
              {playlistSuccessHeadline(source, exportResult.items.length)}
            </h2>
            <p className="playlist-success-name">{name}</p>
            {exportResult.items.length < trackCount && (
              <p className="playlist-warning">
                Es wurden {exportResult.items.length} von {trackCount} gewünschten Titeln
                gefunden (wenige eindeutige Tracks im Pool).
              </p>
            )}
          </header>

          {exportResult.items.length > 0 && (
            <div className="playlist-result-actions">
              <section aria-label="Export" className="playlist-export-section">
                <button
                  className="primary-button playlist-export-primary"
                  onClick={downloadCsvAndOpenTuneMyMusic}
                  type="button"
                >
                  CSV herunterladen und TuneMyMusic öffnen
                </button>
                <p className="field-hint playlist-export-lead">
                  Empfohlen: CSV herunterladen und bei TuneMyMusic als Datei hochladen.
                </p>
                <div className="playlist-export-secondary">
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
                    onClick={downloadTxtExport}
                    type="button"
                  >
                    Als TXT herunterladen
                  </button>
                  <button
                    className="secondary-button"
                    onClick={downloadCsvExport}
                    type="button"
                  >
                    Nur CSV herunterladen
                  </button>
                </div>
              </section>

              <section aria-label="Neue Ziehung" className="playlist-remix-section">
                <button
                  className="secondary-button"
                  disabled={isGenerating}
                  onClick={() => remixPlaylist()}
                  type="button"
                >
                  {isGenerating ? "Wird gemischt …" : "Nochmal mischen"}
                </button>
                <p className="field-hint">Gleiche Einstellungen, neue Zufallsauswahl.</p>
              </section>
            </div>
          )}

          {copyMessage !== null && <p className="field-hint">{copyMessage}</p>}

          {exportResult.items.length === 0 ? (
            <p>
              Es konnten keine Playlist-Vorschläge erzeugt werden. Bitte Pool oder
              Einstellungen prüfen.
            </p>
          ) : (
            <>
              <TuneMyMusicGuide txtContent={txtContent} />
              <PlaylistTrackList items={exportResult.items} />
            </>
          )}
        </div>
      )}
    </section>
  );
}
