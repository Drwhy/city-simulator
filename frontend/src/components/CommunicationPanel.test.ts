import { describe, expect, it } from "vitest";
import { channelLabel, statusLabel } from "./CommunicationPanel";
describe("communication labels", () => {
  it("labels every supported channel", () => { expect(["phone_call", "sms", "email", "letter"].map((value) => channelLabel(value as never))).toEqual(["Téléphone", "SMS", "E-mail", "Lettre"]); });
  it("labels delivery states", () => { expect(statusLabel("failed")).toBe("Échec"); expect(statusLabel("replied")).toBe("Répondu"); });
});
