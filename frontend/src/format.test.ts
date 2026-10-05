import { describe, expect, it } from "vitest";
import { formatPercentile, formatShare, formatTotal, formatValue } from "./format";

describe("formatValue", () => {
  it("shows per-90 counts with two decimals", () => {
    expect(formatValue({ key: "npxg", unit: "per_90", value: 0.4567 })).toBe("0.46");
  });
  it("shows completion-type ratios as percentages", () => {
    expect(formatValue({ key: "pass_completion", unit: "ratio", value: 0.823 })).toBe("82%");
  });
  it("keeps npxG per shot as an xG decimal, not a percentage", () => {
    expect(formatValue({ key: "npxg_per_shot", unit: "ratio", value: 0.125 })).toBe("0.13");
  });
  it("shows a dash, never zero, when a value is unavailable", () => {
    expect(formatValue({ key: "npxg", unit: "per_90", value: null })).toBe("—");
  });
});

describe("formatTotal", () => {
  it("shows integer totals for event counts and one decimal for xG", () => {
    expect(formatTotal({ key: "np_shots", unit: "per_90", total: 42 })).toBe("42");
    expect(formatTotal({ key: "npxg", unit: "per_90", total: 11.234 })).toBe("11.2");
  });
  it("has no season total for ratios", () => {
    expect(formatTotal({ key: "pass_completion", unit: "ratio", total: 900 })).toBeNull();
  });
});

describe("percentiles and shares", () => {
  it("rounds percentiles and marks missing ones", () => {
    expect(formatPercentile(97.6)).toBe("98");
    expect(formatPercentile(null)).toBe("—");
  });
  it("formats position shares", () => {
    expect(formatShare(0.854)).toBe("85%");
  });
});
