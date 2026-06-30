import { describe, expect, it } from "vitest";

import { createFavoritesSyncQueue } from "./favoritesSyncQueue";

describe("createFavoritesSyncQueue", () => {
  it("runs tasks one after another", async () => {
    const enqueue = createFavoritesSyncQueue();
    const order: string[] = [];

    const first = enqueue(async () => {
      await new Promise((resolve) => {
        setTimeout(resolve, 20);
      });
      order.push("first");
    });
    const second = enqueue(async () => {
      order.push("second");
    });

    await Promise.all([first, second]);
    expect(order).toEqual(["first", "second"]);
  });
});
