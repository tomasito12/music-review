import type { ReactElement } from "react";

import { TUNEMYMUSIC_FILE_UPLOAD_URL, TUNEMYMUSIC_URL } from "../../lib/playlistExport";

interface TuneMyMusicGuideProps {
  /** When true, freetext is shown as an alternative import path. */
  showFreetextAlternative?: boolean;
  txtContent: string;
}

/** TuneMyMusic import steps shown open after playlist generation. */
export function TuneMyMusicGuide({
  showFreetextAlternative = true,
  txtContent,
}: TuneMyMusicGuideProps): ReactElement {
  return (
    <section aria-label="TuneMyMusic Import" className="playlist-tunemymusic-guide">
      <h3 className="playlist-tunemymusic-heading">In deinen Musikdienst importieren</h3>
      <p className="field-hint playlist-tunemymusic-lead">
        Empfohlen: CSV herunterladen und bei TuneMyMusic als Datei hochladen.
      </p>
      <ol className="playlist-tunemymusic-steps">
        <li>
          <a href={TUNEMYMUSIC_FILE_UPLOAD_URL} rel="noreferrer" target="_blank">
            TuneMyMusic öffnen
          </a>{" "}
          (Datei hochladen).
        </li>
        <li>Die heruntergeladene CSV-Datei auswählen.</li>
        <li>Deinen Streamingdienst verbinden und den Transfer starten.</li>
      </ol>
      <p className="field-hint">
        Alternativ:{" "}
        <a href={TUNEMYMUSIC_URL} rel="noreferrer" target="_blank">
          TuneMyMusic Startseite
        </a>{" "}
        und Freitext-Import nutzen.
      </p>
      {showFreetextAlternative && txtContent.length > 0 && (
        <details className="playlist-tunemymusic-freetext">
          <summary>Freitext-Alternative (TuneMyMusic)</summary>
          <label>
            Zeilen zum Einfügen
            <textarea readOnly rows={8} value={txtContent} />
          </label>
        </details>
      )}
    </section>
  );
}
