import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ArtistImageData } from "../lib/artistImageApi";
import { ArtistListThumbnail } from "./ArtistListThumbnail";

const image: ArtistImageData = {
  artistMbid: "mbid-1",
  artistName: "Known Artist",
  thumbnailUrl: "https://example.com/thumb.jpg",
  attributionText: "Demo",
  license: "CC BY 4.0",
  sourceUrl: "https://example.com/source",
};

describe("ArtistListThumbnail", () => {
  it("renders the artist thumbnail image", () => {
    render(<ArtistListThumbnail artistName="Known Artist" image={image} />);

    expect(screen.getByRole("img", { name: "Known Artist" })).toBeTruthy();
  });

  it("notifies the parent when the image fails to load", () => {
    const onFailed = vi.fn();
    render(
      <ArtistListThumbnail
        artistName="Known Artist"
        image={image}
        onFailed={onFailed}
      />,
    );

    screen.getByRole("img", { name: "Known Artist" }).dispatchEvent(
      new Event("error"),
    );

    expect(onFailed).toHaveBeenCalledOnce();
  });
});
