import { Badge, Body1, Caption1, Title2, makeStyles, tokens } from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';

import { api, type BotStatus, type Meeting, type Topic, type TopicState } from '@/lib/api';

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
  docRef: {
    marginTop: '4px',
    color: tokens.colorBrandForeground1,
    fontSize: '11px',
    fontStyle: 'italic',
  },
  docItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 10px',
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground3,
    fontSize: '12px',
    gap: '8px',
  },
  docFilename: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
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

const BOT_STATUS_LABEL: Record<BotStatus, string> = {
  idle: '🤖 未参加',
  connecting: '🤖 接続中…',
  in_call: '🤖 会議に参加中',
  disconnected: '🤖 退出済',
  failed: '🤖 失敗',
};

const BOT_STATUS_COLOR: Record<BotStatus, 'subtle' | 'informative' | 'success' | 'warning' | 'danger'> = {
  idle: 'subtle',
  connecting: 'warning',
  in_call: 'success',
  disconnected: 'subtle',
  failed: 'danger',
};

export function Sidebar({ meeting, organizerId }: { meeting: Meeting; organizerId: string }) {
  const styles = useStyles();
  const inheritedIds = new Set(meeting.inherited_topic_ids);
  const inheritedTopics = meeting.topics.filter((t) => inheritedIds.has(t.id));

  // DOC-8: 参考文書一覧 (meeting に紐付く Document を表示)
  const { data: documents } = useQuery({
    queryKey: ['documents', meeting.id, organizerId],
    queryFn: () => api.listDocuments(meeting.id, organizerId),
    enabled: meeting.document_ids.length > 0,
    staleTime: 30_000,
  });

  return (
    <aside className={styles.root}>
      <div className={styles.goalBlock}>
        <Title2 as="h2" style={{ fontSize: 16, margin: 0 }}>
          🎯 ゴール
        </Title2>
        <Body1>{meeting.goal}</Body1>
        <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
          {meeting.series_index !== null && (
            <Badge appearance="tint" color="brand" size="small">
              シリーズ #{meeting.series_index}
            </Badge>
          )}
          <Badge appearance="filled" color={BOT_STATUS_COLOR[meeting.bot_status]} size="small">
            {BOT_STATUS_LABEL[meeting.bot_status]}
          </Badge>
        </div>
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

      {documents && documents.length > 0 && (
        <div className={styles.goalBlock}>
          <Title2 as="h2" style={{ fontSize: 16, margin: 0 }}>
            📎 参考文書 ({documents.length})
          </Title2>
          <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
            CoverageTracker が引用する元データ
          </Caption1>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
            {documents.map((d) => (
              <div key={d.id} className={styles.docItem}>
                <span className={styles.docFilename}>{d.filename}</span>
                <Badge
                  appearance="filled"
                  size="small"
                  color={d.status === 'indexed' ? 'success' : d.status === 'failed' ? 'danger' : 'warning'}
                >
                  {d.status}
                </Badge>
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
            {t.document_reference && (
              <div className={styles.docRef}>📎 {t.document_reference}</div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
