/**
 * CountUp — 数値の change 時にスムーズに値を count up/down するアニメ。
 * 0.4s ease-out で線形補間。
 */
import { useEffect, useRef, useState } from 'react';

interface Props {
  value: number;
  durationMs?: number;
  fmt?: (v: number) => string;
  className?: string;
}

export function CountUp({ value, durationMs = 400, fmt, className }: Props) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = display;
    const to = value;
    if (from === to) return;
    fromRef.current = from;
    const start = performance.now();

    const step = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - t, 3);
      const current = from + (to - from) * eased;
      setDisplay(current);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        setDisplay(to);
      }
    };

    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, durationMs]);

  const isInt = Number.isInteger(value);
  const formatted = fmt
    ? fmt(display)
    : isInt
      ? Math.round(display).toLocaleString()
      : display.toFixed(2);

  return <span className={className}>{formatted}</span>;
}
