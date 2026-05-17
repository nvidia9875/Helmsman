import { makeStyles, mergeClasses } from '@fluentui/react-components';

import { StatusDot, type StatusKind } from '@/components/primitives/StatusDot';
import type { Meeting, TopicState } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    borderLeft: '1px solid var(--border-hairline)',
    padding: '20px 18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    backgroundColor: 'var(--bg-0)',
    height: 'calc(100vh - 52px)',
    position: 'sticky',
    top: '52px',
    overflowY: 'auto',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  sectionTitle: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
    margin: 0,
    fontFamily: 'var(--font-mono)',
  },
  sectionCount: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-4)',
    fontVariantNumeric: 'tabular-nums',
  },
  topicList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  topicRow: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    columnGap: '10px',
    alignItems: 'flex-start',
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid transparent',
    transitionProperty: 'background-color, border-color',
    transitionDuration: '120ms',
    ':hover': {
      backgroundColor: 'var(--bg-1)',
      border: '1px solid var(--border-hairline)',
    },
  },
  topicDecided: {
    opacity: 0.65,
  },
  topicDot: {
    marginTop: '5px',
  },
  topicBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    minWidth: 0,
  },
  topicName: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-1)',
    lineHeight: 1.4,
  },
  topicMeta: {
    fontSize: '10px',
    color: 'var(--text-3)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-mono)',
  },
  docRef: {
    fontSize: '11px',
    color: 'var(--accent)',
    marginTop: '4px',
    fontStyle: 'italic',
  },
  empty: {
    color: 'var(--text-3)',
    fontSize: '12px',
    padding: '8px 0',
    fontStyle: 'italic',
  },
  sep: {
    height: '1px',
    backgroundColor: 'var(--border-hairline)',
    margin: '6px 0',
  },
  legend: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
    fontSize: '10px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
});

const STATE_LABEL: Record<TopicState, string> = {
  not_started: 'not started',
  discussing: 'discussing',
  deep_dive: 'deep dive',
  decided: 'decided',
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
  const decidedCount = topics.filter((t) => t.state === 'decided').length;

  return (
    <aside className={styles.root}>
      <div>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Topics</h3>
          <span className={styles.sectionCount}>
            {decidedCount}/{topics.length}
          </span>
        </div>
        <div className={styles.sep} />
        {topics.length === 0 ? (
          <p className={styles.empty}>(no topics — set a goal to decompose)</p>
        ) : (
          <div className={styles.topicList}>
            {topics.map((t) => (
              <div
                key={t.id}
                className={mergeClasses(
                  styles.topicRow,
                  t.state === 'decided' && styles.topicDecided,
                )}
              >
                <span className={styles.topicDot}>
                  <StatusDot kind={stateDot(t.state)} />
                </span>
                <div className={styles.topicBody}>
                  <span className={styles.topicName}>{t.name}</span>
                  <span className={styles.topicMeta}>
                    {STATE_LABEL[t.state]} · {t.priority}
                  </span>
                  {t.document_reference && (
                    <span className={styles.docRef}>{t.document_reference}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className={styles.sectionTitle}>Legend</h3>
        <div className={styles.sep} />
        <div className={styles.legend}>
          <span className={styles.legendItem}>
            <StatusDot kind="neutral" /> not started
          </span>
          <span className={styles.legendItem}>
            <StatusDot kind="warning" /> discussing
          </span>
          <span className={styles.legendItem}>
            <StatusDot kind="brand" /> deep dive
          </span>
          <span className={styles.legendItem}>
            <StatusDot kind="active" /> decided
          </span>
        </div>
      </div>
    </aside>
  );
}
