import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";

import { AuthDialog } from "./components/AuthDialog";
import { AppShell } from "./components/AppShell";
import { PlaylistGenerator } from "./components/PlaylistGenerator";
import { ProfilePage } from "./components/ProfilePage";
import { RecommendationList } from "./components/RecommendationList";
import { SaveProfileConfirmation } from "./components/SaveProfileConfirmation";
import { SaveProfilePrompt } from "./components/SaveProfilePrompt";
import { WelcomeScreen } from "./components/WelcomeScreen";
import {
  buildAktuellBriefing,
  buildAktuellHighlights,
  newestCountFromUpdateRounds,
  UPDATE_ROUND_OPTIONS,
} from "./lib/aktuellPage";
import { buildEntdeckenHeaderMessage } from "./lib/entdeckenPage";
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
  saveTasteProfile,
} from "./lib/plattenradarApi";
import {
  cloneTasteProfile,
  tasteProfilesMatch,
} from "./lib/profileComparison";
import type { ProfileSetupResult } from "./lib/profileSessionStorage";
import {
  buildFilterSummaryChips,
  readProfileSession,
  writeProfileSession,
} from "./lib/profileSessionStorage";
import type { SetupStep } from "./lib/profileWizard";
import type { ProfileEntryContext } from "./lib/profilePageEntry";
import {
  resolveInitialRoute,
  shouldLandOnAktuell,
  syncBrowserPath,
} from "./lib/initialRoute";
import type {
  ProfileReturnRoute,
  ProfileSetupMode,
} from "./lib/profileReturnNavigation";
import {
  resolveProfileFinishRoute,
  startInitialProfileSetup,
  startProfileEdit,
} from "./lib/profileReturnNavigation";
import {
  buildProfileSessionFromPreset,
  buildUpdatedProfileSession,
  type ProfileSessionUpdate,
} from "./lib/resultProfileUpdate";
import { useResultsFilterOptions } from "./lib/useResultsFilterOptions";
import { resolveProfileSaveBannerState } from "./lib/unsavedProfileBanner";
import type { TasteFilterSettings, TastePreset, TemporaryTasteProfile } from "./lib/plattenradarApi";
import type {
  AppRoute,
  Recommendation,
  RecommendationSource,
  UserState,
} from "./types";

