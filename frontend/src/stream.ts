import type { CitySnapshot, CityStreamMessage } from "./types/city";

export function mergeCityMessage(
  current: CitySnapshot | null,
  message: CityStreamMessage,
): CitySnapshot | null {
  if (message.type === "city_snapshot") return message;
  if (current === null) return null;
  return {
    ...current,
    ...message,
    type: "city_snapshot",
    map: current.map,
    roads: { ...current.roads, ...message.roads },
    transport: { ...current.transport, ...message.transport },
  };
}
