export interface ArtistImageLookupInput {
  artistMbid?: string;
  artistName?: string;
}

/** Build a stable lookup key for highlight artist image requests. */
export function artistImageLookupKey(lookup: ArtistImageLookupInput): string {
  const mbid = lookup.artistMbid?.trim() ?? "";
  if (mbid) {
    return mbid;
  }
  const name = lookup.artistName?.trim().toLowerCase() ?? "";
  return name ? `name:${name}` : "";
}

/** Return whether a lookup key refers to a name-only request. */
export function isNameLookupKey(lookupKey: string): boolean {
  return lookupKey.startsWith("name:");
}
