import { Caption1, makeStyles, tokens } from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';

import { Section } from '@/components/primitives/Section';
import { api } from '@/lib/api';

const useStyles = makeStyles({
  feed: {
    display: 'flex',
    flexDirection: 'column',
    maxHeight: '260px',
    overflowY: 'auto',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '64px 1fr',
    columnGap: '12px',
    padding: '8px 16px',
    fontSize: '13px',
    lineHeight: 1.5,
  },
  ts: {
    fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
    fontVariantNumeric: 'tabular-nums',
    paddingTop: '2px',
  },
  text: {
    color: tokens.colorNeutralForeground1,
    margin: 0,
  },
  empty: {
    padding: '24px 16px',
    textAlign: 'center',
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
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
    <Section
      title="ライブ転写"
      trailing={
        <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
          {data?.bot_active ? `${data.utterance_count}` : 'idle'}
        </Caption1>
      }
      bare
    >
      <div className={styles.feed}>
        {!data?.utterances?.length ? (
          <p className={styles.empty}>
            {data?.bot_active
              ? 'Bot は会議にいますが、まだ発言を拾っていません。'
              : 'Bot を Teams 会議に派遣すると、発言がここに表示されます。'}
          </p>
        ) : (
          data.utterances.map((u) => (
            <div key={u.id} className={styles.row}>
              <span className={styles.ts}>{fmtTime(u.started_at)}</span>
              <p className={styles.text}>{u.text}</p>
            </div>
          ))
        )}
      </div>
    </Section>
  );
}
