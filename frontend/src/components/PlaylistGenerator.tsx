import { useState } from "react";
import type { ReactElement } from "react";

import type { PlaylistSettings, RecommendationSource } from "../types";

interface PlaylistGeneratorProps {
  initialSource: RecommendationSource;
}

export function PlaylistGenerator({
  initialSource,
}: PlaylistGeneratorProps): ReactElement {
  const [source, setSource] = useState<RecommendationSource>(initialSource);
  const settings: PlaylistSettings = {
    source,
    trackCount: 30,
    focus: "balanced",
    variation: 0.35,
    name: `Plattenradar ${new Date().toISOString().slice(0, 10)}`,
  };

  return (
    <section className="playlist-page">
      <p className="eyebrow">Playlists</p>
      <h1>Neue Playlist erzeugen</h1>
      <p>
        Stelle die Playlist passend zu deinem Hörmoment zusammen. Anschließend
        kannst du sie als Text, TXT oder CSV in deinen Musikdienst übertragen.
      </p>
      <div className="generator-card">
        <label>
          Musik auswählen aus
          <select
            onChange={(event) => setSource(event.target.value as RecommendationSource)}
            value={source}
          >
            <option value="aktuell">Den letzten Updates</option>
            <option value="entdecken">Dem Plattentests-Archiv</option>
          </select>
        </label>
        {source === "aktuell" && (
          <label>
            Zeitraum
            <select defaultValue="4">
              <option value="1">Der letzten Update-Runde</option>
              <option value="4">Den letzten 4 Update-Runden</option>
              <option value="8">Den letzten 8 Update-Runden</option>
            </select>
          </label>
        )}
        <label>
          Anzahl Tracks
          <input defaultValue={settings.trackCount} min="5" step="5" type="number" />
        </label>
        <label>
          Fokus
          <select defaultValue={settings.focus}>
            <option value="balanced">Breit über die Liste</option>
            <option value="top">Stärker auf Top-Treffer</option>
          </select>
        </label>
        {source === "entdecken" && (
          <label>
            Abwechslung
            <input
              aria-label="Abwechslung in der Archiv-Playlist"
              defaultValue={settings.variation}
              max="1"
              min="0"
              step="0.05"
              type="range"
            />
            <span className="field-hint">
              Mehr Abwechslung verteilt die Auswahl stärker über die Rangliste.
            </span>
          </label>
        )}
        <label>
          Playlist-Name
          <input defaultValue={settings.name} type="text" />
        </label>
        <button className="primary-button" type="button">
          Playlist vorbereiten
        </button>
      </div>
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
