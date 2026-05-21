/**
 * Granola の "augmented notes" 由来パターン。
 *
 * Helmsman の Report は Helmsman の構造化結果 + ユーザー memo を LLM が織り交ぜて作る。
 * その結果のうち「memo に由来する行」を視覚的に区別するためのヘルパ。
 *
 * 設計判断: LLM が memo を rephrase することは許容するが、保守的に検出する。
 * memo を句読点 / 空白で phrase 単位に切り、substring match した行のみ memo 由来扱い。
 * これにより「memo の影響が確実な行」だけが白、それ以外は灰で表示される。
 */

// 句読点 + 改行で区切る。半角/全角空白では区切らない (「3H で確定」のような句を保つため)。
const SPLIT_REGEX = /[、。,.!?！?\n\r\t()「」『』【】]+/;

export function extractMemoPhrases(memo: string, minLen = 4): string[] {
  if (!memo) return [];
  const seen = new Set<string>();
  for (const part of memo.split(SPLIT_REGEX)) {
    const trimmed = part.trim();
    if (trimmed.length >= minLen) {
      seen.add(trimmed);
    }
  }
  return [...seen];
}

export type LineKind = 'memo' | 'helmsman' | 'quote';

export function classifyLine(line: string, memoPhrases: string[]): LineKind {
  if (line.trimStart().startsWith('>')) return 'quote';
  if (memoPhrases.length === 0) return 'helmsman';
  return memoPhrases.some((p) => line.includes(p)) ? 'memo' : 'helmsman';
}
