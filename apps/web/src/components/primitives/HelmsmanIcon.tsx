/**
 * HelmsmanIcon — 船舵 (ship's wheel) を inline SVG で描画。
 * Bot avatar / アイコンとして 🧭 emoji の代わりに使う。
 * size は CSS で指定 (例: width: 36px)。
 */

interface Props {
  size?: number;
  tone?: 'brand' | 'mono' | 'subtle';
  className?: string;
  spin?: boolean;
}

export function HelmsmanIcon({ size = 24, tone = 'brand', className, spin }: Props) {
  const ringColor = tone === 'mono' ? 'currentColor' : tone === 'subtle' ? 'rgba(120,140,180,0.6)' : '#ffffff';
  const bgFill = tone === 'mono' || tone === 'subtle' ? 'transparent' : 'url(#hi-bg)';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className={className}
      aria-hidden="true"
      style={spin ? { animation: 'helmsman-spin 12s linear infinite' } : undefined}
    >
      <defs>
        <linearGradient id="hi-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#5b8def" />
          <stop offset="100%" stopColor="#3661cf" />
        </linearGradient>
        <radialGradient id="hi-hub" cx="32" cy="32" r="6" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0.55" />
        </radialGradient>
      </defs>

      {tone !== 'mono' && tone !== 'subtle' && (
        <rect width="64" height="64" rx="14" ry="14" fill={bgFill} />
      )}

      {/* outer wheel ring */}
      <circle cx="32" cy="32" r="20" stroke={ringColor} strokeOpacity="0.92" strokeWidth="2.5" fill="none" />

      {/* inner wheel ring */}
      <circle cx="32" cy="32" r="13" stroke={ringColor} strokeOpacity="0.85" strokeWidth="1.5" fill="none" />

      {/* 8 spokes outer (handles) */}
      <g stroke={ringColor} strokeOpacity="0.95" strokeWidth="2.4" strokeLinecap="round">
        <line x1="32" y1="6" x2="32" y2="14" />
        <line x1="32" y1="50" x2="32" y2="58" />
        <line x1="6" y1="32" x2="14" y2="32" />
        <line x1="50" y1="32" x2="58" y2="32" />
        <line x1="13.5" y1="13.5" x2="19.0" y2="19.0" />
        <line x1="45.0" y1="45.0" x2="50.5" y2="50.5" />
        <line x1="50.5" y1="13.5" x2="45.0" y2="19.0" />
        <line x1="13.5" y1="50.5" x2="19.0" y2="45.0" />
      </g>

      {/* inner spokes (radii) */}
      <g stroke={ringColor} strokeOpacity="0.75" strokeWidth="1.5" strokeLinecap="round">
        <line x1="32" y1="19" x2="32" y2="45" />
        <line x1="19" y1="32" x2="45" y2="32" />
        <line x1="22.8" y1="22.8" x2="41.2" y2="41.2" />
        <line x1="41.2" y1="22.8" x2="22.8" y2="41.2" />
      </g>

      {/* center hub */}
      <circle cx="32" cy="32" r="4.5" fill={tone === 'brand' ? 'url(#hi-hub)' : ringColor} />
      {tone === 'brand' && <circle cx="32" cy="32" r="2" fill="#1a3a8c" />}

      <style>{`
        @keyframes helmsman-spin {
          from { transform: rotate(0deg); transform-origin: 32px 32px; }
          to   { transform: rotate(360deg); transform-origin: 32px 32px; }
        }
      `}</style>
    </svg>
  );
}
