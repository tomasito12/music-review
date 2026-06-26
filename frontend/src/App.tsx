import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";

import { AuthDialog } from "./components/AuthDialog";
import { AppShell } from "./components/AppShell";
import { PlaylistGenerator } from "./components/PlaylistGenerator";
import { ProfileSetupShell } from "./components/ProfileSetupShell";
import { RecommendationList } from "./components/RecommendationList";
import { SaveProfileConfirmation } from "./components/SaveProfileConfirmation";
import { SaveProfilePrompt } from "./components/SaveProfilePrompt";
import { WelcomeScreen } from "./components/WelcomeScreen";
import {
  buildAktuellHighlights,
  buildAktuellSummary,
  newestCountFromUpdateRounds,
  UPDATE_ROUND_OPTIONS,
} from "./lib/aktuellPage";
import { ApiClient } from "./lib/apiClient";
import type { AuthSession } from "./lib/authSessionStorage";
import {
  clearAuthSession,
  dismissSavePrompt,
  isSavePromptDismissed,
  readAuthSession,
  writeAuthSession,
} from "./lib/authSessionStorage";
import {
  ARCHIVE_PAGE_SIZE,
  fetchCurrentUser,
  fetchSavedTasteProfile,
  loadArchiveRecommendations,
  loadNewReviewRecommendations,
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
  const [authSession, setAuthSession] = useState<AuthSession | null>(() =>
    readAuthSession(),
  );
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "save-profile">("login");
  const [savePromptHidden, setSavePromptHidden] = useState(() =>
    isSavePromptDismissed(),
  );
  const [profileSavedNotice, setProfileSavedNotice] = useState(false);
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
  const [updateRounds, setUpdateRounds] = useState("4");
  const [aktuellRecommendations, setAktuellRecommendations] = useState<
    Recommendation[] | null
  >(null);
  const [aktuellTotal, setAktuellTotal] = useState(0);
  const [aktuellLoading, setAktuellLoading] = useState(false);
  const [aktuellLoadingMore, setAktuellLoadingMore] = useState(false);
  const [aktuellError, setAktuellError] = useState<string | null>(null);

  const temporaryProfile = profileSession?.profile ?? null;
  const isAuthenticated = authSession !== null;

  const apiClient = useCallback(
    () => new ApiClient({ token: authSession?.accessToken }),
    [authSession],
  );

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
    const storedAuth = readAuthSession();
    if (storedAuth === null) {
      return;
    }

    let active = true;
    const client = new ApiClient({ token: storedAuth.accessToken });
    void fetchCurrentUser(client)
      .then(async (user) => {
        if (!active) {
          return;
        }
        const savedProfile = await fetchSavedTasteProfile(client);
        if (!active) {
          return;
        }
        setAuthSession({
          accessToken: storedAuth.accessToken,
          email: user.email,
        });
        if (savedProfile !== null) {
          const restoredSession: ProfileSetupResult = {
            presetId: "saved",
            presetLabel: "Gespeichertes Profil",
            profile: savedProfile,
          };
          writeProfileSession(restoredSession);
          setProfileSession(restoredSession);
          setUserState("authenticated_saved_profile");
        } else {
          setUserState("authenticated_no_profile");
        }
      })
      .catch(() => {
        if (active) {
          clearAuthSession();
          setAuthSession(null);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (authSession !== null) {
      return;
    }
    setUserState(
      profileSession !== null ? "anonymous_temporary_profile" : "anonymous_no_profile",
    );
  }, [authSession, profileSession]);

  const loadArchivePage = useCallback(
    async (
      profile: TemporaryTasteProfile,
      offset: number,
      mode: "replace" | "append",
    ): Promise<void> => {
      const result = await loadArchiveRecommendations(apiClient(), profile, {
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
    [apiClient],
  );

  const loadAktuellPage = useCallback(
    async (offset: number, mode: "replace" | "append"): Promise<void> => {
      const newestCount = newestCountFromUpdateRounds(Number(updateRounds));
      const result = await loadNewReviewRecommendations(
        apiClient(),
        temporaryProfile,
        {
          offset,
          limit: ARCHIVE_PAGE_SIZE,
          newestCount,
        },
      );
      setAktuellTotal(result.total);
      setAktuellRecommendations((current) =>
        mode === "append" && current !== null
          ? [...current, ...result.recommendations]
          : result.recommendations,
      );
    },
    [apiClient, temporaryProfile, updateRounds],
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

  useEffect(() => {
    if (route !== "aktuell" || temporaryProfile === null) {
      return;
    }
    if (aktuellRecommendations !== null || aktuellLoading) {
      return;
    }

    let active = true;
    setAktuellLoading(true);
    setAktuellError(null);

    void loadAktuellPage(0, "replace")
      .catch(() => {
        if (active) {
          setAktuellRecommendations(null);
          setAktuellError(
            "Die neuen Rezensionen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setAktuellLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [
    aktuellLoading,
    aktuellRecommendations,
    loadAktuellPage,
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

  function openSaveProfile(): void {
    setAuthMode("save-profile");
    setAuthOpen(true);
  }

  function handleAuthSuccess(session: AuthSession): void {
    writeAuthSession(session);
    setAuthSession(session);
    setAuthOpen(false);
    setSavePromptHidden(true);
    if (authMode === "save-profile") {
      setProfileSavedNotice(true);
      setUserState("authenticated_saved_profile");
      return;
    }

    const client = new ApiClient({ token: session.accessToken });
    void fetchSavedTasteProfile(client)
      .then((savedProfile) => {
        if (savedProfile === null) {
          setUserState("authenticated_no_profile");
          return;
        }
        const restoredSession: ProfileSetupResult = {
          presetId: "saved",
          presetLabel: "Gespeichertes Profil",
          profile: savedProfile,
        };
        writeProfileSession(restoredSession);
        setProfileSession(restoredSession);
        setUserState("authenticated_saved_profile");
      })
      .catch(() => {
        setUserState("authenticated_no_profile");
      });
  }

  function handleDismissSavePrompt(): void {
    dismissSavePrompt();
    setSavePromptHidden(true);
  }

  function logout(): void {
    clearAuthSession();
    setAuthSession(null);
    setProfileSavedNotice(false);
    setUserState(
      profileSession !== null ? "anonymous_temporary_profile" : "anonymous_no_profile",
    );
    navigate("willkommen");
  }

  async function finishSetup(result: ProfileSetupResult): Promise<void> {
    writeProfileSession(result);
    setProfileSession(result);
    setProfileEditStep(undefined);
    setProfileSavedNotice(false);
    if (!isAuthenticated) {
      setUserState("anonymous_temporary_profile");
    }
    setArchiveRecommendations(null);
    setArchiveTotal(0);
    setAktuellRecommendations(null);
    setAktuellTotal(0);
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

  async function loadMoreAktuellRecommendations(): Promise<void> {
    if (temporaryProfile === null || aktuellRecommendations === null) {
      return;
    }
    if (aktuellRecommendations.length >= aktuellTotal) {
      return;
    }
    setAktuellLoadingMore(true);
    setAktuellError(null);
    try {
      await loadAktuellPage(aktuellRecommendations.length, "append");
    } catch {
      setAktuellError(
        "Weitere Rezensionen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
      );
    } finally {
      setAktuellLoadingMore(false);
    }
  }

  function handleUpdateRoundsChange(value: string): void {
    setUpdateRounds(value);
    setAktuellRecommendations(null);
    setAktuellTotal(0);
    setAktuellError(null);
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
  const aktuellFilterSummary =
    profileSession !== null
      ? [
          ...buildFilterSummaryChips(profileSession),
          UPDATE_ROUND_OPTIONS.find((option) => option.value === updateRounds)
            ?.label ?? "",
        ]
      : undefined;
  const canLoadMoreArchive =
    archiveRecommendations !== null && archiveRecommendations.length < archiveTotal;
  const canLoadMoreAktuell =
    aktuellRecommendations !== null && aktuellRecommendations.length < aktuellTotal;
  const showSavePrompt =
    userState === "anonymous_temporary_profile" &&
    !savePromptHidden &&
    !profileSavedNotice &&
    archiveRecommendations !== null &&
    archiveRecommendations.length > 0;

  const savePromptSlot = profileSavedNotice && authSession !== null ? (
    <SaveProfileConfirmation
      email={authSession.email}
      onGoToAktuell={() => navigate("aktuell")}
    />
  ) : showSavePrompt ? (
    <SaveProfilePrompt
      onDismiss={handleDismissSavePrompt}
      onSave={openSaveProfile}
    />
  ) : null;

  return (
    <AppShell
      activeRoute={route}
      onLoginClick={openLogin}
      onNavigate={navigate}
      userEmail={authSession?.email ?? null}
      userState={userState}
    >
      {route === "willkommen" && (
        <WelcomeScreen
          onLoginClick={openLogin}
          onStartSetup={() => navigate("musikprofil")}
        />
      )}
      {route === "aktuell" && (
        <AktuellDiscoverPage
          canLoadMore={canLoadMoreAktuell}
          error={aktuellError}
          filterSummary={aktuellFilterSummary}
          highlights={
            aktuellRecommendations !== null
              ? buildAktuellHighlights(aktuellRecommendations)
              : []
          }
          isLoading={aktuellLoading}
          isLoadingMore={aktuellLoadingMore}
          onAdjustFilters={adjustFilters}
          onCreatePlaylist={createPlaylist}
          onEditProfile={editProfile}
          onLoadMore={loadMoreAktuellRecommendations}
          onUpdateRoundsChange={handleUpdateRoundsChange}
          profileExists={temporaryProfile !== null}
          recommendations={aktuellRecommendations}
          total={aktuellTotal}
          updateRounds={updateRounds}
          updateSummary={buildAktuellSummary(aktuellTotal)}
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
          savePrompt={savePromptSlot}
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
          {authSession !== null ? (
            <>
              <p>Angemeldet als {authSession.email}.</p>
              <button className="secondary-button" onClick={logout} type="button">
                Abmelden
              </button>
            </>
          ) : (
            <>
              <p>
                Melde dich an, um dein Musikprofil dauerhaft zu speichern und beim
                nächsten Besuch direkt weiterzumachen.
              </p>
              <button className="primary-button" onClick={openLogin} type="button">
                Einloggen
              </button>
            </>
          )}
        </section>
      )}
      {authOpen && (
        <AuthDialog
          mode={authMode}
          onClose={() => setAuthOpen(false)}
          onSuccess={handleAuthSuccess}
          onSwitchMode={setAuthMode}
          profileToSave={temporaryProfile}
        />
      )}
    </AppShell>
  );
}

interface AktuellDiscoverPageProps {
  canLoadMore: boolean;
  error: string | null;
  filterSummary?: string[];
  highlights: ReturnType<typeof buildAktuellHighlights>;
  isLoading: boolean;
  isLoadingMore: boolean;
  onAdjustFilters: () => void;
  onCreatePlaylist: (source: RecommendationSource) => void;
  onEditProfile: () => void;
  onLoadMore: () => void;
  onUpdateRoundsChange: (value: string) => void;
  profileExists: boolean;
  recommendations: Recommendation[] | null;
  total: number;
  updateRounds: string;
  updateSummary: ReturnType<typeof buildAktuellSummary>;
}

function AktuellDiscoverPage({
  canLoadMore,
  error,
  filterSummary,
  highlights,
  isLoading,
  isLoadingMore,
  onAdjustFilters,
  onCreatePlaylist,
  onEditProfile,
  onLoadMore,
  onUpdateRoundsChange,
  profileExists,
  recommendations,
  total,
  updateRounds,
  updateSummary,
}: AktuellDiscoverPageProps): ReactElement {
  if (!profileExists) {
    return (
      <section className="empty-results">
        <p className="eyebrow">Aktuell</p>
        <h1>Neue Rezensionen brauchen dein Musikprofil</h1>
        <p>
          Erstelle zuerst ein Profil, damit Plattenradar frische Rezensionen nach
          Passung sortieren kann.
        </p>
        <button className="primary-button" onClick={onEditProfile} type="button">
          Musikprofil erstellen
        </button>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="empty-results">
        <p className="eyebrow">Aktuell</p>
        <h1>Neue Rezensionen werden geladen</h1>
      </section>
    );
  }

  if (error !== null && recommendations === null) {
    return (
      <section className="empty-results">
        <p className="eyebrow">Aktuell</p>
        <h1>Neue Rezensionen sind gerade nicht erreichbar</h1>
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
        highlights={highlights}
        loadingMore={isLoadingMore}
        message={`${total} neue Rezensionen im gewählten Zeitraum. ${loadedCount} werden gerade angezeigt.`}
        onAdjustFilters={onAdjustFilters}
        onCreatePlaylist={onCreatePlaylist}
        onLoadMore={onLoadMore}
        onUpdateRoundsChange={onUpdateRoundsChange}
        recommendations={recommendations ?? []}
        source="aktuell"
        title="Neue Rezensionen für dich"
        updateRoundOptions={UPDATE_ROUND_OPTIONS}
        updateRounds={updateRounds}
        updateSummary={updateSummary}
      />
    </>
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
  savePrompt: ReactElement | null;
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
  savePrompt,
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
        savePrompt={savePrompt}
        source="entdecken"
        title="Im Archiv entdecken"
      />
    </>
  );
}
