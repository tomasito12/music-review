import { useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";

import { AuthDialog } from "./components/AuthDialog";
import { AppShell } from "./components/AppShell";
import { PlaylistGenerator } from "./components/PlaylistGenerator";
import { ProfileSetupShell } from "./components/ProfileSetupShell";
import { RecommendationList } from "./components/RecommendationList";
import { WelcomeScreen } from "./components/WelcomeScreen";
import {
  aktuellRecommendations,
  entdeckenRecommendations,
} from "./data/mockRecommendations";
import { routeFromPath } from "./lib/routes";
import type { AppRoute, RecommendationSource, UserState } from "./types";

export function App(): ReactElement {
  const [route, setRoute] = useState<AppRoute>(() =>
    routeFromPath(window.location.pathname),
  );
  const [userState, setUserState] = useState<UserState>("anonymous_no_profile");
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "save-profile">("login");
  const [playlistSource, setPlaylistSource] =
    useState<RecommendationSource>("aktuell");

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

  function finishSetup(): void {
    setUserState("anonymous_temporary_profile");
    navigate("entdecken");
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
          recommendations={aktuellRecommendations}
          source="aktuell"
          title="Neue Rezensionen für dich"
        />
      )}
      {route === "entdecken" && (
        <RecommendationList
          message="Das Archiv ist der große Fundus: Alben aus vielen Jahren plattentests.de, sortiert nach deiner Stilpassung und deinen Filtereinstellungen."
          onCreatePlaylist={createPlaylist}
          recommendations={entdeckenRecommendations}
          source="entdecken"
          title="Im Archiv entdecken"
        />
      )}
      {route === "playlists" && (
        <PlaylistGenerator initialSource={playlistSource} />
      )}
      {route === "musikprofil" && <ProfileSetupShell onFinish={finishSetup} />}
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
