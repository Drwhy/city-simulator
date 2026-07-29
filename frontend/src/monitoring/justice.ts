import type { JudicialCaseSummary, JudicialSentenceSummary } from "../types/city";

export function sortCourtQueue(cases: JudicialCaseSummary[]): JudicialCaseSummary[] {
  return [...cases].sort((left, right) =>
    right.priority - left.priority
    || left.hearingTick - right.hearingTick
    || left.id - right.id,
  );
}

export function sentenceProgress(sentence: JudicialSentenceSummary): number | null {
  if (sentence.requiredMinutes <= 0) return null;
  return Math.min(100, Math.round((sentence.completedMinutes / sentence.requiredMinutes) * 100));
}

export function isActiveSentence(sentence: JudicialSentenceSummary): boolean {
  return sentence.status === "active" || sentence.status === "violated";
}