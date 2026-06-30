import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CommunityStyleMap } from "./CommunityStyleMap";

const communities = [
  {
    id: "C001",
    label: "Indie Rock",
    broad_categories: ["Rock & Alternative"],
    example_artists: ["Radiohead", "The National"],
  },
  {
    id: "C002",
    label: "Dream Pop",
    broad_categories: ["Pop & Indie"],
    example_artists: ["Beach House"],
  },
];

const mapNodes = [
  { id: "C001", x: 0.2, y: 0.4, size: 10, neighbors: ["C002"] },
  { id: "C002", x: 0.7, y: 0.6, size: 12, neighbors: ["C001"] },
];

describe("CommunityStyleMap", () => {
  it("marks a community as liked from the tooltip", () => {
    const onSetCommunityChoice = vi.fn();

    render(
      <CommunityStyleMap
        communities={communities}
        communityChoices={{}}
        mapNodes={mapNodes}
        onSetCommunityChoice={onSetCommunityChoice}
        visibleCommunityIds={["C001", "C002"]}
      />,
    );

    fireEvent.mouseEnter(screen.getByLabelText("Indie Rock: Noch offen"));
    fireEvent.click(screen.getByRole("button", { name: "Passt zu mir" }));
    expect(onSetCommunityChoice).toHaveBeenCalledWith("C001", "liked");
  });

  it("marks a community as disliked from the tooltip", () => {
    const onSetCommunityChoice = vi.fn();

    render(
      <CommunityStyleMap
        communities={communities}
        communityChoices={{ C002: "liked" }}
        mapNodes={mapNodes}
        onSetCommunityChoice={onSetCommunityChoice}
        visibleCommunityIds={["C001", "C002"]}
      />,
    );

    fireEvent.mouseEnter(screen.getByLabelText("Dream Pop: Passt zu mir"));
    fireEvent.click(screen.getByRole("button", { name: "Nicht meins" }));
    expect(onSetCommunityChoice).toHaveBeenCalledWith("C002", "disliked");
  });

  it("cycles node choice on click", () => {
    const onSetCommunityChoice = vi.fn();

    render(
      <CommunityStyleMap
        communities={communities}
        communityChoices={{}}
        mapNodes={mapNodes}
        onSetCommunityChoice={onSetCommunityChoice}
        visibleCommunityIds={["C001", "C002"]}
      />,
    );

    fireEvent.click(screen.getByLabelText("Dream Pop: Noch offen"));
    expect(onSetCommunityChoice).toHaveBeenCalledWith("C002", "liked");
  });
});
