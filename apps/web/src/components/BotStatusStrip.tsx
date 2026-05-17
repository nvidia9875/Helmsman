import { Caption1, makeStyles, mergeClasses, tokens } from '@fluentui/react-components';
import { useEffect, useState } from 'react';

import type { BotStatus, Meeting } from '@/lib/api';
import { Pill, type PillKind } from '@/components/primitives/Pill';
import { StatusDot, type StatusKind } from '@/components/primitives/StatusDot';

const useStyles = makeStyles({
  root: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    alignItems: 'center',
    gap: '16px',
    padding: '12px 16px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: '8px',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    minWidth: 0,
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    fontWeight: 500,
    color: tokens.colorNeutralForeground1,
  },
  separator: {
    width: '1px',
    height: '14px',
    backgroundColor: tokens.colorNeutralStroke2,
  },
  meta: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
    fontVariantNumeric: 'tabular-nums',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  pulse: {
    color: tokens.colorBrandForeground1,
  },
});

const STATUS_LABEL: Record<BotStatus, string> = {
  idle: 'STAND BY',
  connecting: 'JOINING',
  in_call: 'LISTENING',
  disconnected: 'DISCONNECTED',
  failed: 'FAILED',
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

  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!pulsing) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [pulsing]);
  const startedAt = meeting.started_at ? new Date(meeting.started_at).getTime() : null;
  const elapsedSec = startedAt ? Math.max(0, Math.floor((now - startedAt) / 1000)) : 0;
  const mm = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
  const ss = String(elapsedSec % 60).padStart(2, '0');

  return (
    <div className={styles.root} aria-label="Bot status">
      <div className={styles.left}>
        <div className={mergeClasses(styles.status, pulsing && styles.pulse)}>
          <StatusDot kind={STATUS_DOT[status]} pulse={pulsing} />
          <span>{STATUS_LABEL[status]}</span>
        </div>
        <span className={styles.separator} />
        <Caption1 className={styles.meta}>
          {mm}:{ss} / {meeting.total_minutes} min
        </Caption1>
        {status === 'in_call' && (
          <>
            <span className={styles.separator} />
            <Caption1 className={styles.meta}>{liveUtteranceCount} utterances</Caption1>
          </>
        )}
      </div>
      <div className={styles.right}>
        <Pill kind={STATUS_PILL[status]}>{meeting.mode}</Pill>
      </div>
    </div>
  );
}
