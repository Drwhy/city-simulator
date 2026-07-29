import { describe, expect, it } from "vitest";
import { cityWebSocketUrl } from "./useCityStream";
describe("cityWebSocketUrl", () => {
  it("uses a secure socket behind HTTPS", () => expect(cityWebSocketUrl({ protocol: "https:", host: "city.test" } as Location)).toBe("wss://city.test/ws/city"));
  it("uses a regular socket behind HTTP", () => expect(cityWebSocketUrl({ protocol: "http:", host: "localhost:5173" } as Location)).toBe("ws://localhost:5173/ws/city"));
});
