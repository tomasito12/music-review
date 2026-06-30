import { useMemo, useRef, useState } from "react";
import type { PointerEvent, ReactElement, WheelEvent } from "react";

import type { CommunityMapChoice } from "../lib/communityMapChoice";
import {
  communityMapNodeById,
  communityMapNodeRadius,
  mapPointToSvg,
} from "../lib/communityStyleMapLayout";
import { formatCommunityExampleArtists } from "../lib/profileFormatting";
import type {
  TasteCommunityMapNode,
  TasteCommunityOption,
} from "../lib/plattenradarApi";

const VIEWBOX_SIZE = 1000;
const MIN_SCALE = 0.75;
const MAX_SCALE = 2.4;
const HIT_TARGET_PADDING = 12;

interface CommunityStyleMapProps {
  communities: TasteCommunityOption[];
  communityChoices: Record<string, CommunityMapChoice>;
  mapNodes: TasteCommunityMapNode[];
  onSetCommunityChoice: (communityId: string, choice: CommunityMapChoice) => void;
  visibleCommunityIds: string[];
}

interface MapViewport {
  scale: number;
  x: number;
  y: number;
}

function choiceLabel(choice: CommunityMapChoice): string {
  if (choice === "liked") {
    return "Passt zu mir";
  }
  if (choice === "disliked") {
    return "Nicht meins";
  }
  return "Noch offen";
}

