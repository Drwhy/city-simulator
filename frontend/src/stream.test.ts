import { describe, expect, it } from "vitest";

import { mergeCityMessage } from "./stream";
import type { CityDelta, CitySnapshot } from "./types/city";

function snapshot(tick = 1): CitySnapshot {
  return {
    type: "city_snapshot",
    tick,
    day: 1,
    hour: 8,
    minute: 0,
    timeLabel: "Jour 1 — 08:00",
    map: { width: 48, height: 32 },
    roads: {
      cells: [{ x: 1, y: 2 }],
      congestion: [],
    },
    transport: {
      busStops: [{ id: 1, name: "Mairie", x: 2, y: 3, lineId: 1, sequence: 0 }],
      busLines: [{ id: 1, name: "Ligne A", stopIds: [1], route: [], fare: 2 }],
      operating: true,
    },
    health: { tick, metrics: { activeMedicalCases: 0 }, hospital: null, cases: [] },
  } as unknown as CitySnapshot;
}

function delta(): CityDelta {
  return {
    type: "city_delta",
    tick: 2,
    day: 1,
    hour: 8,
    minute: 1,
    timeLabel: "Jour 1 — 08:01",
    roads: {
      congestion: [{ x: 1, y: 2, vehicles: 3, level: "moderate" }],
    },
    transport: { operating: false },
    health: { tick: 2, metrics: { activeMedicalCases: 1 }, hospital: null, cases: [] },
  } as unknown as CityDelta;
}

describe("mergeCityMessage", () => {
  it("refuses a delta received before the initial snapshot", () => {
    expect(mergeCityMessage(null, delta())).toBeNull();
  });

  it("replaces the current state when a full snapshot arrives", () => {
    const current = snapshot(1);
    const replacement = snapshot(7);

    expect(mergeCityMessage(current, replacement)).toBe(replacement);
  });

  it("merges dynamic fields while preserving static map and transport data", () => {
    const current = snapshot();
    const update = delta();
    const merged = mergeCityMessage(current, update);

    expect(merged?.type).toBe("city_snapshot");
    expect(merged?.tick).toBe(2);
    expect(merged?.map).toBe(current.map);
    expect(merged?.roads.cells).toBe(current.roads.cells);
    expect(merged?.roads.congestion).toEqual(update.roads.congestion);
    expect(merged?.transport.busStops).toBe(current.transport.busStops);
    expect(merged?.transport.busLines).toBe(current.transport.busLines);
    expect(merged?.transport.operating).toBe(false);
    expect(merged?.health.metrics.activeMedicalCases).toBe(1);
    expect(current.tick).toBe(1);
    expect(current.transport.operating).toBe(true);
  });
});
