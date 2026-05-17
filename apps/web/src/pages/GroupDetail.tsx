import {
  Body1,
  Button,
  Spinner,
  makeStyles,
} from '@fluentui/react-components';
import {
  ArrowLeft20Regular,
  Delete20Regular,
  FolderRegular,
} from '@fluentui/react-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { DocumentUpload } from '@/components/DocumentUpload';
import { Pill } from '@/components/primitives/Pill';
import { api, type Meeting } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    padding: '24px 28px 64px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  back: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    textDecoration: 'none',
    cursor: 'pointer',
    ':hover': { color: 'var(--text-1)' },
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    gap: '16px',
    flexWrap: 'wrap',
  },
  title: {
    margin: 0,
    fontSize: '26px',
    fontWeight: 600,
    letterSpacing: '-0.015em',
    color: 'var(--text-1)',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  description: {
    color: 'var(--text-2)',
    fontSize: '13px',
    margin: '6px 0 0',
    maxWidth: '720px',
    lineHeight: 1.6,
  },
  meta: {
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    display: 'flex',
    gap: '10px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1.4fr 1fr',
    gap: '20px',
    '@media (max-width: 1100px)': {
      gridTemplateColumns: '1fr',
    },
  },
  panel: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    overflow: 'hidden',
  },
  panelHeader: {
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  panelTitle: {
    margin: 0,
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
  },
  panelBody: {
    padding: '16px 18px',
  },
  meetingRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid var(--border-hairline)',
    backgroundColor: 'var(--bg-2)',
    marginBottom: '6px',
  },
  meetingLink: {
    flex: 1,
    minWidth: 0,
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-1)',
    textDecoration: 'none',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  meetingMeta: {
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    marginLeft: '12px',
  },
  empty: {
    color: 'var(--text-3)',
    fontSize: '12px',
    fontStyle: 'italic',
  },
  errorText: {
    color: '#fca5a5',
    fontSize: '12px',
  },
});

export function GroupDetail() {
  const styles = useStyles();
  const { groupId } = useParams<{ groupId: string }>();
  const navigate = useNavigate();
  const { userId } = useIdentity();
  const qc = useQueryClient();

  const { data: group, isLoading } = useQuery({
    queryKey: ['group', groupId, userId],
    queryFn: () => api.getGroup(groupId!, userId),
    enabled: !!groupId,
  });

  const { data: meetings } = useQuery({
    queryKey: ['group-meetings', groupId, userId],
    queryFn: () => api.listGroupMeetings(groupId!, userId),
    enabled: !!groupId,
  });

  const detachMutation = useMutation({
    mutationFn: (meetingId: string) =>
      api.detachMeetingFromGroup(groupId!, meetingId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['group', groupId, userId] });
      qc.invalidateQueries({ queryKey: ['group-meetings', groupId, userId] });
    },
  });

  const deleteGroupMutation = useMutation({
    mutationFn: () => api.deleteGroup(groupId!, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['groups', userId] });
      navigate('/groups');
    },
  });

  if (isLoading) {
    return (
      <div className={styles.root}>
        <Spinner size="small" />
      </div>
    );
  }

  if (!group) {
    return (
      <div className={styles.root}>
        <Body1>グループが見つかりませんでした。</Body1>
        <Link to="/groups">← Groups に戻る</Link>
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <Link to="/groups" className={styles.back}>
        <ArrowLeft20Regular /> Groups
      </Link>

      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>
            <FolderRegular /> {group.name}
          </h1>
          {group.description && (
            <p className={styles.description}>{group.description}</p>
          )}
          <div className={styles.meta} style={{ marginTop: 10 }}>
            <Pill kind="brand">GROUP</Pill>
            <span>{group.meeting_ids.length} meetings</span>
            <span>{group.document_ids.length} shared docs</span>
            <span>updated {new Date(group.updated_at).toLocaleString()}</span>
          </div>
        </div>
        <Button
          appearance="subtle"
          icon={<Delete20Regular />}
          onClick={() => {
            if (
              confirm(
                `グループ「${group.name}」を削除しますか? 書類は全て削除されます。`,
              )
            ) {
              deleteGroupMutation.mutate();
            }
          }}
          disabled={deleteGroupMutation.isPending}
        >
          グループ削除
        </Button>
      </header>

      <div className={styles.grid}>
        <section className={styles.panel}>
          <header className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>共有書類 · AI が全会議で参照</h2>
            <span className={styles.meta}>
              {group.document_ids.length} doc
              {group.document_ids.length === 1 ? '' : 's'}
            </span>
          </header>
          <div className={styles.panelBody}>
            <DocumentUpload
              scope={{ kind: 'group', groupId: group.id, organizerId: userId }}
              uploadedBy={userId}
            />
          </div>
        </section>

        <section className={styles.panel}>
          <header className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>メンバー会議</h2>
            <span className={styles.meta}>
              {group.meeting_ids.length} meeting
              {group.meeting_ids.length === 1 ? '' : 's'}
            </span>
          </header>
          <div className={styles.panelBody}>
            {meetings && meetings.length === 0 && (
              <Body1 className={styles.empty}>
                まだメンバー会議はありません。会議の Mission Control から
                このグループを選んで追加できます。
              </Body1>
            )}
            {meetings?.map((m: Meeting) => (
              <div key={m.id} className={styles.meetingRow}>
                <Link
                  to={`/m/${m.id}?organizer_id=${encodeURIComponent(userId)}`}
                  className={styles.meetingLink}
                >
                  {m.goal || '(ゴール未設定)'}
                </Link>
                <span className={styles.meetingMeta}>{m.mode}</span>
                <Button
                  appearance="subtle"
                  size="small"
                  icon={<Delete20Regular />}
                  onClick={() => detachMutation.mutate(m.id)}
                  disabled={detachMutation.isPending}
                  aria-label="グループから外す"
                  title="このグループから外す"
                />
              </div>
            ))}
          </div>
        </section>
      </div>

      {deleteGroupMutation.isError && (
        <Body1 className={styles.errorText}>
          削除失敗: {String(deleteGroupMutation.error)}
        </Body1>
      )}
    </div>
  );
}
