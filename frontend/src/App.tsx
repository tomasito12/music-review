import { useCallback, useEffect, useMemo, useState } from "react";
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
import {
  ARCHIVE_PAGE_SIZE,
  loadArchiveRecommendations,
} from "./lib/plattenradarApi";
import type { ProfileSetupResult } from "./lib/profileSessionStorage";
import {
  buildFilterSummaryChips,
  readProfileSession,
  writeProfileSession,
} from "./lib/profileSessionStorage";
import type { SetupStep } from "./lib/profileWizard";
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
  const [profileSession, setProfileSession] = useState<ProfileSetupResult | null>(
    () => readProfileSession(),
  );
  const [profileEditStep, setProfileEditStep] = useState<SetupStep | undefined>();
  const [archiveRecommendations, setArchiveRecommendations] = useState<
    Recommendation[] | null
  >(null);
  const [archiveTotal, setArchiveTotal] = useState(0);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveLoadingMore, setArchiveLoadingMore] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  const temporaryProfile = profileSession?.profile ?? null;

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

  useEffect(() => {
    if (profileSession !== null) {
      setUserState("anonymous_temporary_profile");
    }
  }, [profileSession]);

  const loadArchivePage = useCallback(
    async (
      profile: TemporaryTasteProfile,
      offset: number,
      mode: "replace" | "append",
    ): Promise<void> => {
      const client = new ApiClient();
      const result = await loadArchiveRecommendations(client, profile, {
        offset,
        limit: ARCHIVE_PAGE_SIZE,
      });
      setArchiveTotal(result.total);
      setArchiveRecommendations((current) =>
        mode === "append" && current !== null
          ? [...current, ...result.recommendations]
          : result.recommendations,
      );
    },
    [],
  );

  useEffect(() => {
    if (route !== "entdecken" || temporaryProfile === null) {
      return;
    }
    if (archiveRecommendations !== null || archiveLoading) {
      return;
    }

    let active = true;
    setArchiveLoading(true);
    setArchiveError(null);

    void loadArchivePage(temporaryProfile, 0, "replace")
      .catch(() => {
        if (active) {
          setArchiveRecommendations(null);
          setArchiveError(
            "Die Archivempfehlungen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setArchiveLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [
    archiveLoading,
    archiveRecommendations,
    loadArchivePage,
    route,
    temporaryProfile,
  ]);

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

  async function finishSetup(result: ProfileSetupResult): Promise<void> {
    writeProfileSession(result);
    setProfileSession(result);
    setProfileEditStep(undefined);
    setUserState("anonymous_temporary_profile");
    setArchiveRecommendations(null);
    setArchiveTotal(0);
    setArchiveLoading(true);
    setArchiveError(null);
    navigate("entdecken");
    try {
      await loadArchivePage(result.profile, 0, "replace");
    } catch {
      setArchiveRecommendations(null);
      setArchiveError(
        "Die Archivempfehlungen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
      );
    } finally {
      setArchiveLoading(false);
    }
  }

  async function loadMoreArchiveRecommendations(): Promise<void> {
    if (temporaryProfile === null || archiveRecommendations === null) {
      return;
    }
    if (archiveRecommendations.length >= archiveTotal) {
      return;
    }
    setArchiveLoadingMore(true);
    setArchiveError(null);
    try {
      await loadArchivePage(
        temporaryProfile,
        archiveRecommendations.length,
        "append",
      );
    } catch {
      setArchiveError(
        "Weitere Alben konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
      );
    } finally {
      setArchiveLoadingMore(false);
    }
  }

  function adjustFilters(): void {
    setProfileEditStep("filters");
    navigate("musikprofil");
  }

  function editProfile(): void {
    setProfileEditStep(undefined);
    navigate("musikprofil");
  }

  const archiveFilterSummary =
    profileSession !== null ? buildFilterSummaryChips(profileSession) : undefined;
  const canLoadMoreArchive =
    archiveRecommendations !== null && archiveRecommendations.length < archiveTotal;

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
          canLoadMore={canLoadMoreArchive}
          error={archiveError}
          filterSummary={archiveFilterSummary}
          isLoading={archiveLoading}
          isLoadingMore={archiveLoadingMore}
          onAdjustFilters={adjustFilters}
          onCreatePlaylist={createPlaylist}
          onEditProfile={editProfile}
          onLoadMore={loadMoreArchiveRecommendations}
          profileExists={temporaryProfile !== null}
          recommendations={archiveRecommendations}
          total={archiveTotal}
        />
      )}
      {route === "playlists" && (
        <PlaylistGenerator initialSource={playlistSource} />
      )}
      {route === "musikprofil" && (
        <ProfileSetupShell
          initialPresetId={profileSession?.presetId}
          initialProfile={temporaryProfile}
          initialStep={profileEditStep}
          isSubmitting={archiveLoading}
          onFinish={finishSetup}
        />
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
  canLoadMore: boolean;
  error: string | null;
  filterSummary?: string[];
  isLoading: boolean;
  isLoadingMore: boolean;
  onAdjustFilters: () => void;
  onCreatePlaylist: (source: RecommendationSource) => void;
  onEditProfile: () => void;
  onLoadMore: () => void;
  profileExists: boolean;
  recommendations: Recommendation[] | null;
  total: number;
}

function ArchiveDiscoverPage({
  canLoadMore,
  error,
  filterSummary,
  isLoading,
  isLoadingMore,
  onAdjustFilters,
  onCreatePlaylist,
  onEditProfile,
  onLoadMore,
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

  if (error !== null && recommendations === null) {
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

  const loadedCount = recommendations?.length ?? 0;

  return (
    <>
      {error !== null && recommendations !== null && (
        <p className="form-error archive-inline-error">{error}</p>
      )}
      <RecommendationList
        canLoadMore={canLoadMore}
        filterSummary={filterSummary}
        loadingMore={isLoadingMore}
        message={`${total} Alben passen zu deinen Einstellungen. ${loadedCount} werden gerade angezeigt.`}
        onAdjustFilters={onAdjustFilters}
        onCreatePlaylist={onCreatePlaylist}
        onLoadMore={onLoadMore}
        recommendations={recommendations ?? []}
        source="entdecken"
        title="Im Archiv entdecken"
      />
    </>
  );
}
