/**
 * Gini 係数 — 発言量の偏り。
 * 0 = 完全平等、1 = 完全に 1 人独占。
 *
 * 標準ソート式: 昇順 x_1..x_n に対し G = Σ(2i - n - 1) x_i / (n · Σ x_i)
 */
export function gini(values: ReadonlyArray<number>): number {
  const filtered = values.filter((v) => v >= 0);
  const n = filtered.length;
  if (n === 0) return 0;
  const sorted = [...filtered].sort((a, b) => a - b);
  const sum = sorted.reduce((acc, v) => acc + v, 0);
  if (sum === 0) return 0;
  let weighted = 0;
  for (let i = 0; i < n; i++) {
    weighted += (2 * (i + 1) - n - 1) * sorted[i]!;
  }
  return Math.max(0, Math.min(1, weighted / (n * sum)));
}

export type GiniBand = 'balanced' | 'mild' | 'skewed';

/**
 * 0-1 の Gini を 3 段ラベル化。境界値は文献 (経済学の収入分布) よりも
 * 「会議発言量」の文脈に合わせて緩めに設定 (会議では 2-3 人偏重が普通)。
 */
export function giniBand(value: number): GiniBand {
  if (value < 0.2) return 'balanced';
  if (value < 0.4) return 'mild';
  return 'skewed';
}

export function giniLabel(band: GiniBand): string {
  switch (band) {
    case 'balanced':
      return '均等';
    case 'mild':
      return '軽い偏り';
    case 'skewed':
      return '偏重';
  }
}
