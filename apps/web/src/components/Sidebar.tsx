import { Badge, Body1, Title2, makeStyles, tokens } from '@fluentui/react-components';

import type { Meeting, Topic, TopicState } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    borderLeft: `1px solid ${tokens.colorNeutralStroke1}`,
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    backgroundColor: tokens.colorNeutralBackground2,
    height: '100vh',
    position: 'sticky',
    top: 0,
    overflowY: 'auto',
  },
  goalBlock: {
    paddingBottom: '12px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  topicList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  topic: {
    padding: '12px',
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground3,
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  topicHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
  },
  topicBody: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
  },
});

const STATE_LABEL: Record<TopicState, string> = {
  not_started: '未着手',
  discussing: '議論中',
  deep_dive: '深掘り済',
  decided: '決定済',
};

function stateBadgeColor(state: TopicState): 'subtle' | 'informative' | 'success' | 'warning' {
  switch (state) {
    case 'decided':
      return 'success';
    case 'deep_dive':
      return 'informative';
    case 'discussing':
      return 'warning';
    default:
      return 'subtle';
  }
}

export function Sidebar({ meeting }: { meeting: Meeting }) {
  const styles = useStyles();
  const inheritedIds = new Set(meeting.inherited_topic_ids);
  const inheritedTopics = meeting.topics.filter((t) => inheritedIds.has(t.id));

  return (
    <aside className={styles.root}>
      <div className={styles.goalBlock}>
        <Title2 as="h2" style={{ fontSize: 16, margin: 0 }}>
          🎯 ゴール
        </Title2>
        <Body1>{meeting.goal}</Body1>
        {meeting.series_index !== null && (
          <Badge appearance="tint" color="brand" size="small" style={{ marginTop: 8 }}>
            シリーズ #{meeting.series_index}
          </Badge>
        )}
      </div>

      {inheritedTopics.length > 0 && (
        <div className={styles.goalBlock}>
          <Title2 as="h2" style={{ fontSize: 16, margin: 0 }}>
            🔁 前回からの引き継ぎ事項 ({inheritedTopics.length})
          </Title2>
          <div className={styles.topicList} style={{ marginTop: 8 }}>
            {inheritedTopics.map((t: Topic) => (
              <div key={`inherited-${t.id}`} className={styles.topic}>
                <div className={styles.topicHeader}>
                  <strong>{t.name}</strong>
                  <Badge appearance="outline" color="brand" size="small">
                    継続
                  </Badge>
                </div>
                <div className={styles.topicBody}>
                  <div>{t.decision_criteria}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Title2 as="h2" style={{ fontSize: 16, marginTop: 4 }}>
        📋 論点 ({meeting.topics.length})
      </Title2>

      <div className={styles.topicList}>
        {meeting.topics.map((t: Topic) => (
          <div key={t.id} className={styles.topic}>
            <div className={styles.topicHeader}>
              <strong>{t.name}</strong>
              <Badge appearance="filled" color={stateBadgeColor(t.state)}>
                {STATE_LABEL[t.state]}
              </Badge>
            </div>
            <div className={styles.topicBody}>
              <div>優先度: {t.priority} ／ 時間配分: {t.time_budget_pct}%</div>
              <div>{t.decision_criteria}</div>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
