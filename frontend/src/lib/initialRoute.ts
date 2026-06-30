import { readAuthSession } from "./authSessionStorage";
import { readProfileSession } from "./profileSessionStorage";
import { pathForRoute, routeFromPath } from "./routes";

import type { AppRoute } from "../types";

/** Picks the first route for a visit to `/` with a stored login and profile. */
export function resolveInitialRoute(pathname: string): AppRoute {
  const fromPath = routeFromPath(pathname);
  if (fromPath !== "willkommen") {
    return fromPath;
  }
  if (readAuthSession() !== null && readProfileSession() !== null) {
    return "aktuell";
  }
  return "willkommen";
}

/** Syncs the browser URL with the active in-app route without adding history. */
export function syncBrowserPath(route: AppRoute): void {
  if (typeof window === "undefined") {
    return;
  }
  const nextPath = pathForRoute(route);
  if (window.location.pathname !== nextPath) {
    window.history.replaceState({}, "", nextPath);
  }
}

/** Returns true when an authenticated user with a saved profile should see Aktuell. */
export function shouldLandOnAktuell(
  route: AppRoute,
  isAuthenticated: boolean,
  hasSavedProfile: boolean,
): boolean {
  return route === "willkommen" && isAuthenticated && hasSavedProfile;
}
