/**
 * ParticipantsPanel (Phase 8) — 話者ごとに「直近発言 + 感情傾向」を一覧表示。
 *
 * データソース:
 *   - GET /meetings/{id}/tone → 話者ごとの dominant emotion + sentiment 平均
 *   - GET /meetings/{id}/bot/transcript → 各話者の直近発言テキスト
 *
 * 全体 mood meter もこのカードのヘッダーに併設 (個別 mood meter は作らない、UI 統合)。
 */
import { makeStyles } from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import { api, type EmotionLabel } from '@/lib/api';
import { EMOTION_STYLE, MOOD_STYLE } from '@/lib/tone';

const useStyles = makeStyles({
  root: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    backdropFilter: 'blur(12px) saturate(140%)',
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '14px',
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
    flexWrap: 'wrap',
  },
  title: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
  },
  moodBlock: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  moodLabel: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.08em',
    padding: '4px 10px',
    borderRadius: '999px',
    border: '1px solid currentColor',
  },
  moodHint: {
    fontSize: '11px',
    color: 'var(--text-3)',
  },
  sentimentBar: {
    position: 'relative',
    width: '120px',
    height: '4px',
    borderRadius: '999px',
    backgroundColor: 'var(--border-hairline)',
    overflow: 'visible',
  },
  sentimentMid: {
    position: 'absolute',
    top: '-2px',
    bottom: '-2px',
    left: '50%',
    width: '1px',
    backgroundColor: 'var(--text-4)',
  },
  sentimentMarker: {
    position: 'absolute',
    top: '-3px',
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    transform: 'translateX(-50%)',
    transitionProperty: 'left, background-color',
    transitionDuration: '400ms',
    transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '160px 1fr 80px',
    columnGap: '14px',
    alignItems: 'center',
    padding: '12px 18px',
    borderBottom: '1px solid var(--border-hairline)',
  },
  rowLast: {
    borderBottom: 'none',
  },
  speakerCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: 0,
  },
  speakerName: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-1)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  speakerSub: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.06em',
    color: 'var(--text-3)',
    textTransform: 'uppercase',
  },
  utterance: {
    fontSize: '12px',
    color: 'var(--text-2)',
    lineHeight: 1.55,
    margin: 0,
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  utteranceEmpty: {
    color: 'var(--text-4)',
    fontStyle: 'italic',
  },
  badgeCol: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '4px',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '2px 8px',
    borderRadius: '999px',
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    border: '1px solid currentColor',
  },
  streamRow: {
    display: 'flex',
    gap: '2px',
  },
  streamDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    border: '1px solid var(--border-hairline)',
  },
  empty: {
    padding: '32px 24px',
    textAlign: 'center',
    color: 'var(--text-3)',
    fontSize: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  emptyMark: {
    fontSize: '18px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-4)',
    letterSpacing: '0.1em',
  },
});

interface Props {
  meetingId: string;
  organizerId: string;
}

interface SpeakerRow {
  speakerId: string;
  displayName: string;
  dominantEmotion: EmotionLabel;
  sentimentAvg: number;
  recentEmotions: EmotionLabel[];
  sampleCount: number;
  lastUtterance: string | null;
}

export function ParticipantsPanel({ meetingId, organizerId }: Props) {
  const styles = useStyles();

  const { data: tone } = useQuery({
    queryKey: ['tone', meetingId, organizerId],
    queryFn: () => api.getMeetingTone(meetingId, organizerId),
    refetchInterval: 4000,
    retry: false,
  });

  const { data: transcript } = useQuery({
    queryKey: ['transcript', meetingId, organizerId],
    queryFn: () => api.getBotTranscript(meetingId, organizerId),
    refetchInterval: 3000,
  });

  // 話者ごとの直近発言 (最後の 1 件)
  const lastUtteranceBySpeaker = useMemo(() => {
    const m = new Map<string, string>();
    transcript?.utterances?.forEach((u) => {
      m.set(u.speaker_id, u.text);
    });
    return m;
  }, [transcript]);

  const rows: SpeakerRow[] = useMemo(() => {
    const moods = tone?.participant_moods ?? [];
    return moods.map((m) => ({
      speakerId: m.speaker_id,
      displayName: m.speaker_name || m.speaker_id.slice(0, 8),
      dominantEmotion: m.dominant_emotion,
      sentimentAvg: m.sentiment_avg,
      recentEmotions: m.recent_emotions,
      sampleCount: m.sample_count,
      lastUtterance: lastUtteranceBySpeaker.get(m.speaker_id) ?? null,
    }));
  }, [tone, lastUtteranceBySpeaker]);

  const overallMood = tone?.overall_mood ?? 'stuck';
  const moodStyle = MOOD_STYLE[overallMood];
  const overallSentiment = tone?.overall_sentiment ?? 0;
  const sentimentPct = Math.round(((overallSentiment + 1) / 2) * 100);
  const sentimentColor =
    overallSentiment > 0.15
      ? EMOTION_STYLE.joy.color
      : overallSentiment < -0.15
        ? EMOTION_STYLE.frustration.color
        : EMOTION_STYLE.neutral.color;

  return (
    <section className={styles.root} aria-label="参加者と感情">
      <div className={styles.header}>
        <h2 className={styles.title}>参加者と感情 · live</h2>
        <div className={styles.moodBlock}>
          <span className={styles.moodLabel} style={{ color: moodStyle.color }}>
            {moodStyle.emoji} {moodStyle.label}
          </span>
          <div
            className={styles.sentimentBar}
            role="progressbar"
            aria-valuenow={sentimentPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`全体 sentiment ${(overallSentiment).toFixed(2)}`}
          >
            <span className={styles.sentimentMid} />
            <span
              className={styles.sentimentMarker}
              style={{
                left: `${sentimentPct}%`,
                backgroundColor: sentimentColor,
                boxShadow: `0 0 8px ${sentimentColor}`,
              }}
            />
          </div>
          <span className={styles.moodHint}>{moodStyle.hint}</span>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className={styles.empty}>
          <span className={styles.emptyMark}>~</span>
          <span>感情データを待機中…</span>
          <span style={{ color: 'var(--text-4)', fontSize: 11 }}>
            発言が数件溜まると、話者ごとの傾向がここに出ます。
          </span>
        </div>
      ) : (
        <div className={styles.list}>
          {rows.map((r, i) => {
            const dom = EMOTION_STYLE[r.dominantEmotion];
            return (
              <div
                key={r.speakerId}
                className={`${styles.row}${i === rows.length - 1 ? ` ${styles.rowLast}` : ''}`}
              >
                <div className={styles.speakerCol}>
                  <span className={styles.speakerName}>{r.displayName}</span>
                  <span className={styles.speakerSub}>
                    {r.sampleCount} utt · sentiment {r.sentimentAvg.toFixed(2)}
                  </span>
                  <div className={styles.streamRow} aria-label="最近の感情の流れ">
                    {r.recentEmotions.map((e, idx) => (
                      <span
                        key={`${e}-${idx}`}
                        className={styles.streamDot}
                        style={{ backgroundColor: EMOTION_STYLE[e].color }}
                        title={EMOTION_STYLE[e].label}
                      />
                    ))}
                  </div>
                </div>
                <p
                  className={`${styles.utterance}${r.lastUtterance ? '' : ` ${styles.utteranceEmpty}`}`}
                >
                  {r.lastUtterance ?? '(直近の発言なし)'}
                </p>
                <div className={styles.badgeCol}>
                  <span className={styles.badge} style={{ color: dom.color }}>
                    {dom.emoji} {dom.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
