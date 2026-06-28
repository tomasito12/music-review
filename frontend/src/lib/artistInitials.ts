/** Build up to two uppercase initials from an artist display name. */
export function artistInitials(artistName: string): string {
  const words = artistName
    .trim()
    .split(/\s+/)
    .map((word) => word.replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, ""))
    .filter((word) => word.length > 0);

  if (words.length === 0) {
    return "?";
  }
  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase();
  }
  return `${words[0][0] ?? ""}${words[1][0] ?? ""}`.toUpperCase();
}
