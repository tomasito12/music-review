const EXAMPLE_ARTIST_PREFIX = "z. B. ";

function orderedArtistSubsets(names: string[], count: number): string[][] {
  const subsets: string[][] = [];

  function walk(startIndex: number, picked: string[]): void {
    if (picked.length === count) {
      subsets.push([...picked]);
      return;
    }
    for (let index = startIndex; index < names.length; index += 1) {
      picked.push(names[index]);
      walk(index + 1, picked);
      picked.pop();
    }
  }

  walk(0, []);
  return subsets;
}

function exampleArtistCaption(names: string[]): string {
  return EXAMPLE_ARTIST_PREFIX + names.join(", ");
}

/** Formats up to three example artists on one line for profile detail cards. */
export function formatCommunityExampleArtists(
  artists: string[],
  maxChars = 55,
): string {
  const names = artists.map((name) => name.trim()).filter(Boolean);
  if (names.length === 0) {
    return "";
  }

  for (const count of [3, 2, 1]) {
    if (names.length < count) {
      continue;
    }
    const fitting = orderedArtistSubsets(names, count)
      .map((subset) => ({
        caption: exampleArtistCaption(subset),
        subset,
      }))
      .filter(
        ({ caption }) => caption.length <= maxChars || count === 1,
      )
      .sort((left, right) => left.caption.length - right.caption.length);
    if (fitting.length > 0) {
      return fitting[0].caption;
    }
  }

  return exampleArtistCaption([names[0]]);
}
