import { describe, expect, it } from 'vitest';

import { gini, giniBand, giniLabel } from '../gini';

describe('gini', () => {
  it('returns 0 for empty array', () => {
    expect(gini([])).toBe(0);
  });

  it('returns 0 when all values are equal', () => {
    expect(gini([5, 5, 5, 5])).toBeCloseTo(0, 5);
  });

  it('returns 0 when sum is zero', () => {
    expect(gini([0, 0, 0])).toBe(0);
  });

  it('approaches 1 - 1/n when one person speaks everything', () => {
    // 4 人で 1 人が 100、他 0 -> G = (n-1)/n = 0.75
    expect(gini([0, 0, 0, 100])).toBeCloseTo(0.75, 2);
  });

  it('handles ordering insensitively', () => {
    expect(gini([10, 20, 30, 40])).toBeCloseTo(gini([40, 30, 20, 10]), 5);
  });

  it('clamps to [0, 1]', () => {
    const v = gini([1, 2, 3]);
    expect(v).toBeGreaterThanOrEqual(0);
    expect(v).toBeLessThanOrEqual(1);
  });
});

describe('giniBand + giniLabel', () => {
  it('bands at 0.2 and 0.4', () => {
    expect(giniBand(0)).toBe('balanced');
    expect(giniBand(0.1)).toBe('balanced');
    expect(giniBand(0.2)).toBe('mild');
    expect(giniBand(0.35)).toBe('mild');
    expect(giniBand(0.4)).toBe('skewed');
    expect(giniBand(0.9)).toBe('skewed');
  });

  it('labels each band in Japanese', () => {
    expect(giniLabel('balanced')).toBe('均等');
    expect(giniLabel('mild')).toBe('軽い偏り');
    expect(giniLabel('skewed')).toBe('偏重');
  });
});
