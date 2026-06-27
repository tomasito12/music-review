/** Decide whether cached recommendation rows should be refetched. */
export function shouldRefetchRecommendations(
  recommendations: unknown[] | null,
  reloadToken: number,
  lastHandledReloadToken: number,
): boolean {
  if (recommendations === null) {
    return true;
  }
  return reloadToken !== lastHandledReloadToken;
}