export function App(): ReactElement {
  const [route, setRoute] = useState<AppRoute>(() => {
    const initialRoute = resolveInitialRoute(window.location.pathname);
    syncBrowserPath(initialRoute);
    return initialRoute;
  });
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
  const [profileSetupMode, setProfileSetupMode] =
    useState<ProfileSetupMode>("initial");
  const [profileReturnRoute, setProfileReturnRoute] =
    useState<ProfileReturnRoute | null>(null);
  const [profileWizardContext, setProfileWizardContext] =
    useState<ProfileEntryContext | null>(null);
  const [archiveRecommendations, setArchiveRecommendations] = useState<
    Recommendation[] | null
  >(null);
  const [archiveTotal, setArchiveTotal] = useState(0);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveLoadingMore, setArchiveLoadingMore] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);
  const [archiveReloadToken, setArchiveReloadToken] = useState(0);
  const [updateRounds, setUpdateRounds] = useState("4");
  const [aktuellRecommendations, setAktuellRecommendations] = useState<
    Recommendation[] | null
  >(null);
  const [aktuellTotal, setAktuellTotal] = useState(0);
  const [aktuellLoading, setAktuellLoading] = useState(false);
  const [aktuellLoadingMore, setAktuellLoadingMore] = useState(false);
  const [aktuellError, setAktuellError] = useState<string | null>(null);
  const [aktuellReloadToken, setAktuellReloadToken] = useState(0);
  const [lastSavedProfile, setLastSavedProfile] = useState<TemporaryTasteProfile | null>(
    null,
  );
  const [isSavingProfileChanges, setIsSavingProfileChanges] = useState(false);
  const [profileChangesSavedMessage, setProfileChangesSavedMessage] = useState<
    string | null
  >(null);
  const [profileChangesError, setProfileChangesError] = useState<string | null>(null);
  const lastArchiveReloadTokenHandled = useRef(-1);
  const lastAktuellReloadTokenHandled = useRef(-1);

  const temporaryProfile = profileSession?.profile ?? null;
  const isAuthenticated = authSession !== null;
  const hasUnsavedProfileChanges =
    isAuthenticated &&
    temporaryProfile !== null &&
    lastSavedProfile !== null &&
    !tasteProfilesMatch(temporaryProfile, lastSavedProfile);

  const profileSaveBanner = resolveProfileSaveBannerState({
    isAuthenticated,
    hasUnsavedProfileChanges,
    isSavingProfileChanges,
    savedMessage: profileChangesSavedMessage,
    errorMessage: profileChangesError,
  });

  const resultsFilterOptionsEnabled =
    (route === "aktuell" || route === "entdecken") && temporaryProfile !== null;
  const resultsFilterOptions = useResultsFilterOptions(resultsFilterOptionsEnabled);

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
          setLastSavedProfile(cloneTasteProfile(savedProfile));
        } else {
          setLastSavedProfile(null);
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

  useEffect(() => {
    if (authSession === null) {
      return;
    }
    if (hasUnsavedProfileChanges) {
      setUserState("authenticated_unsaved_changes");
      return;
    }
    if (lastSavedProfile !== null) {
      setUserState("authenticated_saved_profile");
      return;
    }
    setUserState("authenticated_no_profile");
  }, [authSession, hasUnsavedProfileChanges, lastSavedProfile]);

  useEffect(() => {
    if (
      shouldLandOnAktuell(
        route,
        authSession !== null,
        lastSavedProfile !== null,
      )
    ) {
      navigate("aktuell");
    }
  }, [authSession, lastSavedProfile, route]);

  useEffect(() => {
    if (profileChangesSavedMessage === null) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setProfileChangesSavedMessage(null);
    }, 3000);
    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [profileChangesSavedMessage]);

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
    if (archiveReloadToken === lastArchiveReloadTokenHandled.current) {
      return;
    }

    let active = true;
    setArchiveLoading(true);
    setArchiveError(null);

    void loadArchivePage(temporaryProfile, 0, "replace")
      .then(() => {
        if (!active) {
          return;
        }
        lastArchiveReloadTokenHandled.current = archiveReloadToken;
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setArchiveError(
          "Die Archivempfehlungen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
        );
      })
      .finally(() => {
        if (active) {
          setArchiveLoading(false);
        }
      });

    return () => {
      active = false;
      setArchiveLoading(false);
    };
  }, [archiveReloadToken, loadArchivePage, route, temporaryProfile]);

  useEffect(() => {
    if (route !== "aktuell" || temporaryProfile === null) {
      return;
    }
    if (aktuellReloadToken === lastAktuellReloadTokenHandled.current) {
      return;
    }

    let active = true;
    setAktuellLoading(true);
    setAktuellError(null);

    void loadAktuellPage(0, "replace")
      .then(() => {
        if (!active) {
          return;
        }
        lastAktuellReloadTokenHandled.current = aktuellReloadToken;
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setAktuellError(
          "Die neuen Rezensionen konnten gerade nicht geladen werden. Bitte versuche es noch einmal.",
        );
      })
      .finally(() => {
        if (active) {
          setAktuellLoading(false);
        }
      });

    return () => {
      active = false;
      setAktuellLoading(false);
    };
  }, [aktuellReloadToken, loadAktuellPage, route, temporaryProfile]);

  function invalidateRecommendationResults(): void {
    setArchiveReloadToken((token) => token + 1);
    setAktuellReloadToken((token) => token + 1);
    setArchiveError(null);
    setAktuellError(null);
  }

  function setAppRoute(nextRoute: AppRoute): void {
    setRoute(nextRoute);
    window.history.pushState({}, "", nextRoute === "willkommen" ? "/" : `/${nextRoute}`);
  }

  function navigate(nextRoute: AppRoute): void {
    if (nextRoute === "musikprofil" && route !== "musikprofil") {
      const editState = startProfileEdit(route, profileReturnRoute);
      setProfileSetupMode(editState.mode);
      setProfileReturnRoute(editState.returnRoute);
      setProfileEditStep(undefined);
      setProfileWizardContext(null);
    }
    setAppRoute(nextRoute);
  }

  function openInitialProfileSetup(): void {
    const setupState = startInitialProfileSetup();
    setProfileSetupMode(setupState.mode);
    setProfileReturnRoute(setupState.returnRoute);
    setProfileEditStep(undefined);
    setProfileWizardContext(null);
    setAppRoute("musikprofil");
  }

  function openProfileEditor(step?: SetupStep): void {
    const editState = startProfileEdit(route, profileReturnRoute);
    setProfileSetupMode(editState.mode);
    setProfileReturnRoute(editState.returnRoute);
    setProfileWizardContext("shortcut");
    setProfileEditStep(step);
    setAppRoute("musikprofil");
  }

  function showRecommendations(): void {
    navigate(
      isAuthenticated && lastSavedProfile !== null ? "aktuell" : "entdecken",
    );
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
      if (temporaryProfile !== null) {
        setLastSavedProfile(cloneTasteProfile(temporaryProfile));
      }
      setProfileSavedNotice(true);
      return;
    }

    const client = new ApiClient({ token: session.accessToken });
    void fetchSavedTasteProfile(client)
      .then((savedProfile) => {
        if (savedProfile === null) {
          setLastSavedProfile(null);
          if (temporaryProfile !== null) {
            navigate("aktuell");
          }
          return;
        }
        const restoredSession: ProfileSetupResult = {
          presetId: "saved",
          presetLabel: "Gespeichertes Profil",
          profile: savedProfile,
        };
        writeProfileSession(restoredSession);
        setProfileSession(restoredSession);
        setLastSavedProfile(cloneTasteProfile(savedProfile));
        navigate("aktuell");
      })
      .catch(() => {
        setLastSavedProfile(null);
      });
  }

  async function saveProfileChanges(): Promise<void> {
    if (authSession === null || temporaryProfile === null) {
      return;
    }
    setIsSavingProfileChanges(true);
    setProfileChangesError(null);
    setProfileChangesSavedMessage(null);
    try {
      const savedProfile = await saveTasteProfile(apiClient(), temporaryProfile);
      setLastSavedProfile(cloneTasteProfile(savedProfile));
      const updatedSession: ProfileSetupResult = {
        presetId: profileSession?.presetId ?? "saved",
        presetLabel: profileSession?.presetLabel ?? "Gespeichertes Profil",
        profile: savedProfile,
      };
      writeProfileSession(updatedSession);
      setProfileSession(updatedSession);
      setProfileChangesSavedMessage("Gespeichert.");
    } catch {
      setProfileChangesError(
        "Deine Änderungen konnten gerade nicht gespeichert werden. Bitte versuche es noch einmal.",
      );
    } finally {
      setIsSavingProfileChanges(false);
    }
  }

  function discardProfileChanges(): void {
    if (lastSavedProfile === null) {
      return;
    }
    const restoredSession: ProfileSetupResult = {
      presetId: "saved",
      presetLabel: "Gespeichertes Profil",
      profile: cloneTasteProfile(lastSavedProfile),
    };
    writeProfileSession(restoredSession);
    setProfileSession(restoredSession);
    setProfileChangesError(null);
    setProfileChangesSavedMessage(null);
    invalidateRecommendationResults();
  }

  function handleDismissSavePrompt(): void {
    dismissSavePrompt();
    setSavePromptHidden(true);
  }

  function logout(): void {
    clearAuthSession();
    setAuthSession(null);
    setLastSavedProfile(null);
    setProfileSavedNotice(false);
    setProfileChangesSavedMessage(null);
    setProfileChangesError(null);
    setUserState(
      profileSession !== null ? "anonymous_temporary_profile" : "anonymous_no_profile",
    );
    navigate("willkommen");
  }

  function applyProfileToOverview(result: ProfileSetupResult): void {
    const previousProfile = temporaryProfile;
    writeProfileSession(result);
    setProfileSession(result);
    setProfileEditStep(undefined);
    setProfileWizardContext(null);
    setProfileSavedNotice(false);
    if (!isAuthenticated) {
      setUserState("anonymous_temporary_profile");
    }
    if (
      previousProfile !== null &&
      !tasteProfilesMatch(previousProfile, result.profile)
    ) {
      invalidateRecommendationResults();
    }
  }

  async function finishSetup(result: ProfileSetupResult): Promise<void> {
    const previousProfile = temporaryProfile;
    writeProfileSession(result);
    setProfileSession(result);
    setProfileEditStep(undefined);
    setProfileWizardContext(null);
    setProfileSavedNotice(false);
    if (!isAuthenticated) {
      setUserState("anonymous_temporary_profile");
    }
    if (
      previousProfile === null ||
      !tasteProfilesMatch(previousProfile, result.profile)
    ) {
      invalidateRecommendationResults();
    }
    const destination = resolveProfileFinishRoute({
      mode: profileSetupMode,
      returnRoute: profileReturnRoute,
      isAuthenticated,
    });
    setProfileSetupMode("initial");
    setProfileReturnRoute(null);
    navigate(destination);
  }

  function applyResultProfileUpdate(update: ProfileSessionUpdate): void {
    if (profileSession === null) {
      return;
    }
    const next = buildUpdatedProfileSession(profileSession, update);
    writeProfileSession(next);
    setProfileSession(next);
    invalidateRecommendationResults();
  }

  function handleResultPresetSelect(preset: TastePreset): void {
    if (profileSession === null) {
      return;
    }
    const next = buildProfileSessionFromPreset(profileSession, preset);
    writeProfileSession(next);
    setProfileSession(next);
    invalidateRecommendationResults();
  }

  function handleResultFilterSettingsChange(settings: TasteFilterSettings): void {
    applyResultProfileUpdate({ filterSettings: settings });
  }

  function handleResultCommunityWeightsChange(
    weights: Record<string, number>,
  ): void {
    applyResultProfileUpdate({ communityWeightsRaw: weights });
  }

  function openProfileOverview(): void {
    navigate("musikprofil");
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
    setAktuellReloadToken((token) => token + 1);
    setAktuellError(null);
  }

  function editProfile(): void {
    openProfileEditor();
  }

  function retryArchiveLoad(): void {
    setArchiveError(null);
    setArchiveRecommendations(null);
    setArchiveReloadToken((token) => token + 1);
  }

  function retryAktuellLoad(): void {
    setAktuellError(null);
    setAktuellRecommendations(null);
    setAktuellReloadToken((token) => token + 1);
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
      onDiscardProfileChanges={discardProfileChanges}
      onSaveProfileChanges={() => {
        void saveProfileChanges();
      }}
      profileSaveBanner={profileSaveBanner}
      userEmail={authSession?.email ?? null}
      userState={userState}
    >
      {route === "willkommen" && (
        <WelcomeScreen
          onLoginClick={openLogin}
          onStartSetup={openInitialProfileSetup}
        />
      )}
      {route === "aktuell" && (
        <AktuellDiscoverPage
          canLoadMore={canLoadMoreAktuell}
          error={aktuellError}
          filterCommunities={resultsFilterOptions.communities}
          filterError={resultsFilterOptions.error}
          filterLoading={resultsFilterOptions.loading}
          filterPresets={resultsFilterOptions.presets}
          filterSummary={aktuellFilterSummary}
          hasSavedProfileReference={lastSavedProfile !== null}
          highlights={
            aktuellRecommendations !== null
              ? buildAktuellHighlights(aktuellRecommendations)
              : []
          }
          isAuthenticated={isAuthenticated}
          isLoading={aktuellLoading}
          isLoadingMore={aktuellLoadingMore}
          isReloading={aktuellLoading && aktuellRecommendations !== null}
          onCreatePlaylist={createPlaylist}
          onEditProfile={editProfile}
          onFilterCommunityWeightsChange={handleResultCommunityWeightsChange}
          onFilterSettingsChange={handleResultFilterSettingsChange}
          onLoadMore={loadMoreAktuellRecommendations}
          onOpenProfileOverview={openProfileOverview}
          onPresetSelect={handleResultPresetSelect}
          onRetry={retryAktuellLoad}
          onUpdateRoundsChange={handleUpdateRoundsChange}
          profileExists={temporaryProfile !== null}
          profileSession={profileSession}
          recommendations={aktuellRecommendations}
          total={aktuellTotal}
          updateRounds={updateRounds}
        />
      )}
      {route === "entdecken" && (
        <ArchiveDiscoverPage
          canLoadMore={canLoadMoreArchive}
          error={archiveError}
          filterCommunities={resultsFilterOptions.communities}
          filterError={resultsFilterOptions.error}
          filterLoading={resultsFilterOptions.loading}
          filterPresets={resultsFilterOptions.presets}
          filterSummary={archiveFilterSummary}
          hasSavedProfileReference={lastSavedProfile !== null}
          isAuthenticated={isAuthenticated}
          isLoading={archiveLoading}
          isLoadingMore={archiveLoadingMore}
          isReloading={archiveLoading && archiveRecommendations !== null}
          onCreatePlaylist={createPlaylist}
          onEditProfile={editProfile}
          onFilterCommunityWeightsChange={handleResultCommunityWeightsChange}
          onFilterSettingsChange={handleResultFilterSettingsChange}
          onLoadMore={loadMoreArchiveRecommendations}
          onOpenProfileOverview={openProfileOverview}
          onPresetSelect={handleResultPresetSelect}
          onRetry={retryArchiveLoad}
          profileExists={temporaryProfile !== null}
          profileSession={profileSession}
          recommendations={archiveRecommendations}
          savePrompt={savePromptSlot}
          total={archiveTotal}
        />
      )}
      {route === "playlists" && (
        <PlaylistGenerator
          apiClient={apiClient}
          initialSource={playlistSource}
          onEditProfile={editProfile}
          profile={temporaryProfile}
          updateRounds={updateRounds}
        />
      )}
      {route === "musikprofil" && (
        <ProfilePage
          hasSavedProfileReference={lastSavedProfile !== null}
          hasUnsavedProfileChanges={hasUnsavedProfileChanges}
          isAuthenticated={isAuthenticated}
          isSubmitting={false}
          onFinishSetup={finishSetup}
          onOpenLogin={openLogin}
          onReturnToOverview={applyProfileToOverview}
          onShowRecommendations={showRecommendations}
          profileEditStep={profileEditStep}
          profileReturnRoute={profileReturnRoute}
          profileSession={profileSession}
          profileSetupMode={profileSetupMode}
          profileWizardContext={profileWizardContext}
          setProfileEditStep={setProfileEditStep}
          setProfileWizardContext={setProfileWizardContext}
          temporaryProfile={temporaryProfile}
        />
      )}
      {route === "konto" && (
        <section className="account-page page-shell">
          <header className="page-header">
            <p className="eyebrow">Konto</p>
            <h1>Dein Plattenradar-Konto</h1>
          </header>
          <div className="account-card">
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
          </div>
        </section>
      )}
      {authOpen && (
        <AuthDialog
          lockMode
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
  filterCommunities: ReturnType<typeof useResultsFilterOptions>["communities"];
  filterError: string | null;
  filterLoading: boolean;
  filterPresets: ReturnType<typeof useResultsFilterOptions>["presets"];
  filterSummary?: string[];
  hasSavedProfileReference: boolean;
  highlights: ReturnType<typeof buildAktuellHighlights>;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  isReloading: boolean;
  onCreatePlaylist: (source: RecommendationSource) => void;
  onEditProfile: () => void;
  onFilterCommunityWeightsChange: (weights: Record<string, number>) => void;
  onFilterSettingsChange: (settings: TasteFilterSettings) => void;
  onLoadMore: () => void;
  onOpenProfileOverview: () => void;
  onPresetSelect: (preset: TastePreset) => void;
  onRetry: () => void;
  onUpdateRoundsChange: (value: string) => void;
  profileExists: boolean;
  profileSession: ProfileSetupResult | null;
  recommendations: Recommendation[] | null;
  total: number;
  updateRounds: string;
}

function AktuellDiscoverPage({
  canLoadMore,
  error,
  filterCommunities,
  filterError,
  filterLoading,
  filterPresets,
  filterSummary,
  hasSavedProfileReference,
  highlights,
  isAuthenticated,
  isLoading,
  isLoadingMore,
  isReloading,
  onCreatePlaylist,
  onEditProfile,
  onFilterCommunityWeightsChange,
  onFilterSettingsChange,
  onLoadMore,
  onOpenProfileOverview,
  onPresetSelect,
  onRetry,
  onUpdateRoundsChange,
  profileExists,
  profileSession,
  recommendations,
  total,
  updateRounds,
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

  if (isLoading && recommendations === null && !isReloading) {
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
        <button className="primary-button" onClick={onRetry} type="button">
          Erneut versuchen
        </button>
        <button className="secondary-button" onClick={onEditProfile} type="button">
          Musikprofil anpassen
        </button>
      </section>
    );
  }

  const loadedCount = recommendations?.length ?? 0;
  const updateRoundLabel =
    UPDATE_ROUND_OPTIONS.find((option) => option.value === updateRounds)?.label ??
    "Gewählter Zeitraum";
  const aktuellBriefing = buildAktuellBriefing(total, loadedCount, updateRoundLabel);

  return (
    <>
      {error !== null && recommendations !== null && (
        <p className="form-error archive-inline-error">{error}</p>
      )}
      <RecommendationList
        aktuellBriefing={aktuellBriefing}
        canLoadMore={canLoadMore}
        filterCommunities={filterCommunities}
        filterError={filterError}
        filterLoading={filterLoading}
        filterPresets={filterPresets}
        filterSummary={filterSummary}
        hasSavedProfileReference={hasSavedProfileReference}
        highlights={highlights}
        isAuthenticated={isAuthenticated}
        isReloading={isReloading}
        loadingMore={isLoadingMore}
        message={`${total} neue Rezensionen im gewählten Zeitraum. ${loadedCount} werden gerade angezeigt.`}
        onCreatePlaylist={onCreatePlaylist}
        onEditProfile={onOpenProfileOverview}
        onFilterCommunityWeightsChange={onFilterCommunityWeightsChange}
        onFilterSettingsChange={onFilterSettingsChange}
        onLoadMore={onLoadMore}
        onPresetSelect={onPresetSelect}
        onUpdateRoundsChange={onUpdateRoundsChange}
        profileSession={profileSession}
        recommendations={recommendations ?? []}
        source="aktuell"
        title="Neue Rezensionen für dich"
        updateRoundOptions={UPDATE_ROUND_OPTIONS}
        updateRounds={updateRounds}
      />
    </>
  );
}

interface ArchiveDiscoverPageProps {
  canLoadMore: boolean;
  error: string | null;
  filterCommunities: ReturnType<typeof useResultsFilterOptions>["communities"];
  filterError: string | null;
  filterLoading: boolean;
  filterPresets: ReturnType<typeof useResultsFilterOptions>["presets"];
  filterSummary?: string[];
  hasSavedProfileReference: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  isReloading: boolean;
  onCreatePlaylist: (source: RecommendationSource) => void;
  onEditProfile: () => void;
  onFilterCommunityWeightsChange: (weights: Record<string, number>) => void;
  onFilterSettingsChange: (settings: TasteFilterSettings) => void;
  onLoadMore: () => void;
  onOpenProfileOverview: () => void;
  onPresetSelect: (preset: TastePreset) => void;
  onRetry: () => void;
  profileExists: boolean;
  profileSession: ProfileSetupResult | null;
  recommendations: Recommendation[] | null;
  savePrompt: ReactElement | null;
  total: number;
}

function ArchiveDiscoverPage({
  canLoadMore,
  error,
  filterCommunities,
  filterError,
  filterLoading,
  filterPresets,
  filterSummary,
  hasSavedProfileReference,
  isAuthenticated,
  isLoading,
  isLoadingMore,
  isReloading,
  onCreatePlaylist,
  onEditProfile,
  onFilterCommunityWeightsChange,
  onFilterSettingsChange,
  onLoadMore,
  onOpenProfileOverview,
  onPresetSelect,
  onRetry,
  profileExists,
  profileSession,
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

  if (isLoading && recommendations === null && !isReloading) {
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
        <button className="primary-button" onClick={onRetry} type="button">
          Erneut versuchen
        </button>
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
        filterCommunities={filterCommunities}
        filterError={filterError}
        filterLoading={filterLoading}
        filterPresets={filterPresets}
        filterSummary={filterSummary}
        hasSavedProfileReference={hasSavedProfileReference}
        isAuthenticated={isAuthenticated}
        isReloading={isReloading}
        loadingMore={isLoadingMore}
        message={buildEntdeckenHeaderMessage(total, loadedCount)}
        onCreatePlaylist={onCreatePlaylist}
        onEditProfile={onOpenProfileOverview}
        onFilterCommunityWeightsChange={onFilterCommunityWeightsChange}
        onFilterSettingsChange={onFilterSettingsChange}
        onLoadMore={onLoadMore}
        onPresetSelect={onPresetSelect}
        profileSession={profileSession}
        recommendations={recommendations ?? []}
        savePrompt={savePrompt}
        source="entdecken"
        title="Im Archiv entdecken"
      />
    </>
  );
}
