import type { ReactElement } from "react";

interface ProfileSetupShellProps {
  onFinish: () => void;
}

export function ProfileSetupShell({
  onFinish,
}: ProfileSetupShellProps): ReactElement {
  return (
    <section className="setup-shell">
      <div className="setup-progress" aria-label="Musikprofil Fortschritt">
        <span className="active">1 Stilrichtungen</span>
        <span>2 Details</span>
        <span>3 Filter</span>
      </div>
      <div className="setup-grid">
        <div className="setup-panel">
          <p className="eyebrow">Musikprofil</p>
          <h1>Welche Musikrichtungen hörst du gern?</h1>
          <p>
            Wähle zuerst die großen Stilrichtungen. Danach kannst du dein
            Profil mit feineren Stilen und passenden Filtern verfeinern.
          </p>
          <div className="choice-grid">
            {["Indie", "Rock", "Pop", "Elektronik", "Hip-Hop", "Folk"].map((item) => (
              <button className="choice-card" key={item} type="button">
                {item}
              </button>
            ))}
          </div>
          <button className="primary-button" onClick={onFinish} type="button">
            Beispielprofil verwenden
          </button>
        </div>
        <aside className="setup-summary setup-summary-subtle">
          <h2>Dein Profil</h2>
          <p>Noch nicht gespeichert</p>
          <ul>
            <li>Du kannst jederzeit zurück.</li>
            <li>Speichern bieten wir nach den ersten Empfehlungen an.</li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
