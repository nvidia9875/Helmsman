/**
 * Minimal inline-SVG area chart — no chart library, fits in any container.
 * Designed for KPI rows where a 60-260px width sparkline-ish area is enough
 * to show a 30-day trend.
 */
interface Point {
  label: string;
  value: number;
}

interface Props {
  data: Point[];
  width?: number;
  height?: number;
  /** Stroke color; CSS var or hex. Defaults to brand accent. */
  stroke?: string;
  /** Fill gradient top color (semi-transparent). */
  fill?: string;
  /** Show numeric axis labels on left edge. */
  showAxis?: boolean;
  className?: string;
}

export function AreaChart({
  data,
  width = 480,
  height = 120,
  stroke = 'var(--accent)',
  fill = 'rgba(91, 141, 239, 0.16)',
  showAxis = false,
  className,
}: Props) {
  if (data.length === 0) {
    return (
      <svg width={width} height={height} className={className} aria-hidden>
        <text
          x={width / 2}
          y={height / 2}
          textAnchor="middle"
          fontSize="11"
          fill="var(--text-3)"
        >
          no data
        </text>
      </svg>
    );
  }

  const padding = { top: 8, right: 8, bottom: 18, left: showAxis ? 28 : 8 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const max = Math.max(...data.map((d) => d.value), 0.0001);
  const min = 0;
  const range = Math.max(max - min, 0.0001);

  const step = data.length > 1 ? innerW / (data.length - 1) : innerW;

  const points = data.map((d, i) => {
    const x = padding.left + i * step;
    const y = padding.top + innerH - ((d.value - min) / range) * innerH;
    return { x, y, d };
  });

  const lineD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(' ');
  const areaD = `${lineD} L ${points[points.length - 1].x.toFixed(2)} ${(padding.top + innerH).toFixed(2)} L ${points[0].x.toFixed(2)} ${(padding.top + innerH).toFixed(2)} Z`;

  // 4 horizontal gridlines
  const gridY = [0, 0.25, 0.5, 0.75, 1].map((p) => padding.top + innerH * (1 - p));

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className={className} aria-hidden>
      {/* gridlines */}
      {gridY.map((y, i) => (
        <line
          key={`g${i}`}
          x1={padding.left}
          x2={padding.left + innerW}
          y1={y}
          y2={y}
          stroke="var(--border-hairline)"
          strokeDasharray={i === gridY.length - 1 ? '0' : '2 4'}
          strokeWidth="1"
        />
      ))}

      {/* y-axis labels */}
      {showAxis && (
        <>
          <text
            x={padding.left - 6}
            y={padding.top + 4}
            textAnchor="end"
            fontSize="10"
            fill="var(--text-3)"
            fontFamily="var(--font-mono)"
          >
            {max < 1 ? max.toFixed(3) : max.toFixed(2)}
          </text>
          <text
            x={padding.left - 6}
            y={padding.top + innerH}
            textAnchor="end"
            fontSize="10"
            fill="var(--text-3)"
            fontFamily="var(--font-mono)"
          >
            0
          </text>
        </>
      )}

      {/* area + line */}
      <path d={areaD} fill={fill} />
      <path d={lineD} fill="none" stroke={stroke} strokeWidth="1.5" />

      {/* anchor dots on hover targets — invisible but accessible via title */}
      {points.map((p, i) => (
        <g key={`p${i}`}>
          <circle cx={p.x} cy={p.y} r="2" fill={stroke}>
            <title>{`${p.d.label}: ${p.d.value}`}</title>
          </circle>
        </g>
      ))}

      {/* x-axis end labels */}
      <text
        x={padding.left}
        y={height - 4}
        fontSize="10"
        fill="var(--text-3)"
        fontFamily="var(--font-mono)"
      >
        {data[0]?.label}
      </text>
      <text
        x={padding.left + innerW}
        y={height - 4}
        textAnchor="end"
        fontSize="10"
        fill="var(--text-3)"
        fontFamily="var(--font-mono)"
      >
        {data[data.length - 1]?.label}
      </text>
    </svg>
  );
}
