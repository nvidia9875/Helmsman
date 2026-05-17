import { Caption1, makeStyles, tokens } from '@fluentui/react-components';

import { Section } from '@/components/primitives/Section';
import { StatusDot, type StatusKind } from '@/components/primitives/StatusDot';
import type { Meeting, TopicState } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    borderLeft: `1px solid ${tokens.colorNeutralStroke2}`,
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    backgroundColor: tokens.colorNeutralBackground1,
    height: '100vh',
    position: 'sticky',
    top: 0,
    overflowY: 'auto',
  },
  topicList: {
    display: 'flex',
    flexDirection: 'column',
  },
  topicRow: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    columnGap: '10px',
    alignItems: 'baseline',
    padding: '10px 12px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  topicRowLast: {
    borderBottom: 'none',
  },
  topicHeader: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    minWidth: 0,
  },
  topicName: {
    fontSize: '13px',
    fontWeight: 500,
    color: tokens.colorNeutralForeground1,
  },
  topicMeta: {
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
  },
  empty: {
    color: tokens.colorNeutralForeground3,
    fontSize: '13px',
    padding: '8px 0',
  },
});

const STATE_LABEL: Record<TopicState, string> = {
  not_started: '未着手',
  discussing: '議論中',
  deep_dive: '深掘り済',
  decided: '決定済',
};

function stateDot(state: TopicState): StatusKind {
  switch (state) {
    case 'decided':
      return 'active';
    case 'deep_dive':
      return 'brand';
    case 'discussing':
      return 'warning';
    default:
      return 'neutral';
  }
}

interface Props {
  meeting: Meeting;
  organizerId: string;
}

export function Sidebar({ meeting }: Props) {
  const styles = useStyles();
  const topics = meeting.topics;

  return (
    <aside className={styles.root}>
      <Section
        title="論点"
        trailing={
          <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
            {topics.length}
          </Caption1>
        }
        bare
      >
        <div className={styles.topicList}>
          {topics.length === 0 ? (
            <p className={styles.empty}>ゴール未設定です</p>
          ) : (
            topics.map((t, i) => (
              <div
                key={t.id}
                className={`${styles.topicRow}${
                  i === topics.length - 1 ? ` ${styles.topicRowLast}` : ''
                }`}
              >
                <StatusDot kind={stateDot(t.state)} />
                <div className={styles.topicHeader}>
                  <span className={styles.topicName}>{t.name}</span>
                  <span className={styles.topicMeta}>
                    {STATE_LABEL[t.state]} · {t.priority}
                    {t.document_reference ? ` · 📎 ${t.document_reference}` : ''}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </Section>
    </aside>
  );
}
