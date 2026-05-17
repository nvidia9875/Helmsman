import {
  Button,
  Dropdown,
  Option,
  Spinner,
  makeStyles,
} from '@fluentui/react-components';
import {
  FolderArrowRight20Regular,
  FolderLink20Regular,
} from '@fluentui/react-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { Pill } from '@/components/primitives/Pill';
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
    gap: '10px',
  },
  title: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  body: {
    padding: '14px 18px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  intro: {
    color: 'var(--text-3)',
    fontSize: '12px',
    margin: 0,
    lineHeight: 1.55,
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    gap: '10px',
    alignItems: 'center',
  },
  attached: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid var(--border-hairline)',
    backgroundColor: 'var(--bg-2)',
  },
  attachedName: {
    fontSize: '13px',
    color: 'var(--text-1)',
    fontWeight: 500,
    textDecoration: 'none',
  },
  emptyHint: {
    color: 'var(--text-3)',
    fontSize: '12px',
    fontStyle: 'italic',
  },
});

interface Props {
  meeting: Meeting;
  organizerId: string;
}

export function GroupAttachment({ meeting, organizerId }: Props) {
  const styles = useStyles();
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);

  const { data: groups } = useQuery({
    queryKey: ['groups', organizerId],
    queryFn: () => api.listGroups(organizerId),
  });

  const currentGroup = groups?.find((g) => g.id === meeting.group_id) ?? null;

  const attachMutation = useMutation({
    mutationFn: (groupId: string) =>
      api.attachMeetingToGroup(groupId, meeting.id, organizerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meeting', meeting.id, organizerId] });
      qc.invalidateQueries({ queryKey: ['groups', organizerId] });
    },
  });

  const detachMutation = useMutation({
    mutationFn: () =>
      api.detachMeetingFromGroup(meeting.group_id!, meeting.id, organizerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meeting', meeting.id, organizerId] });
      qc.invalidateQueries({ queryKey: ['groups', organizerId] });
    },
  });

  return (
    <section className={styles.root} aria-label="グループ所属">
      <header className={styles.header}>
        <h2 className={styles.title}>
          <FolderLink20Regular /> グループ所属
        </h2>
        <Pill kind={meeting.group_id ? 'success' : 'neutral'}>
          {meeting.group_id ? 'IN GROUP' : 'STANDALONE'}
        </Pill>
      </header>

      <div className={styles.body}>
        <p className={styles.intro}>
          会議をグループに所属させると、グループ配下の書類が AI の参照に追加され、
          複数会議で書類を使い回せます。
        </p>

        {currentGroup ? (
          <div className={styles.attached}>
            <Link
              to={`/groups/${currentGroup.id}`}
              className={styles.attachedName}
            >
              📁 {currentGroup.name}
            </Link>
            <Button
              size="small"
              appearance="secondary"
              onClick={() => detachMutation.mutate()}
              disabled={detachMutation.isPending}
            >
              {detachMutation.isPending ? <Spinner size="tiny" /> : '外す'}
            </Button>
          </div>
        ) : (
          <div className={styles.row}>
            {groups && groups.length > 0 ? (
              <>
                <Dropdown
                  placeholder="グループを選択"
                  value={
                    selected ? groups.find((g) => g.id === selected)?.name ?? '' : ''
                  }
                  selectedOptions={selected ? [selected] : []}
                  onOptionSelect={(_, d) => setSelected(d.optionValue ?? null)}
                >
                  {groups.map((g) => (
                    <Option key={g.id} value={g.id}>
                      {g.name}
                    </Option>
                  ))}
                </Dropdown>
                <Button
                  appearance="primary"
                  size="small"
                  icon={<FolderArrowRight20Regular />}
                  onClick={() => selected && attachMutation.mutate(selected)}
                  disabled={!selected || attachMutation.isPending}
                >
                  追加
                </Button>
              </>
            ) : (
              <span className={styles.emptyHint}>
                グループがまだありません。
                <Link to="/groups" style={{ marginLeft: 6, color: 'var(--accent)' }}>
                  Groups で作成 →
                </Link>
              </span>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
