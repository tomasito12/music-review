import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import { ApiClient } from "../lib/apiClient";
import { buildProfileOverviewSummary } from "../lib/profileOverviewSummary";
import { loadTasteCommunities } from "../lib/plattenradarApi";
import type { TasteCommunityOption } from "../lib/plattenradarApi";
import type { ProfileSetupResult } from "../lib/profileSessionStorage";
import type { SetupStep } from "../lib/profileWizard";

interface ProfileOverviewPageProps {
  hasSavedProfileReference: boolean;
  hasUnsavedProfileChanges: boolean;
  isAuthenticated: boolean;
  profileSession: ProfileSetupResult;
  onEditStep: (step: SetupStep) => void;
  onOpenLogin: () => void;
  onShowRecommendations: () => void;
}

export function ProfileOverviewPage({
  hasSavedProfileReference,
  hasUnsavedProfileChanges,
  isAuthenticated,
  profileSession,
  onEditStep,
  onOpenLogin,
  onShowRecommendations,
}: ProfileOverviewPageProps): ReactElement {
  const [communities, setCommunities] = useState<TasteCommunityOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadCommunities(): Promise<void> {
      try {
        const options = await loadTasteCommunities(new ApiClient());
        if (!active) {
          return;
        }
        setCommunities(options);
        setError(null);
      } catch {
        if (active) {
          setError(
            "Die Profilübersicht konnte gerade nicht geladen werden. Bitte versuche es noch einmal.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadCommunities();
    return () => {
      active = false;
    };
  }, []);

  const summary =
    communities.length > 0
      ? buildProfileOverviewSummary(profileSession, communities)
      : null;
  const statusLabel = hasUnsavedProfileChanges
    ? "Temporär angepasst"
    : hasSavedProfileReference
      ? "Gespeichertes Profil"
      : "Temporäres Profil";

  return (
    <section className="profile-overview">
      <header className="profile-overview-header">
        <p className="eyebrow">Musikprofil</p>
        <h1>Dein Musikprofil</h1>
        <p>
          Hier siehst du deine aktuellen Stil- und Filter-Einstellungen. Änderungen
          wirken zuerst auf deine Empfehlungen
          {isAuthenticated && hasSavedProfileReference
            ? "; speichern kannst du sie oben im Banner."
            : "."}
        </p>
        <p className="profile-overview-status">{statusLabel}</p>
      </header>

      {loading && <p className="field-hint">Profilübersicht wird geladen ...</p>}
      {error !== null && <p className="form-error">{error}</p>}

      {summary !== null && (
        <div className="profile-overview-grid">
          <article className="profile-overview-card">
            <h2>Stilrichtungen</h2>
            <p>{summary.broadCategoriesText}</p>
            <div className="profile-overview-card-actions">
              <button
                className="secondary-button"
                onClick={() => onEditStep("broad")}
                type="button"
              >
                Stilrichtungen bearbeiten
              </button>
            </div>
          </article>

          <article className="profile-overview-card">
            <h2>Detailstile</h2>
            <p>{summary.detailStylesText}</p>
            <div className="profile-overview-card-actions">
              <button
                className="secondary-button"
                onClick={() => onEditStep("details")}
                type="button"
              >
                Details bearbeiten
              </button>
            </div>
          </article>

          <article className="profile-overview-card">
            <h2>Filter und Gewichtung</h2>
            <p>{summary.presetLabel}</p>
            <div className="profile-overview-chips" aria-label="Aktuelle Filter">
              {summary.filterChips.map((chip) => (
                <span key={chip}>{chip}</span>
              ))}
            </div>
            <div className="profile-overview-card-actions">
              <button
                className="secondary-button"
                onClick={() => onEditStep("filters")}
                type="button"
              >
                Filter und Gewichtung bearbeiten
              </button>
            </div>
          </article>
        </div>
      )}

      <div className="profile-overview-footer">
        <button className="primary-button" onClick={onShowRecommendations} type="button">
          Empfehlungen anzeigen
        </button>
        {!isAuthenticated && (
          <p className="profile-overview-login-hint">
            Melde dich an, um dieses Profil dauerhaft zu speichern.{" "}
            <button className="link-button" onClick={onOpenLogin} type="button">
              Einloggen
            </button>
          </p>
        )}
      </div>
    </section>
  );
}
