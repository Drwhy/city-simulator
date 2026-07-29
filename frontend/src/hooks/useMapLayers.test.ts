import { describe, expect, it } from "vitest";
import { DEFAULT_MAP_LAYERS, updateMapLayer } from "./useMapLayers";

describe("map layers", () => {
  it("starts with every monitoring layer visible", () => {
    expect(Object.values(DEFAULT_MAP_LAYERS).every(Boolean)).toBe(true);
    expect(Object.keys(DEFAULT_MAP_LAYERS)).toHaveLength(12);
  });

  it("updates one layer without mutating the current state", () => {
    const current = { ...DEFAULT_MAP_LAYERS };
    const updated = updateMapLayer(current, "traffic", false);

    expect(updated.traffic).toBe(false);
    expect(updated.citizens).toBe(true);
    expect(current.traffic).toBe(true);
    expect(updated).not.toBe(current);
  });
});