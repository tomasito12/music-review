import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import type { ProfileEntryContext, ProfilePageView } from "../lib/profilePageEntry";
import { resolveMusikprofilView } from "../lib/profilePageEntry";
import type { ProfileReturnRoute, ProfileSetupMode } from "../lib/profileReturnNavigation";
import type { ProfileSetupResult } from "../lib/profileSessionStorage";
import type { SetupStep } from "../lib/profileWizard";
import type { TemporaryTasteProfile } from "../lib/plattenradarApi";

import { ProfileOverviewPage } from "./ProfileOverviewPage";
import { ProfileSetupShell } from "./ProfileSetupShell";

interface ProfilePageProps {
  hasSavedProfileReference: boolean;
  hasUnsavedProfileChanges: boolean;
  isAuthenticated: boolean;
  isSubmitting: boolean;
  onFinishSetup: (result: ProfileSetupResult) => void;
  onOpenLogin: () => void;
  onReturnToOverview: (result: ProfileSetupResult) => void;
  onShowRecommendations: () => void;
  profileEditStep: SetupStep | undefined;
  profileReturnRoute: ProfileReturnRoute | null;
  profileSession: ProfileSetupResult | null;
  profileSetupMode: ProfileSetupMode;
  profileWizardContext: ProfileEntryContext | null;
  setProfileEditStep: (step: SetupStep | undefined) => void;
  setProfileWizardContext: (context: ProfileEntryContext | null) => void;
  temporaryProfile: TemporaryTasteProfile | null;
}

export function ProfilePage({
  hasSavedProfileReference,
  hasUnsavedProfileChanges,
  isAuthenticated,
  isSubmitting,
  onFinishSetup,
  onOpenLogin,
  onReturnToOverview,
  onShowRecommendations,
  profileEditStep,
  profileReturnRoute,
  profileSession,
  profileSetupMode,
  profileWizardContext,
  setProfileEditStep,
  setProfileWizardContext,
  temporaryProfile,
}: ProfilePageProps): ReactElement {
  const [pageView, setPageView] = useState<ProfilePageView>(() =>
    resolveMusikprofilView({
      hasProfile: temporaryProfile !== null,
      setupMode: profileSetupMode,
      editStep: profileEditStep,
    }),
  );

  useEffect(() => {
    setPageView(
      resolveMusikprofilView({
        hasProfile: temporaryProfile !== null,
        setupMode: profileSetupMode,
        editStep: profileEditStep,
      }),
    );
  }, [profileEditStep, profileSetupMode, temporaryProfile]);

  if (temporaryProfile === null || profileSession === null) {
    return (
      <ProfileSetupShell
        entryContext="initial"
        hasReturnRoute={false}
        initialPresetId={profileSession?.presetId}
        initialProfile={temporaryProfile}
        initialStep={profileEditStep}
        isSubmitting={isSubmitting}
        onFinish={onFinishSetup}
        onReturnToOverview={onReturnToOverview}
      />
    );
  }

  if (pageView === "overview") {
    return (
      <ProfileOverviewPage
        hasSavedProfileReference={hasSavedProfileReference}
        hasUnsavedProfileChanges={hasUnsavedProfileChanges}
        isAuthenticated={isAuthenticated}
        onEditStep={(step) => {
          setProfileWizardContext("overview");
          setProfileEditStep(step);
          setPageView("wizard");
        }}
        onOpenLogin={onOpenLogin}
        onShowRecommendations={onShowRecommendations}
        profileSession={profileSession}
      />
    );
  }

  const entryContext =
    profileSetupMode === "initial"
      ? "initial"
      : profileWizardContext ?? (profileEditStep !== undefined ? "shortcut" : "overview");

  return (
    <ProfileSetupShell
      entryContext={entryContext}
      hasReturnRoute={profileReturnRoute !== null}
      initialPresetId={profileSession.presetId}
      initialProfile={temporaryProfile}
      initialStep={profileEditStep}
      isSubmitting={isSubmitting}
      onBackToOverview={() => {
        setProfileEditStep(undefined);
        setProfileWizardContext(null);
        setPageView("overview");
      }}
      onFinish={onFinishSetup}
      onReturnToOverview={onReturnToOverview}
    />
  );
}
