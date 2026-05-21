import { describe, expect, it } from 'vitest';

import { classifyLine, extractMemoPhrases } from '../augmented';

describe('extractMemoPhrases', () => {
  it('returns empty array for empty memo', () => {
    expect(extractMemoPhrases('')).toEqual([]);
  });

  it('splits Japanese sentences on punctuation', () => {
    const phrases = extractMemoPhrases('山田 CTO の発言通り 3H は確定。KPI は次回持ち越し');
    expect(phrases).toContain('山田 CTO の発言通り 3H は確定');
    expect(phrases).toContain('KPI は次回持ち越し');
  });

  it('drops phrases shorter than minLen', () => {
    const phrases = extractMemoPhrases('OK。確認済み。後で', 4);
    expect(phrases).not.toContain('OK');
    expect(phrases).not.toContain('後で');
    expect(phrases).toContain('確認済み');
  });

  it('deduplicates repeated phrases', () => {
    const phrases = extractMemoPhrases('3H で確定。3H で確定。');
    expect(phrases.filter((p) => p === '3H で確定')).toHaveLength(1);
  });
});

describe('classifyLine', () => {
  const phrases = extractMemoPhrases('山田 CTO の発言通り 3H は確定');

  it('marks lines containing memo phrase as memo', () => {
    expect(classifyLine('山田 CTO の発言通り 3H は確定とのこと', phrases)).toBe(
      'memo',
    );
  });

  it('marks lines starting with > as quote (highest priority)', () => {
    expect(classifyLine('> 山田 CTO の発言通り 3H は確定', phrases)).toBe(
      'quote',
    );
  });

  it('marks lines without memo phrase as helmsman', () => {
    expect(classifyLine('## 決定事項', phrases)).toBe('helmsman');
    expect(classifyLine('Topic 1 は decided', phrases)).toBe('helmsman');
  });

  it('returns helmsman for all lines when memo is empty', () => {
    expect(classifyLine('山田 CTO の発言通り 3H は確定', [])).toBe('helmsman');
  });
});
