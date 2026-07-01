import type { AppRoute } from "../types";

/** Browser path for one in-app route. */
export function pathForRoute(route: AppRoute): string {
  if (route === "willkommen") {
    return "/";
  }
  if (route === "aktuell") {
    return "/neuheiten";
  }
  return `/${route}`;
}

export function routeFromPath(pathname: string): AppRoute {
  const normalized = pathname.replace(/^\/+/, "");
  if (normalized === "neuheiten" || normalized === "aktuell") {
    return "aktuell";
  }
  if (
    normalized === "entdecken" ||
    normalized === "playlists" ||
    normalized === "musikprofil" ||
    normalized === "konto"
  ) {
    return normalized;
  }
  if (normalized === "profil/setup") {
    return "musikprofil";
  }
  return "willkommen";
}
