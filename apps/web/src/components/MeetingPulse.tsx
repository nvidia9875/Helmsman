import { Badge, makeStyles } from '@fluentui/react-components';
import {
  ArrowTrending24Regular,
  CompassNorthwestRegular,
  People24Regular,
} from '@fluentui/react-icons';
import { useMemo } from 'react';

import type { BotTranscript, Meeting, Topic, Utterance } from '@/lib/api';
import { gini, giniBand, giniLabel } from '@/lib/gini';

const useStyles = makeStyles({
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '14px',
    '@media (max-width: 1100px)': {
      gridTemplateColumns: '1fr',
    },
  },
  card: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    backdropFilter: 'blur(12px) saturate(140%)',
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
    padding: '16px 18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    minHeight: '180px',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
  },
  count: {
    fontSize: '10px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
  },
  emptyHint: {
    color: 'var(--text-3)',
    fontSize: '12px',
    fontStyle: 'italic',
  },

  // --- temperature card ---
  temperatureRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '10px',
  },
  temperatureValue: {
    fontSize: '24px',
    fontWeight: 600,
    color: 'var(--text-1)',
    letterSpacing: '-0.01em',
  },
  temperatureSub: {
    fontSize: '12px',
    color: 'var(--text-3)',
  },
  temperatureBar: {
    height: '4px',
    borderRadius: '2px',
    backgroundColor: 'var(--bg-3)',
    overflow: 'hidden',
    position: 'relative',
  },
  temperatureBarFill: {
    height: '100%',
    transitionProperty: 'width, background-color',
    transitionDuration: '300ms',
  },
  focusLabel: {
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    marginTop: '6px',
  },
  focusName: {
    fontSize: '14px',
    color: 'var(--text-1)',
    fontWeight: 500,
    lineHeight: 1.4,
  },
  focusQuote: {
    fontSize: '12px',
    color: 'var(--text-3)',
    fontStyle: 'italic',
    borderLeft: '2px solid var(--border-default)',
    paddingLeft: '8px',
    marginTop: '4px',
    lineHeight: 1.5,
  },

  // --- topics card ---
  topicList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  topicRow: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    gap: '10px',
    alignItems: 'center',
    padding: '8px 10px',
    borderRadius: '6px',
    backgroundColor: 'var(--bg-2)',
    border: '1px solid var(--border-hairline)',
  },
  topicName: {
    fontSize: '13px',
    color: 'var(--text-1)',
    fontWeight: 500,
    lineHeight: 1.35,
  },

  // --- participants card ---
  participantList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  participantRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    gap: '10px',
    alignItems: 'center',
    padding: '6px 0',
  },
  participantName: {
    fontSize: '13px',
    color: 'var(--text-1)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  participantBar: {
    height: '4px',
    borderRadius: '2px',
    backgroundColor: 'var(--bg-3)',
    overflow: 'hidden',
    marginTop: '4px',
  },
  participantBarFill: {
    height: '100%',
    backgroundColor: 'var(--accent)',
    transitionProperty: 'width',
    transitionDuration: '300ms',
  },
  participantStat: {
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    fontVariantNumeric: 'tabular-nums',
  },
  equityRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
    padding: '6px 8px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '6px',
    backgroundColor: 'var(--bg-2)',
    marginBottom: '6px',
  },
  equityLabel: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
  },
  equityValue: {
    fontSize: '12px',
    fontFamily: 'var(--font-mono)',
    fontVariantNumeric: 'tabular-nums',
    color: 'var(--text-1)',
    fontWeight: 600,
  },
  equityBand: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  equityBandBalanced: {
    backgroundColor: 'rgba(43, 196, 138, 0.14)',
    color: 'var(--success)',
  },
  equityBandMild: {
    backgroundColor: 'rgba(245, 165, 36, 0.14)',
    color: 'var(--warning)',
  },
  equityBandSkewed: {
    backgroundColor: 'rgba(239, 79, 79, 0.14)',
    color: 'var(--danger)',
  },
});

type TemperatureLevel = 'cool' | 'warm' | 'hot' | 'tense';

interface TemperatureSignal {
  level: TemperatureLevel;
  label: string;
  sub: string;
  fillPct: number;
  color: string;
}

