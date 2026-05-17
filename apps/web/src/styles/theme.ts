/**
 * Helmsman の Fluent UI dark theme override.
 *
 * "Mission Control Terminal" aesthetic — Bloomberg-density meets Linear-precision.
 * Values mirror src/styles/global.css :root custom properties so plain CSS and
 * Fluent components stay in sync.
 */
import { Theme, webDarkTheme } from '@fluentui/react-components';

export const helmsmanDarkTheme: Theme = {
  ...webDarkTheme,
  // Page / panel surfaces — graded by depth
  colorNeutralBackground1: '#08080a',
  colorNeutralBackground1Hover: '#131319',
  colorNeutralBackground1Pressed: '#1a1a22',
  colorNeutralBackground2: '#0d0d10',
  colorNeutralBackground2Hover: '#131319',
  colorNeutralBackground2Pressed: '#1a1a22',
  colorNeutralBackground3: '#131319',
  colorNeutralBackground3Hover: '#1a1a22',
  colorNeutralBackground3Pressed: '#262633',
  colorNeutralBackground4: '#08080a',
  colorNeutralBackground5: '#131319',
  colorNeutralBackground6: '#1a1a22',

  colorNeutralBackgroundInverted: '#ededed',
  colorNeutralBackgroundDisabled: '#1a1a22',

  // Borders — hairline & default
  colorNeutralStroke1: '#262633',
  colorNeutralStroke1Hover: '#34344a',
  colorNeutralStroke1Pressed: '#34344a',
  colorNeutralStroke2: '#1d1d27',
  colorNeutralStroke3: '#1d1d27',
  colorTransparentStroke: '#1d1d27',
  colorNeutralStrokeAccessible: '#34344a',
  colorNeutralStrokeDisabled: '#262633',

  // Text ladder
  colorNeutralForeground1: '#ededed',
  colorNeutralForeground1Hover: '#ffffff',
  colorNeutralForeground2: '#9a9aac',
  colorNeutralForeground3: '#5e5e72',
  colorNeutralForeground4: '#3d3d4d',
  colorNeutralForegroundDisabled: '#3d3d4d',

  // Brand — single blue accent
  colorBrandBackground: '#5b8def',
  colorBrandBackgroundHover: '#4576e6',
  colorBrandBackgroundPressed: '#3661cf',
  colorBrandBackground2: '#101424',
  colorBrandBackgroundInverted: '#5b8def',
  colorBrandStroke1: '#5b8def',
  colorBrandStroke2: '#1e2a4a',
  colorBrandForeground1: '#83a8f3',
  colorBrandForeground2: '#5b8def',
  colorBrandForegroundLink: '#83a8f3',
  colorBrandForegroundLinkHover: '#a8c1f7',
};

/** 4px grid spacing scale */
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

/** Typography scale (px). 7 sizes total — anything outside this is wrong. */
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
