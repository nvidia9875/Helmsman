import {
  Body1,
  Button,
  Field,
  Input,
  Spinner,
  Textarea,
  Title2,
  makeStyles,
} from '@fluentui/react-components';
import {
  Delete20Regular,
  FolderAddRegular,
  FolderRegular,
} from '@fluentui/react-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { api, type MeetingGroup } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    padding: '32px 28px 64px',
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    marginBottom: '24px',
  },
  eyebrow: {
    color: 'var(--accent)',
    fontSize: '10px',
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  title: {
    margin: 0,
    fontSize: '28px',
    lineHeight: 1.15,
    letterSpacing: '-0.015em',
    fontWeight: 600,
    color: 'var(--text-1)',
  },
  intro: {
    color: 'var(--text-2)',
    lineHeight: 1.55,
    fontSize: '14px',
    margin: '4px 0 0',
    maxWidth: '640px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1.2fr 1fr',
    gap: '24px',
    alignItems: 'flex-start',
    '@media (max-width: 960px)': {
      gridTemplateColumns: '1fr',
    },
  },
  panel: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  panelTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
    paddingBottom: '12px',
    borderBottom: '1px solid var(--border-hairline)',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  card: {
    display: 'flex',
    gap: '12px',
    padding: '14px 16px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-0)',
    transitionProperty: 'border-color, background-color',
    transitionDuration: '120ms',
    ':hover': {
      border: '1px solid var(--accent)',
      backgroundColor: 'var(--bg-2)',
    },
  },
  cardBody: {
    flex: 1,
    minWidth: 0,
  },
  cardName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
    textDecoration: 'none',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  cardDesc: {
    fontSize: '12px',
    color: 'var(--text-3)',
    margin: '4px 0 0',
    lineHeight: 1.55,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  cardMeta: {
    marginTop: '6px',
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    display: 'flex',
    gap: '10px',
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

export function Groups() {
  const styles = useStyles();
  const { userId } = useIdentity();
  const qc = useQueryClient();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const { data: groups, isLoading } = useQuery({
    queryKey: ['groups', userId],
    queryFn: () => api.listGroups(userId),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createGroup({
        organizer_id: userId,
        name: name.trim(),
        description: description.trim(),
      }),
    onSuccess: () => {
      setName('');
      setDescription('');
      qc.invalidateQueries({ queryKey: ['groups', userId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (groupId: string) => api.deleteGroup(groupId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['groups', userId] }),
  });

  const handleDelete = (g: MeetingGroup) => {
    if (
      !confirm(
        `グループ「${g.name}」を削除しますか? 配下の書類も全て削除され、` +
          `所属していた会議は単独に戻ります。`,
      )
    )
      return;
    deleteMutation.mutate(g.id);
  };

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <span className={styles.eyebrow}>GROUPS · shared knowledge</span>
        <Title2 as="h1" className={styles.title}>
          会議グループ
        </Title2>
        <p className={styles.intro}>
          複数会議で書類と文脈を共有するための束。グループに所属する会議は、
          配下の全書類を AI が参照します。
        </p>
      </header>

      <div className={styles.grid}>
        <section className={styles.panel}>
          <h2 className={styles.panelTitle}>すべてのグループ</h2>

          {isLoading && <Spinner size="tiny" />}

          {groups && groups.length === 0 && (
            <Body1 className={styles.empty}>
              まだグループはありません。右の「新規グループ作成」で追加してください。
            </Body1>
          )}

          <div className={styles.list}>
            {groups?.map((g) => (
              <div key={g.id} className={styles.card}>
                <div className={styles.cardBody}>
                  <Link to={`/groups/${g.id}`} className={styles.cardName}>
                    <FolderRegular /> {g.name}
                  </Link>
                  {g.description && (
                    <p className={styles.cardDesc}>{g.description}</p>
                  )}
                  <div className={styles.cardMeta}>
                    <span>{g.meeting_ids.length} meetings</span>
                    <span>{g.document_ids.length} docs</span>
                    <span>updated {new Date(g.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <Button
                  appearance="subtle"
                  size="small"
                  icon={<Delete20Regular />}
                  onClick={() => handleDelete(g)}
                  disabled={deleteMutation.isPending}
                  aria-label={`${g.name} を削除`}
                />
              </div>
            ))}
          </div>
        </section>

        <aside className={styles.panel}>
          <h2 className={styles.panelTitle}>新規グループ作成</h2>

          <Field label="グループ名" required>
            <Input
              value={name}
              onChange={(_, d) => setName(d.value)}
              placeholder="例: Q3 プロダクトローンチ"
              maxLength={120}
            />
          </Field>
          <Field label="説明 (任意)">
            <Textarea
              value={description}
              onChange={(_, d) => setDescription(d.value)}
              placeholder="このグループで扱う議題やコンテキストのメモ"
              rows={4}
            />
          </Field>

          <div>
            <Button
              appearance="primary"
              icon={<FolderAddRegular />}
              onClick={() => createMutation.mutate()}
              disabled={!name.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? (
                <>
                  <Spinner size="tiny" /> 作成中…
                </>
              ) : (
                '作成'
              )}
            </Button>
          </div>

          {createMutation.isError && (
            <Body1 className={styles.errorText}>
              作成失敗: {String(createMutation.error)}
            </Body1>
          )}
        </aside>
      </div>
    </div>
  );
}
