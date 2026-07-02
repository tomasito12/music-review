import type { ReactElement } from "react";

const TUNEMYMUSIC_URL = "https://www.tunemymusic.com";

interface TuneMyMusicGuideProps {
  txtContent: string;
}

/** Collapsible generic TuneMyMusic import steps shown after playlist generation. */
export function TuneMyMusicGuide({ txtContent }: TuneMyMusicGuideProps): ReactElement {
  return (
    <details className="playlist-tunemymusic-guide">
      <summary>In deinen Musikdienst importieren (TuneMyMusic)</summary>
      <ol className="playlist-tunemymusic-steps">
        <li>
          <a href={TUNEMYMUSIC_URL} rel="noreferrer" target="_blank">
            TuneMyMusic öffnen
          </a>
          .
        </li>
        <li>
          Als Quelle <strong>Datei hochladen</strong> (CSV) oder <strong>Freitext</strong>{" "}
          wählen.
        </li>
        <li>Deinen Streamingdienst verbinden und den Transfer starten.</li>
      </ol>
      {txtContent.length > 0 && (
        <label>
          Für TuneMyMusic (Freitext)
          <textarea readOnly rows={8} value={txtContent} />
        </label>
      )}
    </details>
  );
}
