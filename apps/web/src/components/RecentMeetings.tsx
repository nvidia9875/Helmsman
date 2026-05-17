import {
  Badge,
  Body1,
  Button,
  Card,
  CardHeader,
  Spinner,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { api, type Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    width: '100%',
    maxWidth: '720px',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  card: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
  },
  goalCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: 0,
  },
  goal: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  meta: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  actions: {
    display: 'flex',
    gap: '8px',
  },
  empty: {
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
    textAlign: 'center',
    padding: '16px',
  },
});

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('ja-JP', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface RecentMeetingsProps {
  organizerId: string;
  /** Display behavior. "open" = navigate to meeting room; "continue" = create successor. */
  variant?: 'open' | 'continue';
  /** Continue-mode callback: parent caller wires it to /new?parent={id}. */
  onContinue?: (meeting: Meeting) => void;
  limit?: number;
}

export function RecentMeetings({
  organizerId,
  variant = 'open',
  onContinue,
  limit = 10,
}: RecentMeetingsProps) {
  const styles = useStyles();
  const navigate = useNavigate();

  const { data: meetings, isLoading } = useQuery({
    queryKey: ['meetings', 'recent', organizerId, limit],
    queryFn: () => api.listMeetings(organizerId, limit),
    staleTime: 30_000,
  });

  if (isLoading) {
    return <Spinner size="small" label="最近の会議を読み込み中..." />;
  }

  if (!meetings || meetings.length === 0) {
    return (
      <Body1 className={styles.empty}>
        まだ会議がありません。最初の会議を作成しましょう。
      </Body1>
    );
  }

  return (
    <div className={styles.root}>
      <Title3 as="h2" style={{ margin: 0 }}>
        🕘 最近の会議
      </Title3>
      <div className={styles.list}>
        {meetings.map((m) => (
          <Card key={m.id} className={styles.card}>
            <div className={styles.goalCol}>
              <CardHeader
                header={<Body1 className={styles.goal}>{m.goal}</Body1>}
              />
              <div className={styles.meta}>
                <span>{m.mode}</span>
                <span>・</span>
                <span>{formatDate(m.started_at)}</span>
                {m.series_index !== null && (
                  <Badge appearance="outline" size="small">
                    シリーズ #{m.series_index}
                  </Badge>
                )}
                {m.parent_meeting_id !== null && (
                  <Badge appearance="tint" size="small" color="brand">
                    継続会議
                  </Badge>
                )}
              </div>
            </div>
            <div className={styles.actions}>
              {variant === 'continue' && onContinue ? (
                <Button appearance="primary" onClick={() => onContinue(m)}>
                  この会議を引き継ぐ
                </Button>
              ) : (
                <>
                  <Button
                    appearance="primary"
                    onClick={() =>
                      navigate(
                        `/m/${m.id}?organizer_id=${encodeURIComponent(organizerId)}`,
                      )
                    }
                  >
                    開く
                  </Button>
                  <Button
                    appearance="secondary"
                    onClick={() => navigate(`/new?parent=${encodeURIComponent(m.id)}`)}
                  >
                    続きから
                  </Button>
                </>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
