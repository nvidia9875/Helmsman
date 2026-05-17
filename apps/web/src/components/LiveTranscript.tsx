import {
  Body1,
  Caption1,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '16px',
    marginTop: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  log: {
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
    padding: '12px',
    maxHeight: '260px',
    overflowY: 'auto',
    fontFamily: tokens.fontFamilyMonospace,
    fontSize: '13px',
    lineHeight: 1.6,
  },
  utteranceRow: {
    display: 'grid',
    gridTemplateColumns: '70px 1fr',
    gap: '8px',
    padding: '2px 0',
  },
  ts: {
    color: tokens.colorNeutralForeground3,
    fontVariantNumeric: 'tabular-nums',
  },
  empty: {
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
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

  return (
    <section className={styles.root} aria-label="ライブ発言ログ">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <Title3 as="h2" style={{ margin: 0 }}>
          🎤 ライブ発言ログ (Bot 経由)
        </Title3>
        <Caption1>
          {data?.bot_active ? `${data.utterance_count} 発言` : '(Bot 未接続)'}
        </Caption1>
      </div>
      <div className={styles.log}>
        {!data?.utterances?.length ? (
          <Body1 className={styles.empty}>
            {data?.bot_active
              ? '(Bot は会議にいますが、まだ発言を拾っていません)'
              : 'Bot を Teams 会議に招待すると、発言がここにリアルタイム表示されます'}
          </Body1>
        ) : (
          data.utterances.map((u) => (
            <div key={u.id} className={styles.utteranceRow}>
              <span className={styles.ts}>{fmtTime(u.started_at)}</span>
              <span>{u.text}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
