import type { TasteCommunityOption } from "./plattenradarApi";

/** Picks one community per broad category for the quick-test profile. */
export function pickExampleCommunityIds(communities: TasteCommunityOption[]): string[] {
  const picked: string[] = [];
  const seenCategories = new Set<string>();

  for (const community of communities) {
    const category = community.broad_categories[0];
    if (category === undefined || seenCategories.has(category)) {
      continue;
    }
    seenCategories.add(category);
    picked.push(community.id);
    if (picked.length >= 3) {
      return picked;
    }
  }

  if (picked.length > 0) {
    return picked;
  }

  return communities.slice(0, 3).map((community) => community.id);
}
