import { makeStyles, mergeClasses } from '@fluentui/react-components';
import { useEffect, useState } from 'react';

import type { BotTranscript, Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr auto',
    alignItems: 'center',
    gap: '14px',
    padding: '8px 16px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '8px',
    backgroundColor: 'var(--bg-1)',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '0.04em',
    minHeight: '32px',
    overflow: 'hidden',
  },
  rootActive: {
    background:
      'linear-gradient(90deg, rgba(92, 240, 245, 0.06) 0%, rgba(13, 13, 16, 0) 60%), var(--bg-1)',
    border: '1px solid rgba(92, 240, 245, 0.28)',
  },
  rootOffline: {
    opacity: 0.72,
  },
  leadDot: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontWeight: 700,
    color: 'var(--text-2)',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '999px',
    backgroundColor: 'var(--text-3)',
    flexShrink: 0,
  },
  dotLive: {
    backgroundColor: 'var(--accent-cyan)',
    boxShadow: '0 0 0 0 rgba(92, 240, 245, 0.55)',
    animationName: {
      '0%, 100%': {
        boxShadow: '0 0 0 0 rgba(92, 240, 245, 0.6)',
      },
      '50%': {
        boxShadow: '0 0 0 6px rgba(92, 240, 245, 0)',
      },
    },
    animationDuration: '2s',
    animationIterationCount: 'infinite',
    animationTimingFunction: 'ease-out',
    '@media (prefers-reduced-motion: reduce)': {
      animationName: 'none',
    },
  },
  liveLabel: {
    color: 'var(--accent-cyan)',
    letterSpacing: '0.12em',
  },
  liveLabelDim: {
    color: 'var(--text-3)',
  },
  facts: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
    alignItems: 'center',
    color: 'var(--text-2)',
    minWidth: 0,
  },
  fact: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    whiteSpace: 'nowrap',
  },
  factLabel: {
    color: 'var(--text-4)',
    textTransform: 'uppercase',
  },
  factValue: {
    color: 'var(--text-1)',
    fontVariantNumeric: 'tabular-nums',
  },
  factValueDim: {
    color: 'var(--text-3)',
  },
  trailing: {
    color: 'var(--text-3)',
    fontVariantNumeric: 'tabular-nums',
    textTransform: 'uppercase',
  },
});

interface Props {
  meeting: Meeting;
  transcript: BotTranscript | undefined;
  /** デフォルト 20s (Helmsman tick 周期と一致) */
  nudgeIntervalSec?: number;
}

function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

function secondsSince(iso: string | null, now: number): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.round((now - t) / 1000));
}

function formatAgo(sec: number | null): string {
  if (sec === null) return '—';
  if (sec < 5) return 'just now';
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}min ago`;
  const hr = Math.floor(min / 60);
  return `${hr}h ago`;
}

function lastSpeaker(transcript: BotTranscript | undefined): string | null {
  const u = transcript?.utterances ?? [];
  if (u.length === 0) return null;
  const last = u[u.length - 1];
  if (!last) return null;
  if (!last.speaker_id || last.speaker_id === 'unknown') return '—';
  return last.speaker_id;
}

export function RightNowStrip({
  meeting,
  transcript,
  nudgeIntervalSec = 20,
}: Props) {
  const styles = useStyles();
  const now = useNow(1000);

  const botInCall = meeting.bot_status === 'in_call';
  const lastDecisionAt = meeting.delivered_interventions
    .filter((d) => d.agent === 'DecisionCapture')
    .map((d) => d.delivered_at)
    .at(-1) ?? null;
  const decisionAgoSec = secondsSince(lastDecisionAt, now);

  const lastUtteranceIso = transcript?.utterances?.at(-1)?.started_at ?? null;
  const utteranceAgoSec = secondsSince(lastUtteranceIso, now);
  const speaker = lastSpeaker(transcript);

  // 次の tick (nudge) までの予想秒。bot_last_event_at から計算、なければ起動からの推定
  const lastEventAgoSec = secondsSince(meeting.bot_last_event_at, now);
  const sinceLastTick = lastEventAgoSec ?? utteranceAgoSec ?? null;
  const nextNudgeIn =
    sinceLastTick === null
      ? null
      : Math.max(0, nudgeIntervalSec - (sinceLastTick % nudgeIntervalSec));

  const liveLabel = botInCall ? 'LIVE' : 'STAND BY';
  const statusText = botInCall
    ? speaker
      ? `Listening · ${speaker} speaking · ${formatAgo(utteranceAgoSec)}`
      : 'Listening · awaiting first utterance'
    : 'awaiting dispatch';

  return (
    <div
      className={mergeClasses(
        styles.root,
        botInCall ? styles.rootActive : styles.rootOffline,
      )}
      aria-label="現在の動作状況"
      data-testid="right-now-strip"
    >
      <span className={styles.leadDot}>
        <span
          className={mergeClasses(styles.dot, botInCall && styles.dotLive)}
          aria-hidden
        />
        <span
          className={botInCall ? styles.liveLabel : styles.liveLabelDim}
        >
          {liveLabel}
        </span>
      </span>

      <span className={styles.facts}>
        <span className={styles.fact}>
          <span
            className={
              botInCall ? styles.factValue : styles.factValueDim
            }
          >
            {statusText}
          </span>
        </span>
        <span className={styles.fact}>
          <span className={styles.factLabel}>last decision</span>
          <span className={styles.factValue}>{formatAgo(decisionAgoSec)}</span>
        </span>
      </span>

      <span className={styles.trailing}>
        {botInCall && nextNudgeIn !== null
          ? `next nudge in ${nextNudgeIn}s`
          : `${meeting.delivered_interventions.length} delivered`}
      </span>
    </div>
  );
}
