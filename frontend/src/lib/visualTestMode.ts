/** Return whether the page runs in Playwright visual-regression mode. */
export function isVisualTestMode(): boolean {
  return (
    typeof document !== "undefined" &&
    document.documentElement.dataset.visualTest === "true"
  );
}
