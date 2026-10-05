import { describe, expect, it } from "vitest";
import { niceScale, niceStep } from "./ScatterMap";

describe("nice axis scales", () => {
  it("picks 1-2-5 steps", () => {
    expect(niceStep(8)).toBe(2);
    expect(niceStep(0.9)).toBe(0.2);
    expect(niceStep(30)).toBe(10);
  });
  it("snaps the domain to round ticks that contain the data", () => {
    const { domain, ticks } = niceScale([10.8, 19.3]);
    expect(domain[0]).toBeLessThanOrEqual(10.8);
    expect(domain[1]).toBeGreaterThanOrEqual(19.3);
    expect(ticks).toEqual([10, 12, 14, 16, 18, 20]);
  });
});
