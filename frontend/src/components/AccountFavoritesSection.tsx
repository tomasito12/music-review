import type { ReactElement } from "react";

import type { SavedAlbum } from "../types";

import { SaveHeartButton } from "./SaveHeartButton";
import { useFavorites } from "../lib/favoritesContext";

interface AccountFavoritesSectionProps {
  isAuthenticated: boolean;
  onOpenLogin: () => void;
}

function sourceLabel(source: SavedAlbum["source"]): string | null {
  if (source === "aktuell") {
    return "Neuheiten";
  }
  if (source === "entdecken") {
    return "Entdecken";
  }
  return null;
}

function formatSavedAt(savedAt: string): string {
  const parsed = new Date(savedAt);
  if (Number.isNaN(parsed.getTime())) {
    return savedAt;
  }
  return parsed.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** Lists saved albums on the account page. */
export function AccountFavoritesSection({
  isAuthenticated,
  onOpenLogin,
}: AccountFavoritesSectionProps): ReactElement {
  const { favorites, isLoading, isToggling, removeSavedAlbum } = useFavorites();

  return (
    <section className="account-favorites" aria-labelledby="account-favorites-title">
      <header className="account-favorites-header">
        <h2 id="account-favorites-title">Gemerkte Alben</h2>
        {!isAuthenticated && favorites.length > 0 && (
          <p className="account-favorites-hint">
            Diese Merkungen sind nur in diesem Browser gespeichert. Melde dich an,
            damit nichts verloren geht.
          </p>
        )}
      </header>

      {isLoading ? (
        <p className="account-favorites-status" role="status">
          Merkliste wird geladen ...
        </p>
      ) : favorites.length === 0 ? (
        <p className="account-favorites-empty">
          Noch nichts vorgemerkt — stöbere bei Neuheiten oder Entdecken.
        </p>
      ) : (
        <ul className="account-favorites-list">
          {favorites.map((item) => {
            const badge = sourceLabel(item.source);
            return (
              <li className="account-favorite-item" key={item.reviewId}>
                <div className="account-favorite-copy">
                  <h3>
                    <a href={item.reviewUrl} rel="noreferrer" target="_blank">
                      {item.artist} — {item.album}
                    </a>
                  </h3>
                  <p className="account-favorite-meta">
                    Gemerkt am {formatSavedAt(item.savedAt)}
                    {badge !== null ? ` · ${badge}` : ""}
                  </p>
                </div>
                <div className="account-favorite-actions">
                  <a
                    className="secondary-button account-favorite-open"
                    href={item.reviewUrl}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Rezension öffnen
                  </a>
                  <SaveHeartButton
                    className="card-save-heart account-favorite-remove"
                    isSaved
                    isToggling={isToggling(item.reviewId)}
                    onToggle={() => {
                      void removeSavedAlbum(item.reviewId);
                    }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {!isAuthenticated && (
        <button className="primary-button account-favorites-login" onClick={onOpenLogin} type="button">
          Einloggen
        </button>
      )}
    </section>
  );
}
