import type { ReactElement } from "react";

import type { PlaylistSettings, RecommendationSource } from "../types";

interface PlaylistGeneratorProps {
  initialSource: RecommendationSource;
}

export function PlaylistGenerator({
  initialSource,
}: PlaylistGeneratorProps): ReactElement {
  const settings: PlaylistSettings = {
    source: initialSource,
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
        Wähle kurz, wie stark die Playlist auf die besten Treffer fokussieren
        soll. Nach der Generierung bekommst du Text, TXT und CSV.
      </p>
      <div className="generator-card">
        <label>
          Quelle
          <select defaultValue={settings.source}>
            <option value="aktuell">Aktuell</option>
            <option value="entdecken">Entdecken</option>
          </select>
        </label>
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
        <label>
          Variation
          <input defaultValue={settings.variation} max="1" min="0" step="0.05" type="range" />
        </label>
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
