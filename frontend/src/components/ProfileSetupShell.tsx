import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import { ApiClient } from "../lib/apiClient";
import {
  createTemporaryTasteProfile,
  loadTasteCommunities,
} from "../lib/plattenradarApi";
import type {
  TasteCommunityOption,
  TemporaryTasteProfile,
} from "../lib/plattenradarApi";

type SetupStep = "broad" | "details";

interface ProfileSetupShellProps {
  isSubmitting: boolean;
  onFinish: (profile: TemporaryTasteProfile) => void;
}

export function ProfileSetupShell({
  isSubmitting,
  onFinish,
}: ProfileSetupShellProps): ReactElement {
  const [communities, setCommunities] = useState<TasteCommunityOption[]>([]);
  const [selectedBroadCategories, setSelectedBroadCategories] = useState<
    string[]
  >([]);
  const [selectedCommunityIds, setSelectedCommunityIds] = useState<string[]>([]);
  const [step, setStep] = useState<SetupStep>("broad");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const broadCategories = Array.from(
    new Set(
      communities.flatMap((community) => community.broad_categories).filter(Boolean),
    ),
  ).sort((left, right) => left.localeCompare(right, "de"));

  const availableCommunities = communities.filter((community) =>
    community.broad_categories.some((category) =>
      selectedBroadCategories.includes(category),
    ),
  );

  useEffect(() => {
    let active = true;

    async function loadOptions(): Promise<void> {
      try {
        const options = await loadTasteCommunities(new ApiClient());
        if (active) {
          setCommunities(options);
          setError(null);
        }
      } catch {
        if (active) {
          setError("Die Stilrichtungen konnten gerade nicht geladen werden.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadOptions();
    return () => {
      active = false;
    };
  }, []);

  function toggleBroadCategory(category: string): void {
    setSelectedBroadCategories((current) => {
      const next = current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category];
      const allowedCommunityIds = new Set(
        communities
          .filter((community) =>
            community.broad_categories.some((broadCategory) =>
              next.includes(broadCategory),
            ),
          )
          .map((community) => community.id),
      );
      setSelectedCommunityIds((selected) =>
        selected.filter((communityId) => allowedCommunityIds.has(communityId)),
      );
      return next;
    });
  }

  function toggleCommunity(communityId: string): void {
    setSelectedCommunityIds((current) =>
      current.includes(communityId)
        ? current.filter((id) => id !== communityId)
        : [...current, communityId],
    );
  }

  function useExampleProfile(): void {
    const exampleIds = communities.slice(0, 3).map((community) => community.id);
    onFinish(createTemporaryTasteProfile(exampleIds));
  }

  function continueWithSelection(): void {
    if (step === "broad") {
      setStep("details");
      return;
    }
    onFinish(createTemporaryTasteProfile(selectedCommunityIds));
  }

  const canContinue =
    step === "broad"
      ? selectedBroadCategories.length > 0
      : selectedCommunityIds.length > 0;

  return (
    <section className="setup-shell">
      <div className="setup-progress" aria-label="Musikprofil Fortschritt">
        <span className={step === "broad" ? "active" : ""}>1 Richtungen</span>
        <span className={step === "details" ? "active" : ""}>2 Details</span>
        <span>3 Filter</span>
      </div>
      <div className="setup-grid">
        <div className="setup-panel">
          <p className="eyebrow">Musikprofil</p>
          {step === "broad" ? (
            <>
              <h1>Welche groben Richtungen passen zu dir?</h1>
              <p>
                Wähle zuerst die musikalischen Bereiche, aus denen Plattenradar
                passende Detailstile vorschlagen soll.
              </p>
              <div className="choice-grid">
                {broadCategories.map((category) => (
                  <button
                    aria-pressed={selectedBroadCategories.includes(category)}
                    className={`choice-card${
                      selectedBroadCategories.includes(category) ? " selected" : ""
                    }`}
                    key={category}
                    onClick={() => toggleBroadCategory(category)}
                    type="button"
                  >
                    {category}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <h1>Welche Detailstile sollen dein Profil prägen?</h1>
              <p>
                Diese Auswahl basiert auf deinen groben Richtungen. Du kannst
                zurückgehen, wenn du den Stilraum ändern möchtest.
              </p>
              <div className="choice-grid choice-grid-details">
                {availableCommunities.map((community) => (
                  <button
                    aria-pressed={selectedCommunityIds.includes(community.id)}
                    className={`choice-card${
                      selectedCommunityIds.includes(community.id) ? " selected" : ""
                    }`}
                    key={community.id}
                    onClick={() => toggleCommunity(community.id)}
                    type="button"
                  >
                    <span>{community.label}</span>
                    <small>{community.broad_categories.join(", ")}</small>
                  </button>
                ))}
              </div>
            </>
          )}
          {loading && <p className="field-hint">Stilrichtungen werden geladen ...</p>}
          {error !== null && <p className="form-error">{error}</p>}
          <div className="welcome-actions">
            {step === "details" && (
              <button
                className="secondary-button"
                disabled={isSubmitting}
                onClick={() => setStep("broad")}
                type="button"
              >
                Zurück
              </button>
            )}
            <button
              className="primary-button"
              disabled={!canContinue || isSubmitting}
              onClick={continueWithSelection}
              type="button"
            >
              {isSubmitting
                ? "Empfehlungen werden geladen ..."
                : step === "broad"
                  ? "Detailstile auswählen"
                  : "Empfehlungen anzeigen"}
            </button>
            <button
              className="ghost-button"
              disabled={communities.length === 0 || isSubmitting}
              onClick={useExampleProfile}
              type="button"
            >
              Beispielprofil verwenden
            </button>
          </div>
        </div>
        <aside className="setup-summary setup-summary-subtle">
          <h2>Dein Profil</h2>
          <p>Noch nicht gespeichert</p>
          <div className="setup-summary-section">
            <strong>Richtungen</strong>
            <span>
              {selectedBroadCategories.length > 0
                ? selectedBroadCategories.join(", ")
                : "Noch keine Auswahl"}
            </span>
          </div>
          <div className="setup-summary-section">
            <strong>Detailstile</strong>
            <span>
              {selectedCommunityIds.length > 0
                ? `${selectedCommunityIds.length} ausgewählt`
                : "Folgen im nächsten Schritt"}
            </span>
          </div>
          <ul>
            <li>Du kannst jederzeit zurück.</li>
            <li>Speichern bieten wir nach den ersten Empfehlungen an.</li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
