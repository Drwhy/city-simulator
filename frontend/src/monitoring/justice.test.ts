import { describe, expect, it } from "vitest";
import { isActiveSentence, sentenceProgress, sortCourtQueue } from "./justice";
import type { JudicialCaseSummary, JudicialSentenceSummary } from "../types/city";

const caseRow = (id: number, priority: number, hearingTick: number) => ({ id, priority, hearingTick }) as JudicialCaseSummary;
const sentence = (status: JudicialSentenceSummary["status"], completedMinutes = 0, requiredMinutes = 0) => ({ status, completedMinutes, requiredMinutes }) as JudicialSentenceSummary;

describe("justice monitoring", () => {
  it("orders the court queue by priority, hearing and stable id", () => {
    const rows = sortCourtQueue([caseRow(3, 1, 50), caseRow(2, 3, 80), caseRow(1, 3, 80)]);
    expect(rows.map((row) => row.id)).toEqual([1, 2, 3]);
  });

  it("derives bounded community-service progress", () => {
    expect(sentenceProgress(sentence("active", 120, 480))).toBe(25);
    expect(sentenceProgress(sentence("completed", 600, 480))).toBe(100);
    expect(sentenceProgress(sentence("active"))).toBeNull();
  });

  it("keeps violated probation visible as active monitoring", () => {
    expect(isActiveSentence(sentence("active"))).toBe(true);
    expect(isActiveSentence(sentence("violated"))).toBe(true);
    expect(isActiveSentence(sentence("completed"))).toBe(false);
  });
});