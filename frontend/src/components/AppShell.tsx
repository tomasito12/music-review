import type { ReactElement, ReactNode } from "react";

import type { ProfileSaveBannerState } from "../lib/unsavedProfileBanner";
import type { AppRoute, UserState } from "../types";

import { UnsavedProfileBanner } from "./UnsavedProfileBanner";

interface AppShellProps {
  activeRoute: AppRoute;
  children: ReactNode;
  profileSaveBanner: ProfileSaveBannerState;
  onDiscardProfileChanges: () => void;
  onSaveProfileChanges: () => void;
  savedCount?: number;
  userEmail?: string | null;
  userState: UserState;
  onNavigate: (route: AppRoute) => void;
  onLoginClick: () => void;
}

const navItems: Array<{ route: AppRoute; label: string }> = [
  { route: "aktuell", label: "Aktuell" },
  { route: "entdecken", label: "Entdecken" },
  { route: "playlists", label: "Playlists" },
  { route: "musikprofil", label: "Musikprofil" },
];

export function AppShell({
  activeRoute,
  children,
  profileSaveBanner,
  onDiscardProfileChanges,
  onSaveProfileChanges,
  savedCount = 0,
  userEmail = null,
  userState,
  onNavigate,
  onLoginClick,
}: AppShellProps): ReactElement {
  const isLoggedIn = userState.startsWith("authenticated");

  return (
    <div className="app-shell">
      <div className="app-header">
        <header className="topbar">
          <button
            className="brand"
            onClick={() => onNavigate(isLoggedIn ? "aktuell" : "willkommen")}
            type="button"
          >
            <span className="brand-mark" aria-hidden="true">
              PR
            </span>
            <span>
              <strong>Plattenradar</strong>
              <small>Musik finden, die passt</small>
            </span>
          </button>

          <nav className="main-nav" aria-label="Hauptnavigation">
            {navItems.map((item) => (
              <button
                aria-current={activeRoute === item.route ? "page" : undefined}
                className="nav-link"
                key={item.route}
                onClick={() => onNavigate(item.route)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="account-slot">
            {isLoggedIn ? (
              <button
                className="account-button"
                onClick={() => onNavigate("konto")}
                type="button"
              >
                {userEmail ?? "Konto"}
                {savedCount > 0 ? (
                  <span className="account-button-badge" aria-label={`${savedCount} gemerkte Alben`}>
                    {savedCount}
                  </span>
                ) : null}
              </button>
            ) : savedCount > 0 ? (
              <button
                className="account-button"
                onClick={() => onNavigate("konto")}
                type="button"
              >
                Merkliste
                <span className="account-button-badge" aria-label={`${savedCount} gemerkte Alben`}>
                  {savedCount}
                </span>
              </button>
            ) : (
              <button className="account-button" onClick={onLoginClick} type="button">
                Einloggen
              </button>
            )}
          </div>
        </header>
        <UnsavedProfileBanner
          onDiscard={onDiscardProfileChanges}
          onSave={onSaveProfileChanges}
          state={profileSaveBanner}
        />
      </div>
      <main className="app-main">{children}</main>
    </div>
  );
}
