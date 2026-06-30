import type { TasteCommunityMapNode } from "./plattenradarApi";

const MAP_SIZE_MIN = 8;
const MAP_SIZE_MAX = 22;

/** Whether the desktop style map is enabled for profile step 2. */
export function isProfileStyleMapEnabled(): boolean {
  return import.meta.env.VITE_PROFILE_STYLE_MAP !== "false";
}

/** Convert normalized map coordinates to SVG viewBox units. */
export function mapPointToSvg(
  node: Pick<TasteCommunityMapNode, "x" | "y">,
  viewBoxSize = 1000,
): { x: number; y: number } {
  return {
    x: node.x * viewBoxSize,
    y: node.y * viewBoxSize,
  };
}

/** Scale community size into a readable node radius. */
export function communityMapNodeRadius(
  node: Pick<TasteCommunityMapNode, "size">,
  sizes: readonly number[],
): number {
  if (sizes.length === 0) {
    return MAP_SIZE_MIN;
  }
  const minSize = Math.min(...sizes);
  const maxSize = Math.max(...sizes);
  if (minSize === maxSize) {
    return (MAP_SIZE_MIN + MAP_SIZE_MAX) / 2;
  }
  const normalized = (node.size - minSize) / (maxSize - minSize);
  return MAP_SIZE_MIN + normalized * (MAP_SIZE_MAX - MAP_SIZE_MIN);
}

/** Build a lookup table for map nodes by community id. */
export function communityMapNodeById(
  nodes: readonly TasteCommunityMapNode[],
): Map<string, TasteCommunityMapNode> {
  return new Map(nodes.map((node) => [node.id, node]));
}
