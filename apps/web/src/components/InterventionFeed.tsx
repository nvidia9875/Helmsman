import { Caption1, makeStyles, tokens } from '@fluentui/react-components';

import { LevelBar } from '@/components/primitives/LevelBar';
import { Section } from '@/components/primitives/Section';
import type { InterventionDelivery, Meeting } from '@/lib/api';

const useStyles = makeStyles({
  feed: {
    display: 'flex',
    flexDirection: 'column',
    maxHeight: '520px',
    overflowY: 'auto',
  },
  item: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    columnGap: '12px',
    padding: '14px 16px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  itemLast: {
    borderBottom: 'none',
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: 0,
  },
  topRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '10px',
    justifyContent: 'space-between',
  },
  agent: {
    fontSize: '12px',
    color: tokens.colorNeutralForeground2,
    fontWeight: 500,
    letterSpacing: '0.02em',
  },
  timestamp: {
    fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
    fontVariantNumeric: 'tabular-nums',
  },
  content: {
    fontSize: '14px',
    color: tokens.colorNeutralForeground1,
    lineHeight: 1.5,
    margin: 0,
  },
  evidence: {
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
    paddingLeft: '10px',
    borderLeft: `2px solid ${tokens.colorNeutralStroke2}`,
    marginTop: '6px',
  },
  empty: {
    padding: '32px 16px',
    textAlign: 'center',
    color: tokens.colorNeutralForeground3,
    fontSize: '13px',
  },
});

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function InterventionFeed({ meeting }: { meeting: Meeting }) {
  const styles = useStyles();
  const items: InterventionDelivery[] = [...meeting.delivered_interventions].reverse();

  return (
    <Section
      title="介入フィード"
      trailing={
        <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
          {items.length === 0 ? '0' : `${items.length} 件`}
        </Caption1>
      }
      bare
    >
      <div className={styles.feed}>
        {items.length === 0 ? (
          <p className={styles.empty}>
            まだ介入はありません。会議が進むと AI 提案がここに流れます。
          </p>
        ) : (
          items.map((d, i) => (
            <div
              key={d.id}
              className={`${styles.item}${i === items.length - 1 ? ` ${styles.itemLast}` : ''}`}
            >
              <LevelBar level={d.level} />
              <div className={styles.body}>
                <div className={styles.topRow}>
                  <span className={styles.agent}>
                    {d.agent} · {d.level}
                  </span>
                  <span className={styles.timestamp}>{fmtTime(d.delivered_at)}</span>
                </div>
                <p className={styles.content}>{d.content}</p>
                {d.evidence_quote && (
                  <p className={styles.evidence}>「{d.evidence_quote}」</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </Section>
  );
}