function computeTemperature(meeting: Meeting): TemperatureSignal {
  const density = meeting.recent_utterance_density ?? 0;
  const dissentCount = meeting.delivered_interventions.filter(
    (d) => d.agent === 'DissentSurface',
  ).length;
  const recentInterventions = meeting.delivered_interventions.slice(-5);
  const recentDissent = recentInterventions.some(
    (d) => d.agent === 'DissentSurface',
  );

  // tense: 直近に Dissent + 高密度
  if (recentDissent && density > 0.5) {
    return {
      level: 'tense',
      label: '緊張感',
      sub: '反対意見 / 同意過剰の検知あり',
      fillPct: Math.min(95, 70 + density * 25),
      color: '#ef4f4f',
    };
  }
  // hot: 高密度 + 多介入
  if (density > 0.7 || recentInterventions.length >= 4) {
    return {
      level: 'hot',
      label: '活発',
      sub: '議論密度が高い、複数論点が並走',
      fillPct: Math.min(95, 55 + density * 35),
      color: '#f5a524',
    };
  }
  // warm: 中密度 or 進行順調
  if (density > 0.3 || meeting.delivered_interventions.length > 0) {
    return {
      level: 'warm',
      label: '進行中',
      sub:
        dissentCount > 0
          ? '懸念点も拾えている'
          : '安定して議論が進んでいる',
      fillPct: 30 + density * 40,
      color: '#5b8def',
    };
  }
  // cool: 低密度 or 静か
  return {
    level: 'cool',
    label: '静観',
    sub: '会議が立ち上がり中、または小休止',
    fillPct: 15,
    color: '#9a9aac',
  };
}

const PRIORITY_RANK: Record<string, number> = {
  Critical: 0,
  Important: 1,
  Optional: 2,
};

const PRIORITY_COLOR: Record<
  string,
  'danger' | 'warning' | 'subtle' | 'informative'
> = {
  Critical: 'danger',
  Important: 'warning',
  Optional: 'subtle',
};

const STATE_LABEL: Record<string, string> = {
  not_started: '未着手',
  discussing: '議論中',
  deep_dive: '深掘り',
  decided: '決定済',
};

function formatRelative(iso: string | null): string {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 30) return 'たった今';
  if (diff < 60) return `${Math.round(diff)} 秒前`;
  if (diff < 3600) return `${Math.round(diff / 60)} 分前`;
  if (diff < 86400) return `${Math.round(diff / 3600)} 時間前`;
  return new Date(iso).toLocaleDateString();
}

interface ParticipantStat {
  speakerId: string;
  utteranceCount: number;
  totalChars: number;
  lastSpokeIso: string | null;
}

function aggregateParticipants(utterances: Utterance[]): ParticipantStat[] {
  const map = new Map<string, ParticipantStat>();
  for (const u of utterances) {
    const existing = map.get(u.speaker_id);
    if (existing) {
      existing.utteranceCount += 1;
      existing.totalChars += u.text.length;
      if (
        !existing.lastSpokeIso ||
        new Date(u.started_at) > new Date(existing.lastSpokeIso)
      ) {
        existing.lastSpokeIso = u.started_at;
      }
    } else {
      map.set(u.speaker_id, {
        speakerId: u.speaker_id,
        utteranceCount: 1,
        totalChars: u.text.length,
        lastSpokeIso: u.started_at,
      });
    }
  }
  return [...map.values()].sort(
    (a, b) => b.utteranceCount - a.utteranceCount,
  );
}

interface Props {
  meeting: Meeting;
  transcript: BotTranscript | undefined;
}

