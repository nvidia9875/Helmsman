/**
 * Tone (発言感情) UI ヘルパー。
 *
 * バックエンドの EmotionLabel / MeetingMood に 1:1 対応する絵文字 + 色 + 日本語ラベル。
 * 文字列マジックを撒かないように、components から参照する単一の source-of-truth。
 */
import type { EmotionLabel, MeetingMood } from '@/lib/api';

interface EmotionStyle {
  emoji: string;
  label: string; // 日本語 1 単語
  color: string; // CSS var or hex
}

export const EMOTION_STYLE: Record<EmotionLabel, EmotionStyle> = {
  joy: { emoji: '😊', label: '前向き', color: '#ffd166' },
  agreement: { emoji: '👍', label: '賛同', color: '#5cf0f5' },
  curiosity: { emoji: '🤔', label: '探求', color: '#a78bfa' },
  concern: { emoji: '😕', label: '懸念', color: '#fbbf24' },
  frustration: { emoji: '😤', label: '苛立ち', color: '#fb7185' },
  neutral: { emoji: '😐', label: '中立', color: '#94a3b8' },
};

interface MoodStyle {
  label: string;
  emoji: string;
  hint: string;
  color: string;
}

export const MOOD_STYLE: Record<MeetingMood, MoodStyle> = {
  aligned: {
    label: 'ALIGNED',
    emoji: '✦',
    hint: '合意が積み上がっています',
    color: '#5cf0f5',
  },
  energetic: {
    label: 'ENERGETIC',
    emoji: '⚡',
    hint: '探求と熱量が出ています',
    color: '#ffd166',
  },
  tense: {
    label: 'TENSE',
    emoji: '⚠',
    hint: '緊張・困惑のシグナルが多めです',
    color: '#fb7185',
  },
  stuck: {
    label: 'STUCK',
    emoji: '~',
    hint: '中立発言が続き、空気が止まっています',
    color: '#94a3b8',
  },
};