/** Interactive 2D map of taste communities for desktop profile setup. */
export function CommunityStyleMap({
  communities,
  communityChoices,
  mapNodes,
  onSetCommunityChoice,
  visibleCommunityIds,
}: CommunityStyleMapProps): ReactElement {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const [hoveredCommunityId, setHoveredCommunityId] = useState<string | null>(null);
  const [viewport, setViewport] = useState<MapViewport>({ scale: 1, x: 0, y: 0 });

  const communityById = useMemo(
    () => new Map(communities.map((community) => [community.id, community])),
    [communities],
  );
  const mapNodeById = useMemo(() => communityMapNodeById(mapNodes), [mapNodes]);
  const visibleIds = useMemo(() => new Set(visibleCommunityIds), [visibleCommunityIds]);
  const sizes = useMemo(() => mapNodes.map((node) => node.size), [mapNodes]);

  const activeCommunityId = hoveredCommunityId;
  const activeCommunity =
    activeCommunityId !== null ? communityById.get(activeCommunityId) : undefined;
  const activeMapNode =
    activeCommunityId !== null ? mapNodeById.get(activeCommunityId) : undefined;
  const activeChoice =
    activeCommunityId !== null ? (communityChoices[activeCommunityId] ?? "unset") : "unset";
  const neighborIds = useMemo(() => {
    if (activeMapNode === undefined) {
      return new Set<string>();
    }
    return new Set(activeMapNode.neighbors);
  }, [activeMapNode]);

  function handleWheel(event: WheelEvent<HTMLDivElement>): void {
    event.preventDefault();
    const direction = event.deltaY > 0 ? -1 : 1;
    setViewport((current) => {
      const nextScale = Math.min(
        MAX_SCALE,
        Math.max(MIN_SCALE, current.scale + direction * 0.08),
      );
      return { ...current, scale: nextScale };
    });
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>): void {
    if (event.button !== 0) {
      return;
    }
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      originX: viewport.x,
      originY: viewport.y,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>): void {
    const drag = dragRef.current;
    if (drag === null) {
      return;
    }
    const deltaX = event.clientX - drag.startX;
    const deltaY = event.clientY - drag.startY;
    if (Math.hypot(deltaX, deltaY) > 4) {
      drag.moved = true;
    }
    setViewport((current) => ({
      ...current,
      x: drag.originX + deltaX,
      y: drag.originY + deltaY,
    }));
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>): void {
    if (dragRef.current?.moved) {
      suppressClickRef.current = true;
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
    }
    dragRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  function handleNodeClick(communityId: string): void {
    if (suppressClickRef.current) {
      return;
    }
    const current = communityChoices[communityId] ?? "unset";
    if (current === "unset") {
      onSetCommunityChoice(communityId, "liked");
      return;
    }
    if (current === "liked") {
      onSetCommunityChoice(communityId, "disliked");
      return;
    }
    onSetCommunityChoice(communityId, "unset");
  }

  return (
    <div className="style-map-shell">
      <div className="style-map-toolbar">
        <p className="style-map-hint">
          Zoomen mit Mausrad, verschieben per Ziehen. Klick wechselt offen, passt
          und nicht meins — oder nutze die Buttons im Tooltip.
        </p>
        <ul className="style-map-legend" aria-label="Legende">
          <li>
            <span className="style-map-legend-swatch open" />
            Noch offen
          </li>
          <li>
            <span className="style-map-legend-swatch liked" />
            Passt zu mir
          </li>
          <li>
            <span className="style-map-legend-swatch disliked" />
            Nicht meins
          </li>
        </ul>
      </div>
      <div
        className="style-map-viewport"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
      >
        <svg
          aria-label="Stilwelten-Landkarte"
          className="style-map-svg"
          ref={svgRef}
          role="img"
          viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
        >
          <rect
            className="style-map-background"
            height={VIEWBOX_SIZE}
            width={VIEWBOX_SIZE}
            x={0}
            y={0}
          />
          <g
            transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}
          >
            {activeMapNode !== undefined &&
              activeMapNode.neighbors.map((neighborId) => {
                const neighborNode = mapNodeById.get(neighborId);
                if (neighborNode === undefined || !visibleIds.has(neighborId)) {
                  return null;
                }
                const start = mapPointToSvg(activeMapNode, VIEWBOX_SIZE);
                const end = mapPointToSvg(neighborNode, VIEWBOX_SIZE);
                return (
                  <line
                    className="style-map-neighbor-edge"
                    key={`${activeMapNode.id}-${neighborId}`}
                    x1={start.x}
                    x2={end.x}
                    y1={start.y}
                    y2={end.y}
                  />
                );
              })}
            {mapNodes.map((node) => {
              if (!visibleIds.has(node.id)) {
                return null;
              }
              const community = communityById.get(node.id);
              if (community === undefined) {
                return null;
              }
              const point = mapPointToSvg(node, VIEWBOX_SIZE);
              const radius = communityMapNodeRadius(node, sizes);
              const choice = communityChoices[node.id] ?? "unset";
              const isHovered = hoveredCommunityId === node.id;
              const isNeighbor = neighborIds.has(node.id);
              const className = [
                "style-map-node",
                choice !== "unset" ? "reviewed" : "",
                choice === "liked" ? "liked" : "",
                choice === "disliked" ? "disliked" : "",
                isHovered ? "hovered" : "",
                isNeighbor ? "neighbor" : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <g
                  className={className}
                  key={node.id}
                  onMouseEnter={() => setHoveredCommunityId(node.id)}
                  onMouseLeave={() =>
                    setHoveredCommunityId((current) => (current === node.id ? null : current))
                  }
                  transform={`translate(${point.x} ${point.y})`}
                >
                  <circle
                    aria-label={`${community.label}: ${choiceLabel(choice)}`}
                    className="style-map-node-hit"
                    onClick={() => handleNodeClick(node.id)}
                    onPointerDown={(event) => event.stopPropagation()}
                    r={radius + HIT_TARGET_PADDING}
                  />
                  <circle className="style-map-node-circle" r={radius} />
                </g>
              );
            })}
          </g>
        </svg>
        {activeCommunity !== undefined && activeMapNode !== undefined && (
          <div className="style-map-tooltip" role="status">
            <strong>{activeCommunity.label}</strong>
            {formatCommunityExampleArtists(activeCommunity.example_artists) !== "" && (
              <span>{formatCommunityExampleArtists(activeCommunity.example_artists)}</span>
            )}
            <span className="style-map-tooltip-state">{choiceLabel(activeChoice)}</span>
            <div className="style-map-tooltip-actions">
              <button
                className={`secondary-button${
                  activeChoice === "liked" ? " style-map-choice-active" : ""
                }`}
                onClick={() => onSetCommunityChoice(activeCommunity.id, "liked")}
                type="button"
              >
                Passt zu mir
              </button>
              <button
                className={`secondary-button style-map-choice-dislike${
                  activeChoice === "disliked" ? " style-map-choice-active" : ""
                }`}
                onClick={() => onSetCommunityChoice(activeCommunity.id, "disliked")}
                type="button"
              >
                Nicht meins
              </button>
              {activeChoice !== "unset" && (
                <button
                  className="ghost-button"
                  onClick={() => onSetCommunityChoice(activeCommunity.id, "unset")}
                  type="button"
                >
                  Zurücksetzen
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
