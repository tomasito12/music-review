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

/** Keys used to avoid showing the same band twice (MBID and normalized name). */
export function artistDedupeKeys(lookup: ArtistImageLookupInput): string[] {
  const keys: string[] = [];
  const mbid = lookup.artistMbid?.trim() ?? "";
  const name = lookup.artistName?.trim().toLowerCase() ?? "";
  if (mbid) {
    keys.push(mbid);
  }
  if (name) {
    keys.push(`name:${name}`);
  }
  return keys;
}

/** Return whether an artist is already claimed by MBID or normalized name. */
export function isArtistClaimed(
  lookup: ArtistImageLookupInput,
  claimedKeys: ReadonlySet<string>,
): boolean {
  const keys = artistDedupeKeys(lookup);
  return keys.length > 0 && keys.some((key) => claimedKeys.has(key));
}

/** Register all dedupe keys for one artist. */
export function claimArtist(
  lookup: ArtistImageLookupInput,
  claimedKeys: Set<string>,
): void {
  for (const key of artistDedupeKeys(lookup)) {
    claimedKeys.add(key);
  }
}

/** Return whether a lookup key refers to a name-only request. */
export function isNameLookupKey(lookupKey: string): boolean {
  return lookupKey.startsWith("name:");
}
