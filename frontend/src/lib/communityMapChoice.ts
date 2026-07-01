/** Tri-state choice for one community on the style map. */
export type CommunityMapChoice = "unset" | "liked" | "disliked";

export interface CommunityMapChoiceSummary {
  disliked: number;
  liked: number;
  reviewed: number;
  total: number;
  unset: number;
}

/** Advance one community through unset → liked → disliked → unset. */
export function cycleCommunityMapChoice(current: CommunityMapChoice): CommunityMapChoice {
  if (current === "unset") {
    return "liked";
  }
  if (current === "liked") {
    return "disliked";
  }
  return "unset";
}

/** Apply a choice update, dropping unset entries from the map. */
export function applyCommunityMapChoice(
  current: Record<string, CommunityMapChoice>,
  communityId: string,
  choice: CommunityMapChoice,
): Record<string, CommunityMapChoice> {
  if (choice === "unset") {
    const next = { ...current };
    delete next[communityId];
    return next;
  }
  return { ...current, [communityId]: choice };
}

/** Return community ids marked as liked. */
export function likedCommunityIds(
  choices: Record<string, CommunityMapChoice>,
): string[] {
  return Object.entries(choices)
    .filter(([, choice]) => choice === "liked")
    .map(([communityId]) => communityId);
}

/** Keep only choices for communities that remain visible. */
export function pruneCommunityMapChoices(
  choices: Record<string, CommunityMapChoice>,
  allowedCommunityIds: readonly string[],
): Record<string, CommunityMapChoice> {
  const allowed = new Set(allowedCommunityIds);
  return Object.fromEntries(
    Object.entries(choices).filter(([communityId]) => allowed.has(communityId)),
  );
}

/** Summarize reviewed vs open communities for the current visible set. */
export function summarizeCommunityMapChoices(
  choices: Record<string, CommunityMapChoice>,
  visibleCommunityIds: readonly string[],
): CommunityMapChoiceSummary {
  let liked = 0;
  let disliked = 0;
  for (const communityId of visibleCommunityIds) {
    const choice = choices[communityId] ?? "unset";
    if (choice === "liked") {
      liked += 1;
    } else if (choice === "disliked") {
      disliked += 1;
    }
  }
  const total = visibleCommunityIds.length;
  const reviewed = liked + disliked;
  return {
    liked,
    disliked,
    reviewed,
    total,
    unset: total - reviewed,
  };
}

/** Remove choices for the given community ids. */
export function resetCommunityMapChoices(
  choices: Record<string, CommunityMapChoice>,
  communityIds: readonly string[],
): Record<string, CommunityMapChoice> {
  const toClear = new Set(communityIds);
  return Object.fromEntries(
    Object.entries(choices).filter(([communityId]) => !toClear.has(communityId)),
  );
}

/** Build initial choices from saved liked community ids. */
export function communityChoicesFromLikedIds(
  likedIds: readonly string[],
): Record<string, CommunityMapChoice> {
  return Object.fromEntries(likedIds.map((communityId) => [communityId, "liked" as const]));
}
