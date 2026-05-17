import {
  Body1,
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  Spinner,
  Textarea,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { api, type Meeting } from '@/lib/api';

const useStyles = makeStyles({
  trigger: {
    fontSize: '13px',
    color: tokens.colorBrandForeground1,
  },
});

interface Props {
  meeting: Meeting;
  organizerId: string;
}

export function GoalEditor({ meeting, organizerId }: Props) {
  const styles = useStyles();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState(meeting.goal ?? '');

  const mutation = useMutation({
    mutationFn: () => api.setGoal(meeting.id, organizerId, goal.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meeting.id, organizerId] });
      setOpen(false);
    },
  });

  const hasGoal = !!meeting.goal?.trim();
  const triggerLabel = hasGoal ? '✏️ ゴールを編集' : '🎯 ゴールを後から追加';
  const dialogTitle = hasGoal
    ? 'ゴールを更新して論点を再分解'
    : 'ゴールを追加して論点を分解';

  return (
    <Dialog open={open} onOpenChange={(_, d) => setOpen(d.open)}>
      <DialogTrigger disableButtonEnhancement>
        <Button appearance="subtle" size="small" className={styles.trigger}>
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>{dialogTitle}</DialogTitle>
          <DialogContent>
            <Body1 style={{ marginBottom: 12, color: tokens.colorNeutralForeground3 }}>
              {hasGoal
                ? '既存の論点は破棄され、新しいゴールから再分解されます。'
                : '会議で議論したい論点を Goal Decomposer が自動で 3-7 個に分解します。'}
            </Body1>
            <Textarea
              value={goal}
              onChange={(_, d) => setGoal(d.value)}
              placeholder="例: 6 月 30 日のローンチ可否を決定する"
              rows={4}
            />
            {mutation.isError && (
              <Body1 style={{ color: tokens.colorPaletteRedForeground1, marginTop: 8 }}>
                エラー: {String(mutation.error)}
              </Body1>
            )}
          </DialogContent>
          <DialogActions>
            <DialogTrigger disableButtonEnhancement>
              <Button appearance="secondary">キャンセル</Button>
            </DialogTrigger>
            <Button
              appearance="primary"
              disabled={!goal.trim() || mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? (
                <>
                  <Spinner size="tiny" /> 分解中…
                </>
              ) : (
                hasGoal ? '更新 & 再分解' : '追加 & 分解'
              )}
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}