export function MeetingPulse({ meeting, transcript }: Props) {
  const styles = useStyles();

  const temperature = useMemo(() => computeTemperature(meeting), [meeting]);

  // 議論中 / 深掘り 中の topic を「現在の焦点」として抽出 (deep_dive 優先)
  const focusTopic = useMemo<Topic | null>(() => {
    const deepDive = meeting.topics.find((t) => t.state === 'deep_dive');
    if (deepDive) return deepDive;
    const discussing = meeting.topics.find((t) => t.state === 'discussing');
    return discussing ?? null;
  }, [meeting.topics]);

  // 未着手 topic を priority 順
  const nextTopics = useMemo(() => {
    return meeting.topics
      .filter((t) => t.state === 'not_started')
      .sort(
        (a, b) =>
          (PRIORITY_RANK[a.priority] ?? 99) -
          (PRIORITY_RANK[b.priority] ?? 99),
      );
  }, [meeting.topics]);

  const participants = useMemo(
    () => aggregateParticipants(transcript?.utterances ?? []),
    [transcript],
  );
  const maxUtter = participants[0]?.utteranceCount ?? 1;

  const equity = useMemo(() => {
    if (participants.length < 2) return null;
    const value = gini(participants.map((p) => p.utteranceCount));
    const band = giniBand(value);
    return { value, band, label: giniLabel(band) };
  }, [participants]);

  const equityBandClass =
    equity?.band === 'balanced'
      ? styles.equityBandBalanced
      : equity?.band === 'mild'
        ? styles.equityBandMild
        : styles.equityBandSkewed;

  return (
    <div className={styles.grid}>
      {/* Temperature + focus */}
      <section className={styles.card} aria-label="議論の温度と方向性">
        <div className={styles.cardHeader}>
          <span className={styles.cardTitle}>
            <ArrowTrending24Regular /> 議論の温度
          </span>
          <span className={styles.count}>{temperature.level.toUpperCase()}</span>
        </div>
        <div>
          <div className={styles.temperatureRow}>
            <span className={styles.temperatureValue}>{temperature.label}</span>
            <span className={styles.temperatureSub}>{temperature.sub}</span>
          </div>
          <div className={styles.temperatureBar} style={{ marginTop: 10 }}>
            <div
              className={styles.temperatureBarFill}
              style={{
                width: `${temperature.fillPct}%`,
                backgroundColor: temperature.color,
              }}
            />
          </div>
        </div>
        <div>
          <div className={styles.focusLabel}>
            <CompassNorthwestRegular
              style={{ width: 14, height: 14, verticalAlign: -3 }}
            />{' '}
            現在の焦点
          </div>
          {focusTopic ? (
            <>
              <div className={styles.focusName}>{focusTopic.name}</div>
              {focusTopic.evidence_quote && (
                <div className={styles.focusQuote}>
                  「{focusTopic.evidence_quote}」
                </div>
              )}
              <div className={styles.participantStat} style={{ marginTop: 4 }}>
                {STATE_LABEL[focusTopic.state]} ·{' '}
                {formatRelative(focusTopic.last_mention_at)}
              </div>
            </>
          ) : (
            <div className={styles.emptyHint}>
              論点はまだ議論段階に入っていません
            </div>
          )}
        </div>
      </section>

      {/* Suggested next topics */}
      <section className={styles.card} aria-label="次に話してほしい論点">
        <div className={styles.cardHeader}>
          <span className={styles.cardTitle}>
            <CompassNorthwestRegular /> 次に促す論点
          </span>
          <span className={styles.count}>{nextTopics.length}</span>
        </div>
        {nextTopics.length === 0 ? (
          <div className={styles.emptyHint}>
            {meeting.topics.length === 0
              ? 'ゴール未設定 — 監視のみモード'
              : '全論点をカバー中 ✓'}
          </div>
        ) : (
          <div className={styles.topicList}>
            {nextTopics.slice(0, 5).map((t) => (
              <div key={t.id} className={styles.topicRow}>
                <Badge
                  appearance="filled"
                  color={PRIORITY_COLOR[t.priority] ?? 'subtle'}
                  size="small"
                >
                  {t.priority}
                </Badge>
                <span className={styles.topicName}>{t.name}</span>
              </div>
            ))}
            {nextTopics.length > 5 && (
              <span className={styles.count}>
                +{nextTopics.length - 5} 件
              </span>
            )}
          </div>
        )}
      </section>

      {/* Participants */}
      <section className={styles.card} aria-label="参加者の動き">
        <div className={styles.cardHeader}>
          <span className={styles.cardTitle}>
            <People24Regular /> 参加者の動き
          </span>
          <span className={styles.count}>{participants.length}</span>
        </div>
        {participants.length === 0 ? (
          <div className={styles.emptyHint}>
            {transcript?.bot_active
              ? '発言を待機中…'
              : 'Bot 派遣後に発言データが集まります'}
          </div>
        ) : (
          <div className={styles.participantList}>
            {equity && (
              <div
                className={styles.equityRow}
                aria-label="発言量の偏り (Gini 係数)"
                title="0 = 完全平等, 1 = 1 人独占。Quiet Activator の発火閾値と整合"
              >
                <span className={styles.equityLabel}>Equity (Gini)</span>
                <span className={styles.equityValue}>
                  {equity.value.toFixed(2)}
                </span>
                <span
                  className={`${styles.equityBand} ${equityBandClass}`}
                >
                  {equity.label}
                </span>
              </div>
            )}
            {participants.slice(0, 6).map((p) => (
              <div key={p.speakerId}>
                <div className={styles.participantRow}>
                  <span className={styles.participantName} title={p.speakerId}>
                    {p.speakerId === 'unknown' ? '名前未解決' : p.speakerId}
                  </span>
                  <span className={styles.participantStat}>
                    {p.utteranceCount} 発言 · {formatRelative(p.lastSpokeIso)}
                  </span>
                </div>
                <div className={styles.participantBar}>
                  <div
                    className={styles.participantBarFill}
                    style={{
                      width: `${Math.max(8, (p.utteranceCount / maxUtter) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
            {participants.length > 6 && (
              <span className={styles.count}>+{participants.length - 6} 名</span>
            )}
          </div>
        )}
      </section>

    </div>
  );
}
