import type { AppRoute } from "../types";

export function routeFromPath(pathname: string): AppRoute {
  const normalized = pathname.replace(/^\/+/, "");
  if (
    normalized === "aktuell" ||
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
