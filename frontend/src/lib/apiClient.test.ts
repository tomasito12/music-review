import { describe, expect, it } from "vitest";

import { parseApiErrorMessage } from "./apiClient";

describe("parseApiErrorMessage", () => {
  it("returns string detail messages unchanged", () => {
    expect(parseApiErrorMessage({ detail: "Invalid email." }, "Fallback")).toBe(
      "Invalid email.",
    );
  });

  it("formats pydantic validation error arrays", () => {
    expect(
      parseApiErrorMessage(
        {
          detail: [
            {
              loc: ["body", "archive_limit"],
              msg: "Input should be less than or equal to 1000",
            },
          ],
        },
        "Unprocessable Content",
      ),
    ).toBe("body.archive_limit: Input should be less than or equal to 1000");
  });

  it("falls back when detail is missing", () => {
    expect(parseApiErrorMessage({}, "Unprocessable Content")).toBe(
      "Unprocessable Content",
    );
  });
});
