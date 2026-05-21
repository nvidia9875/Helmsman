import {
  Body1,
  Caption1,
  Title2,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useEffect, useState } from 'react';

import { HelmsmanIcon } from '@/components/primitives/HelmsmanIcon';
import type { BotStatus, Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    borderRadius: tokens.borderRadiusXLarge,
    padding: '24px 28px',
    color: '#fff',
    display: 'grid',
    gridTemplateColumns: 'auto 1fr auto',
    gap: '20px',
    alignItems: 'center',
    boxShadow: tokens.shadow16,
    position: 'relative',
    overflow: 'hidden',
  },
  active: {
    background: 'linear-gradient(135deg, #0078d4 0%, #1d4ed8 60%, #312e81 100%)',
  },
  connecting: {
    background: 'linear-gradient(135deg, #b45309 0%, #d97706 60%, #92400e 100%)',
  },
  idle: {
    background: 'linear-gradient(135deg, #4b5563 0%, #1f2937 60%, #111827 100%)',
  },
  failed: {
    background: 'linear-gradient(135deg, #b91c1c 0%, #7f1d1d 60%, #450a0a 100%)',
  },
  haloWrap: {
    width: '64px',
    height: '64px',
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  halo: {
    position: 'absolute',
    width: '64px',
    height: '64px',
    borderRadius: '50%',
    backgroundColor: 'rgba(255,255,255,0.18)',
    animationName: {
      from: { transform: 'scale(1)', opacity: 0.7 },
      to: { transform: 'scale(1.8)', opacity: 0 },
    },
    animationDuration: '2.2s',
    animationIterationCount: 'infinite',
    animationTimingFunction: 'ease-out',
  },
  icon: {
    fontSize: '36px',
    zIndex: 1,
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: 0,
  },
  status: {
    color: 'rgba(255,255,255,0.85)',
    letterSpacing: '0.02em',
    textTransform: 'uppercase',
    fontSize: '11px',
    fontWeight: 600,
  },
  headline: {
    color: '#fff',
    margin: 0,
    fontSize: '24px',
    fontWeight: 600,
    lineHeight: 1.2,
  },
  subtext: {
    color: 'rgba(255,255,255,0.75)',
    marginTop: '2px',
  },
  metrics: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    textAlign: 'right',
    color: '#fff',
  },
  metricBig: {
    fontSize: '28px',
    fontWeight: 700,
    lineHeight: 1,
    fontVariantNumeric: 'tabular-nums',
  },
  metricSmall: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: '11px',
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
  },
  progressTrack: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '4px',
    backgroundColor: 'rgba(255,255,255,0.15)',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#fff',
    transitionProperty: 'width',
    transitionDuration: '500ms',
    transitionTimingFunction: 'ease-out',
  },
});

interface Props {
  meeting: Meeting;
  liveUtteranceCount: number;
}

function statusVariant(s: BotStatus): 'active' | 'connecting' | 'idle' | 'failed' {
  if (s === 'in_call') return 'active';
  if (s === 'connecting') return 'connecting';
  if (s === 'failed') return 'failed';
  return 'idle';
}

function statusTitle(s: BotStatus): { label: string; headline: string; subtext: string } {
  switch (s) {
    case 'in_call':
      return {
        label: 'LISTENING',
        headline: 'Helmsman は会議に参加しています',
        subtext: '8 つのエージェントが並列で議論を分析中',
      };
    case 'connecting':
      return {
        label: 'JOINING',
        headline: 'Teams 会議に接続中…',
        subtext: 'ACS Call Automation で参加リクエスト送信済み',
      };
    case 'failed':
      return {
        label: 'ERROR',
        headline: 'Bot の参加に失敗しました',
        subtext: '会議 URL の形式 or Teams テナント設定を確認',
      };
    case 'disconnected':
      return {
        label: 'IDLE',
        headline: '会議を退出しました',
        subtext: '次の会議で Bot を再招待できます',
      };
    default:
      return {
        label: 'STAND BY',
        headline: 'Helmsman を起動する準備ができています',
        subtext: '下のフォームに Teams 会議 URL を貼ってください',
      };
  }
}

export function BotMissionCard({ meeting, liveUtteranceCount }: Props) {
  const styles = useStyles();
  const variant = statusVariant(meeting.bot_status);
  const { label, headline, subtext } = statusTitle(meeting.bot_status);

  // 経過時間 (会議開始 → 現在)
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const startedAt = meeting.started_at ? new Date(meeting.started_at).getTime() : null;
  const elapsedSec = startedAt ? Math.max(0, Math.floor((now - startedAt) / 1000)) : 0;
  const totalSec = meeting.total_minutes * 60;
  const elapsedPct = totalSec > 0 ? Math.min(100, (elapsedSec / totalSec) * 100) : 0;
  const mm = Math.floor(elapsedSec / 60);
  const ss = String(elapsedSec % 60).padStart(2, '0');

  const isPulsing = meeting.bot_status === 'in_call' || meeting.bot_status === 'connecting';

  return (
    <section
      className={`${styles.root} ${styles[variant]}`}
      aria-label="Helmsman Bot ステータス"
    >
      <div className={styles.haloWrap}>
        {isPulsing && <span className={styles.halo} />}
        <span className={styles.icon}>
          <HelmsmanIcon size={44} tone="brand" spin={isPulsing} />
        </span>
      </div>

      <div className={styles.body}>
        <span className={styles.status}>{label}</span>
        <Title2 as="h2" className={styles.headline}>
          {headline}
        </Title2>
        <Body1 className={styles.subtext}>{subtext}</Body1>
      </div>

      {meeting.bot_status === 'in_call' && (
        <div className={styles.metrics}>
          <span className={styles.metricBig}>
            {String(mm).padStart(2, '0')}:{ss}
          </span>
          <span className={styles.metricSmall}>elapsed / {meeting.total_minutes} min</span>
          <Caption1 style={{ color: 'rgba(255,255,255,0.85)', marginTop: 8 }}>
            🎤 {liveUtteranceCount} 発言キャプチャ
          </Caption1>
        </div>
      )}

      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: `${elapsedPct}%` }} />
      </div>
      {/* unused but defined */}
      <span style={{ display: 'none' }}>
        <Title3>{label}</Title3>
      </span>
    </section>
  );
}
