import { useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";

import { AuthDialog } from "./components/AuthDialog";
import { AppShell } from "./components/AppShell";
import { PlaylistGenerator } from "./components/PlaylistGenerator";
import { ProfileSetupShell } from "./components/ProfileSetupShell";
import { RecommendationList } from "./components/RecommendationList";
import { WelcomeScreen } from "./components/WelcomeScreen";
import {
  aktuellHighlights,
  aktuellRecommendations,
  aktuellSummary,
} from "./data/mockRecommendations";
import { ApiClient } from "./lib/apiClient";
import { loadArchiveRecommendations } from "./lib/plattenradarApi";
import { routeFromPath } from "./lib/routes";
import type { TemporaryTasteProfile } from "./lib/plattenradarApi";
import type {
  AppRoute,
  Recommendation,
  RecommendationSource,
  UserState,
} from "./types";

export function App(): ReactElement {
  const [route, setRoute] = useState<AppRoute>(() =>
    routeFromPath(window.location.pathname),
  );
  const [userState, setUserState] = useState<UserState>("anonymous_no_profile");
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "save-profile">("login");
  const [playlistSource, setPlaylistSource] =
    useState<RecommendationSource>("aktuell");
  const [temporaryProfile, setTemporaryProfile] =
    useState<TemporaryTasteProfile | null>(null);
  const [archiveRecommendations, setArchiveRecommendations] = useState<
    Recommendation[] | null
  >(null);
  const [archiveTotal, setArchiveTotal] = useState(0);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  const pageTitle = useMemo(() => {
    switch (route) {
      case "aktuell":
        return "Aktuell";
      case "entdecken":
        return "Entdecken";
      case "playlists":
        return "Playlists";
      case "musikprofil":
        return "Musikprofil";
      case "konto":
        return "Konto";
      case "willkommen":
        return "Willkommen";
    }
  }, [route]);

  useEffect(() => {
    document.title = `Plattenradar - ${pageTitle}`;
  }, [pageTitle]);

  function navigate(nextRoute: AppRoute): void {
    setRoute(nextRoute);
    window.history.pushState({}, "", nextRoute === "willkommen" ? "/" : `/${nextRoute}`);
  }

  function createPlaylist(source: RecommendationSource): void {
    setPlaylistSource(source);
    navigate("playlists");
  }

  function openLogin(): void {
    setAuthMode("login");
    setAuthOpen(true);
  }

  async function finishSetup(profile: TemporaryTasteProfile): Promise<void> {
    setUserState("anonymous_temporary_profile");
    setTemporaryProfile(profile);
    setArchiveLoading(true);
    setArchiveError(null);
    navigate("entdecken");
    try {
      const result = await loadArchiveRecommendations(new ApiClient(), profile);
      setArchiveRecommendations(result.recommendations);
      setArchiveTotal(result.total);
    } catch {
      setArchiveRecommendations(null);
      setArchiveError(
        "Die Archivempfehlungen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
      );
    } finally {
      setArchiveLoading(false);
    }
  }

  return (
    <AppShell
      activeRoute={route}
      onLoginClick={openLogin}
      onNavigate={navigate}
      userState={userState}
    >
      {route === "willkommen" && (
        <WelcomeScreen
          onLoginClick={openLogin}
          onStartSetup={() => navigate("musikprofil")}
        />
      )}
      {route === "aktuell" && (
        <RecommendationList
          message="Wähle, wie viele der letzten Update-Runden du einbeziehen möchtest. Plattenradar sortiert den aktuellen Schwung danach, was am besten zu deinem Musikprofil passt."
          onCreatePlaylist={createPlaylist}
          highlights={aktuellHighlights}
          recommendations={aktuellRecommendations}
          source="aktuell"
          title="Neue Rezensionen für dich"
          updateSummary={aktuellSummary}
        />
      )}
      {route === "entdecken" && (
        <ArchiveDiscoverPage
          error={archiveError}
          isLoading={archiveLoading}
          onCreatePlaylist={createPlaylist}
          onEditProfile={() => navigate("musikprofil")}
          profileExists={temporaryProfile !== null}
          recommendations={archiveRecommendations}
          total={archiveTotal}
        />
      )}
      {route === "playlists" && (
        <PlaylistGenerator initialSource={playlistSource} />
      )}
      {route === "musikprofil" && (
        <ProfileSetupShell isSubmitting={archiveLoading} onFinish={finishSetup} />
      )}
      {route === "konto" && (
        <section className="account-page">
          <p className="eyebrow">Konto</p>
          <h1>Dein Plattenradar-Konto</h1>
          <p>
            Die Kontoansicht ist im ersten Shell-Schritt reserviert. Hier landen
            E-Mail, Logout, Passwort ändern und Konto löschen.
          </p>
          <button className="secondary-button" type="button">
            Abmelden
          </button>
        </section>
      )}
      {authOpen && (
        <AuthDialog mode={authMode} onClose={() => setAuthOpen(false)} />
      )}
    </AppShell>
  );
}

interface ArchiveDiscoverPageProps {
  error: string | null;
  isLoading: boolean;
  onCreatePlaylist: (source: RecommendationSource) => void;
  onEditProfile: () => void;
  profileExists: boolean;
  recommendations: Recommendation[] | null;
  total: number;
}

function ArchiveDiscoverPage({
  error,
  isLoading,
  onCreatePlaylist,
  onEditProfile,
  profileExists,
  recommendations,
  total,
}: ArchiveDiscoverPageProps): ReactElement {
  if (!profileExists) {
    return (
      <section className="empty-results">
        <p className="eyebrow">Entdecken</p>
        <h1>Dein Archiv wartet auf dein Musikprofil</h1>
        <p>Wähle zuerst ein paar Stilrichtungen, damit die Auswahl zu dir passt.</p>
        <button className="primary-button" onClick={onEditProfile} type="button">
          Musikprofil erstellen
        </button>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="empty-results">
        <p className="eyebrow">Entdecken</p>
        <h1>Das Archiv wird für dich durchsucht</h1>
      </section>
    );
  }

  if (error !== null) {
    return (
      <section className="empty-results">
        <p className="eyebrow">Entdecken</p>
        <h1>Das Archiv ist gerade nicht erreichbar</h1>
        <p>{error}</p>
        <button className="secondary-button" onClick={onEditProfile} type="button">
          Musikprofil anpassen
        </button>
      </section>
    );
  }

  return (
    <RecommendationList
      message={`${total} Alben aus dem Plattentests-Archiv passen zu deinen aktuellen Einstellungen.`}
      onCreatePlaylist={onCreatePlaylist}
      recommendations={recommendations ?? []}
      source="entdecken"
      title="Im Archiv entdecken"
    />
  );
}
