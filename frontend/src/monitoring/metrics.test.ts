import { describe, expect, it } from "vitest";
import { buildMetricGroups, type CityStats } from "./metrics";

const stats = new Proxy({}, { get: (_, key) => key === "activityCounts" ? { walking: 2, driving: 3, riding_bus: 4, waiting_bus: 1 } : 0 }) as CityStats;
describe("buildMetricGroups", () => {
  it("keeps every monitoring view compact and uniquely addressable", () => {
    const groups = buildMetricGroups(stats);
    expect(groups.map((group) => group.id)).toEqual(["summary", "housing", "economy", "banking", "health", "mobility", "social", "neighborhoods", "security"]);
    expect(groups.every((group) => group.metrics.length === 6)).toBe(true);
    expect(groups.every((group) => new Set(group.metrics.map((metric) => metric.id)).size === group.metrics.length)).toBe(true);
  });
  it("derives moving citizens in one tested place", () => {
    const mobility = buildMetricGroups(stats).find((group) => group.id === "mobility");
    expect(mobility?.metrics[0].value).toBe("10");
  });
});
