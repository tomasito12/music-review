import type { AppRoute } from "../types";

export type ProfileSetupMode = "initial" | "edit";

export type ProfileReturnRoute = "aktuell" | "entdecken" | "playlists";

export interface ProfileReturnNavigationState {
  mode: ProfileSetupMode;
  returnRoute: ProfileReturnRoute | null;
}

const CONTENT_RETURN_ROUTES = new Set<ProfileReturnRoute>([
  "aktuell",
  "entdecken",
  "playlists",
]);

function isContentReturnRoute(route: AppRoute): route is ProfileReturnRoute {
  return CONTENT_RETURN_ROUTES.has(route as ProfileReturnRoute);
}

/** Stores a content page as the route to return to after profile editing. */
export function captureProfileReturnRoute(
  fromRoute: AppRoute,
  currentReturnRoute: ProfileReturnRoute | null = null,
): ProfileReturnRoute | null {
  if (isContentReturnRoute(fromRoute)) {
    return fromRoute;
  }
  return currentReturnRoute;
}

/** Prepares navigation state for first-time profile setup. */
export function startInitialProfileSetup(): ProfileReturnNavigationState {
  return {
    mode: "initial",
    returnRoute: null,
  };
}

/** Prepares navigation state when opening the profile editor from another page. */
export function startProfileEdit(
  fromRoute: AppRoute,
  currentReturnRoute: ProfileReturnRoute | null = null,
): ProfileReturnNavigationState {
  return {
    mode: "edit",
    returnRoute: captureProfileReturnRoute(fromRoute, currentReturnRoute),
  };
}

/** Picks where the app should go after the profile wizard finishes. */
export function resolveProfileFinishRoute(input: {
  mode: ProfileSetupMode;
  returnRoute: ProfileReturnRoute | null;
  isAuthenticated: boolean;
}): ProfileReturnRoute {
  if (input.mode === "initial") {
    return "entdecken";
  }
  if (input.returnRoute !== null) {
    return input.returnRoute;
  }
  return input.isAuthenticated ? "aktuell" : "entdecken";
}
