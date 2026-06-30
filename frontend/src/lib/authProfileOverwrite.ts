import { tasteProfilesMatch } from "./profileComparison";
import type { TemporaryTasteProfile } from "./plattenradarApi";

/** Returns true when login should ask before replacing a stored account profile. */
export function shouldConfirmProfileOverwrite(
  existingProfile: TemporaryTasteProfile | null,
  sessionProfile: TemporaryTasteProfile | null,
): boolean {
  if (sessionProfile === null || existingProfile === null) {
    return false;
  }
  return !tasteProfilesMatch(existingProfile, sessionProfile);
}

export const profileOverwriteConfirmTitle =
  "Bestehendes Profil überschreiben?";

export const profileOverwriteConfirmIntro =
  "In deinem Konto liegt bereits ein gespeichertes Musikprofil. Möchtest du es mit deinem aktuellen Profil überschreiben?";

export const profileOverwriteConfirmSaveLabel = "Aktuelles Profil speichern";

export const profileOverwriteConfirmKeepLabel = "Gespeichertes Profil behalten";
