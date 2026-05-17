import { makeStyles, mergeClasses } from '@fluentui/react-components';
import { useEffect, useState } from 'react';

import { Pill, type PillKind } from '@/components/primitives/Pill';
import { StatusDot, type StatusKind } from '@/components/primitives/StatusDot';
import type { BotStatus, Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    position: 'relative',
    display: 'grid',
    gridTemplateColumns: 'auto 1fr auto',
    alignItems: 'center',
    gap: '20px',
    padding: '16px 20px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    overflow: 'hidden',
  },
  rootActive: {
    background:
      'linear-gradient(135deg, rgba(91,141,239,0.10) 0%, rgba(91,141,239,0.02) 50%, rgba(13,13,16,0) 100%), var(--bg-1)',
    border: '1px solid rgba(91, 141, 239, 0.35)',
  },
  rootFailed: {
    background:
      'linear-gradient(135deg, rgba(239,79,79,0.10) 0%, rgba(13,13,16,0) 70%), var(--bg-1)',
    border: '1px solid rgba(239, 79, 79, 0.35)',
  },
  beacon: {
    width: '40px',
    height: '40px',
    borderRadius: '999px',
    border: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-2)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '18px',
    fontWeight: 700,
    color: 'var(--text-2)',
    flexShrink: 0,
  },
  beaconActive: {
    color: 'var(--accent)',
    border: '1px solid var(--accent)',
    boxShadow: '0 0 0 4px rgba(91, 141, 239, 0.12)',
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: 0,
  },
  statusLine: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-1)',
    fontFamily: 'var(--font-mono)',
  },
  statusDesc: {
    fontSize: '12px',
    color: 'var(--text-2)',
    margin: 0,
  },
  metricsBlock: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
  },
  metricCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    textAlign: 'right',
  },
  metricLabel: {
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
  },
  metricValue: {
    fontFamily: 'var(--font-mono)',
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-1)',
    lineHeight: 1,
    fontVariantNumeric: 'tabular-nums',
    letterSpacing: '-0.02em',
  },
});

const STATUS_LABEL: Record<BotStatus, string> = {
  idle: 'STAND BY',
  connecting: 'JOINING',
  in_call: 'LISTENING',
  disconnected: 'DISCONNECTED',
  failed: 'FAILED',
};

const STATUS_DESC: Record<BotStatus, string> = {
  idle: 'Bot は待機中。会議 URL を貼って派遣してください。',
  connecting: 'Azure Communication Services に接続中…',
  in_call: '8 並列エージェントが議論を分析しています。',
  disconnected: '会議を退出しました。再派遣できます。',
  failed: 'Bot 派遣に失敗。URL またはテナント設定を確認。',
};

const STATUS_DOT: Record<BotStatus, StatusKind> = {
  idle: 'neutral',
  connecting: 'warning',
  in_call: 'active',
  disconnected: 'neutral',
  failed: 'danger',
};

const STATUS_PILL: Record<BotStatus, PillKind> = {
  idle: 'neutral',
  connecting: 'warning',
  in_call: 'success',
  disconnected: 'neutral',
  failed: 'danger',
};

interface Props {
  meeting: Meeting;
  liveUtteranceCount: number;
}

export function BotStatusStrip({ meeting, liveUtteranceCount }: Props) {
  const styles = useStyles();
  const status = meeting.bot_status;
  const pulsing = status === 'in_call' || status === 'connecting';
  const isActive = status === 'in_call';
  const isFailed = status === 'failed';

  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!pulsing) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [pulsing]);

  const startedAt = meeting.started_at ? new Date(meeting.started_at).getTime() : null;
  const elapsedSec = startedAt ? Math.max(0, Math.floor((now - startedAt) / 1000)) : 0;
  const totalSec = meeting.total_minutes * 60;
  const remainingSec = Math.max(0, totalSec - elapsedSec);
  const mm = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
  const ss = String(elapsedSec % 60).padStart(2, '0');
  const remainingMin = Math.floor(remainingSec / 60);

  return (
    <div
      className={mergeClasses(
        styles.root,
        'scanlines',
        isActive && styles.rootActive,
        isFailed && styles.rootFailed,
      )}
      aria-label="Bot status"
    >
      <div className={mergeClasses(styles.beacon, isActive && styles.beaconActive)}>
        🧭
      </div>

      <div className={styles.body}>
        <div className={styles.statusLine}>
          <StatusDot kind={STATUS_DOT[status]} pulse={pulsing} />
          <span>{STATUS_LABEL[status]}</span>
          <Pill kind={STATUS_PILL[status]}>{meeting.mode}</Pill>
        </div>
        <p className={styles.statusDesc}>{STATUS_DESC[status]}</p>
      </div>

      <div className={styles.metricsBlock}>
        <div className={styles.metricCol}>
          <span className={styles.metricLabel}>Elapsed</span>
          <span className={styles.metricValue}>
            {mm}:{ss}
          </span>
        </div>
        <div className={styles.metricCol}>
          <span className={styles.metricLabel}>Remaining</span>
          <span className={styles.metricValue}>{remainingMin}m</span>
        </div>
        <div className={styles.metricCol}>
          <span className={styles.metricLabel}>Utterances</span>
          <span className={styles.metricValue}>{liveUtteranceCount}</span>
        </div>
      </div>
    </div>
  );
}
