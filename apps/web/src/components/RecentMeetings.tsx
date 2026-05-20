import { Button, Spinner, makeStyles } from '@fluentui/react-components';
import { ArrowRight16Regular } from '@fluentui/react-icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { Skeleton } from '@/components/primitives/Skeleton';
import { StatusDot, type StatusKind } from '@/components/primitives/StatusDot';
import { api, type Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    overflow: 'hidden',
  },
  header: {
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
  },
  count: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  headRow: {
    backgroundColor: 'var(--bg-2)',
    borderBottom: '1px solid var(--border-hairline)',
  },
  th: {
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
    textAlign: 'left',
    padding: '10px 18px',
    fontFamily: 'var(--font-mono)',
  },
  thRight: {
    textAlign: 'right',
  },
  row: {
    borderBottom: '1px solid var(--border-hairline)',
    transitionProperty: 'background-color',
    transitionDuration: '120ms',
    ':hover': {
      backgroundColor: 'var(--bg-2)',
    },
  },
  rowLast: {
    borderBottom: 'none',
  },
  td: {
    padding: '14px 18px',
    fontSize: '13px',
    color: 'var(--text-1)',
    verticalAlign: 'middle',
  },
  tdStatus: {
    width: '90px',
  },
  tdMode: {
    width: '120px',
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  tdDate: {
    width: '140px',
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    fontVariantNumeric: 'tabular-nums',
  },
  tdActions: {
    width: '180px',
    textAlign: 'right',
  },
  goal: {
    color: 'var(--text-1)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: '420px',
  },
  goalMeta: {
    color: 'var(--text-3)',
    fontSize: '11px',
    marginTop: '2px',
    display: 'flex',
    gap: '8px',
  },
  statusInner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  empty: {
    padding: '32px 18px',
    textAlign: 'center',
    color: 'var(--text-3)',
    fontSize: '13px',
  },
  actionGroup: {
    display: 'inline-flex',
    gap: '6px',
  },
});

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('ja-JP', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * meeting.state と meeting.bot_status を組み合わせた表示ステータス。
 * Teams 会議が終わっても meeting.state は 'in_progress' のまま残る (Helmsman が自動 conclude しない) ため、
 * bot_status を優先して disconnected/failed を red 表示にする。
 */
function deriveStatus(m: Meeting): { kind: StatusKind; label: string } {
  // 失敗系は最優先で red
  if (m.bot_status === 'failed') return { kind: 'danger', label: 'FAILED' };
  // 会議そのものが終了
  if (m.state === 'concluded') return { kind: 'neutral', label: 'DONE' };
  // scheduled (未開始)
  if (m.state === 'scheduled') return { kind: 'warning', label: 'SCHED' };

  // ここから state === 'in_progress'
  if (m.bot_status === 'in_call') return { kind: 'active', label: 'LIVE' };
  if (m.bot_status === 'connecting') return { kind: 'warning', label: 'JOINING' };
  // bot が退出済 → 終わってる扱い (灰色、エラーではないので danger は避ける)
  if (m.bot_status === 'disconnected') return { kind: 'neutral', label: 'ENDED' };
  if (m.bot_status === 'idle') return { kind: 'neutral', label: 'IDLE' };

  return { kind: 'neutral', label: m.state.toUpperCase() };
}

interface RecentMeetingsProps {
  organizerId: string;
  variant?: 'open' | 'continue';
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

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <h2 className={styles.title}>Recent sessions</h2>
        <span className={styles.count}>
          {isLoading ? (
            <Spinner size="extra-tiny" />
          ) : (
            `${meetings?.length ?? 0} · last ${limit}`
          )}
        </span>
      </div>

      {isLoading ? (
        <div style={{ padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} height={28} />
          ))}
        </div>
      ) : !meetings || meetings.length === 0 ? (
        <p className={styles.empty}>まだセッションがありません。「Bot を派遣」から始めてください。</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr className={styles.headRow}>
              <th className={styles.th} style={{ width: 90 }}>Status</th>
              <th className={styles.th}>Goal / session</th>
              <th className={styles.th} style={{ width: 120 }}>Mode</th>
              <th className={styles.th} style={{ width: 140 }}>Started</th>
              <th className={styles.th} style={{ width: 180, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {meetings.map((m, i) => {
              const status = deriveStatus(m);
              return (
                <tr
                  key={m.id}
                  className={`${styles.row}${i === meetings.length - 1 ? ` ${styles.rowLast}` : ''}`}
                >
                  <td className={`${styles.td} ${styles.tdStatus}`}>
                    <span className={styles.statusInner}>
                      <StatusDot kind={status.kind} pulse={status.kind === 'active'} />
                      {status.label}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <div className={styles.goal} title={m.goal}>
                      {m.goal || <span style={{ color: 'var(--text-3)' }}>(no goal)</span>}
                    </div>
                    {(m.series_index !== null || m.parent_meeting_id !== null) && (
                      <div className={styles.goalMeta}>
                        {m.series_index !== null && <span>series #{m.series_index}</span>}
                        {m.parent_meeting_id !== null && <span>continued</span>}
                      </div>
                    )}
                  </td>
                  <td className={`${styles.td} ${styles.tdMode}`}>{m.mode}</td>
                  <td className={`${styles.td} ${styles.tdDate}`}>{formatDate(m.started_at)}</td>
                  <td className={`${styles.td} ${styles.tdActions}`}>
                    <span className={styles.actionGroup}>
                      {variant === 'continue' && onContinue ? (
                        <Button size="small" appearance="primary" onClick={() => onContinue(m)}>
                          引き継ぐ
                        </Button>
                      ) : (
                        <>
                          <Button
                            size="small"
                            appearance="primary"
                            icon={<ArrowRight16Regular />}
                            iconPosition="after"
                            onClick={() =>
                              navigate(
                                `/m/${m.id}?organizer_id=${encodeURIComponent(organizerId)}`,
                              )
                            }
                          >
                            Open
                          </Button>
                          <Button
                            size="small"
                            appearance="subtle"
                            onClick={() => navigate(`/new?parent=${encodeURIComponent(m.id)}`)}
                          >
                            Continue
                          </Button>
                        </>
                      )}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
