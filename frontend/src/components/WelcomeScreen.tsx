import type { ReactElement } from "react";

interface WelcomeScreenProps {
  onLoginClick: () => void;
  onStartSetup: () => void;
}

export function WelcomeScreen({
  onLoginClick,
  onStartSetup,
}: WelcomeScreenProps): ReactElement {
  return (
    <section className="welcome-screen">
      <div className="welcome-copy">
        <p className="eyebrow">Willkommen bei Plattenradar</p>
        <h1>Wie viele Alben würden dir gefallen, wenn du sie nur kennen würdest?</h1>
        <p>
          plattentests.de rezensiert seit 1999 Alben aus allen Ecken der
          Musikwelt. Plattenradar nimmt diesen Kosmos als Ausgangspunkt und
          hilft dir, die Platten zu finden, die zu deinem Musikprofil passen:
          alte Fundstücke, neue Rezensionen und Musik, die sonst leicht unter
          dem Radar bleibt.
        </p>
        <p className="welcome-bridge">
          Der schnellste Weg dorthin ist ein kurzes Musikprofil. Wenn du schon
          eines gespeichert hast, kannst du direkt weiterhören.
        </p>
        <div className="welcome-actions">
          <button className="primary-button" onClick={onStartSetup} type="button">
            Musikprofil erstellen
          </button>
          <button className="ghost-button" onClick={onLoginClick} type="button">
            Ich habe schon ein Profil
          </button>
        </div>
      </div>
    </section>
  );
}
