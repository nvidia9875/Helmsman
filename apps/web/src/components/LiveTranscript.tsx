import { makeStyles } from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useRef } from 'react';

import { StatusDot } from '@/components/primitives/StatusDot';
import { api, type EmotionLabel } from '@/lib/api';
import { EMOTION_STYLE } from '@/lib/tone';

const useStyles = makeStyles({
  root: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    backdropFilter: 'blur(12px) saturate(140%)',
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    minHeight: '320px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
  },
  title: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  meta: {
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  feed: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    maxHeight: '560px',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '72px 1fr',
    columnGap: '12px',
    padding: '10px 18px',
    fontSize: '13px',
    lineHeight: 1.5,
    borderBottom: '1px solid var(--border-hairline)',
  },
  rowLast: {
    borderBottom: 'none',
  },
  ts: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-3)',
    fontVariantNumeric: 'tabular-nums',
    paddingTop: '2px',
  },
  speakerLine: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '2px',
  },
  speaker: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
  },
  emotionBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '1px 7px',
    borderRadius: '999px',
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    border: '1px solid currentColor',
    backgroundColor: 'transparent',
  },
  text: {
    color: 'var(--text-1)',
    margin: 0,
  },
  empty: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 24px',
    color: 'var(--text-3)',
    fontSize: '13px',
    gap: '6px',
  },
  emptyMark: {
    fontSize: '20px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-4)',
    letterSpacing: '0.1em',
  },
});

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

interface Props {
  meetingId: string;
  organizerId: string;
}

export function LiveTranscript({ meetingId, organizerId }: Props) {
  const styles = useStyles();
  const { data } = useQuery({
    queryKey: ['transcript', meetingId, organizerId],
    queryFn: () => api.getBotTranscript(meetingId, organizerId),
    refetchInterval: 3000,
  });

  // 感情ラベル: tick で ToneAgent が分類した結果を polling
  const { data: tone } = useQuery({
    queryKey: ['tone', meetingId, organizerId],
    queryFn: () => api.getMeetingTone(meetingId, organizerId),
    refetchInterval: 4000,
    retry: false,
  });

  // utterance_id → emotion / speaker_name 辞書 (lookup を O(1) に)
  const toneByUtterance = useMemo(() => {
    const m = new Map<string, { emotion: EmotionLabel; speakerName: string | null }>();
    tone?.per_utterance?.forEach((t) =>
      m.set(t.utterance_id, { emotion: t.emotion, speakerName: t.speaker_name }),
    );
    return m;
  }, [tone]);

  const feedRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [data?.utterance_count]);

  return (
    <section className={styles.root} aria-label="ライブ転写">
      <div className={styles.header}>
        <h2 className={styles.title}>
          <StatusDot kind={data?.bot_active ? 'active' : 'neutral'} pulse={data?.bot_active} />
          Live transcript
        </h2>
        <span className={styles.meta}>
          {data?.bot_active ? `${data.utterance_count} utterances` : 'idle'}
        </span>
      </div>

      {!data?.utterances?.length ? (
        <div className={styles.empty}>
          <span className={styles.emptyMark}>~</span>
          <span>
            {data?.bot_active ? 'listening…' : 'no audio yet'}
          </span>
          <span style={{ color: 'var(--text-4)', fontSize: 11 }}>
            {data?.bot_active
              ? 'Bot は会議にいます。発言を待機中。'
              : 'Bot を派遣すると発言がここに流れます。'}
          </span>
        </div>
      ) : (
        <div className={styles.feed} ref={feedRef}>
          {data.utterances.map((u, i) => {
            const t = toneByUtterance.get(u.id);
            const style = t ? EMOTION_STYLE[t.emotion] : null;
            const speakerLabel = t?.speakerName || u.speaker_id.slice(0, 8);
            return (
              <div
                key={u.id}
                className={`${styles.row}${i === data.utterances.length - 1 ? ` ${styles.rowLast}` : ''}`}
              >
                <span className={styles.ts}>{fmtTime(u.started_at)}</span>
                <div>
                  <div className={styles.speakerLine}>
                    <span className={styles.speaker}>{speakerLabel}</span>
                    {style && (
                      <span
                        className={styles.emotionBadge}
                        style={{ color: style.color }}
                        aria-label={`感情: ${style.label}`}
                      >
                        {style.emoji} {style.label}
                      </span>
                    )}
                  </div>
                  <p className={styles.text}>{u.text}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
