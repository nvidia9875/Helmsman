/**
 * Helmsman の Fluent UI dark theme override。
 *
 * 設計方針 (Linear / Vercel 風ミニマル):
 * - ニュートラル背景は純黒寄り (#0a0a0a / #111111)
 * - border は薄く (#1f1f1f / #262626)
 * - ブランド色は 1 つ (#3b82f6) — CTA と focus にだけ使う
 * - shadow / gradient は使わない
 */
import { Theme, webDarkTheme } from '@fluentui/react-components';

export const helmsmanDarkTheme: Theme = {
  ...webDarkTheme,
  // page / panel 背景
  colorNeutralBackground1: '#0a0a0a',
  colorNeutralBackground1Hover: '#161616',
  colorNeutralBackground1Pressed: '#1f1f1f',
  colorNeutralBackground2: '#111111',
  colorNeutralBackground2Hover: '#161616',
  colorNeutralBackground2Pressed: '#1f1f1f',
  colorNeutralBackground3: '#161616',
  colorNeutralBackground3Hover: '#1f1f1f',
  colorNeutralBackground3Pressed: '#262626',
  colorNeutralBackground4: '#0a0a0a',
  colorNeutralBackground5: '#161616',
  colorNeutralBackground6: '#1f1f1f',

  // 入力欄 / surface
  colorNeutralBackgroundInverted: '#ededed',
  colorNeutralBackgroundDisabled: '#1f1f1f',

  // border (薄く一律)
  colorNeutralStroke1: '#262626',
  colorNeutralStroke1Hover: '#3a3a3a',
  colorNeutralStroke1Pressed: '#3a3a3a',
  colorNeutralStroke2: '#1f1f1f',
  colorNeutralStroke3: '#1f1f1f',
  colorTransparentStroke: '#1f1f1f',
  colorNeutralStrokeAccessible: '#3a3a3a',
  colorNeutralStrokeDisabled: '#262626',

  // text
  colorNeutralForeground1: '#ededed',
  colorNeutralForeground1Hover: '#ffffff',
  colorNeutralForeground2: '#999999',
  colorNeutralForeground3: '#6e6e6e',
  colorNeutralForeground4: '#5a5a5a',
  colorNeutralForegroundDisabled: '#5a5a5a',

  // ブランド色 (青 1 色のみ。CTA / focus / accent)
  colorBrandBackground: '#3b82f6',
  colorBrandBackgroundHover: '#2563eb',
  colorBrandBackgroundPressed: '#1d4ed8',
  colorBrandBackground2: '#0f172a',
  colorBrandBackgroundInverted: '#3b82f6',
  colorBrandStroke1: '#3b82f6',
  colorBrandStroke2: '#1e3a8a',
  colorBrandForeground1: '#60a5fa',
  colorBrandForeground2: '#3b82f6',
  colorBrandForegroundLink: '#60a5fa',
  colorBrandForegroundLinkHover: '#93c5fd',
};

/** UI で使う 4px グリッドのスケール */
export const spacing = {
  xs: '4px',
  s: '8px',
  m: '12px',
  l: '16px',
  xl: '24px',
  xxl: '32px',
  xxxl: '48px',
  xxxxl: '64px',
} as const;

/** タイポグラフィスケール (px) */
export const fontSize = {
  xs: '11px',
  s: '12px',
  m: '13px',
  l: '16px',
  xl: '20px',
  xxl: '28px',
  display: '40px',
} as const;

export const radii = {
  s: '4px',
  m: '6px',
  l: '8px',
  pill: '999px',
} as const;
