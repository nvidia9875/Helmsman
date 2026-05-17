import {
  Body1,
  Button,
  Dropdown,
  Field,
  Input,
  Option,
  Spinner,
  Textarea,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api, type MeetingMode } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    maxWidth: '720px',
    margin: '64px auto',
    padding: '32px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  hint: {
    color: tokens.colorNeutralForeground3,
  },
});

const MODES: MeetingMode[] = ['Decision', 'Brainstorm', 'Status', 'Interview', '1on1', 'Kickoff'];

export function CreateMeeting() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { userId, displayName, setName } = useIdentity();
  const [goal, setGoal] = useState('');
  const [mode, setMode] = useState<MeetingMode>('Decision');
  const [totalMinutes, setTotalMinutes] = useState(60);
  const [name, setNameLocal] = useState(displayName === 'Anonymous' ? '' : displayName);

  const mutation = useMutation({
    mutationFn: () =>
      api.startMeeting({
        organizer_id: userId,
        goal,
        mode,
        total_minutes: totalMinutes,
      }),
    onSuccess: (meeting) => {
      if (name) setName(name);
      navigate(`/m/${meeting.id}?organizer_id=${encodeURIComponent(userId)}`);
    },
  });

  const ready = goal.trim().length >= 4 && !!name.trim();

  return (
    <div className={styles.root}>
      <Title2>新しい会議を作る</Title2>
      <Body1 className={styles.hint}>
        ゴールを宣言すると、AI が論点を分解して会議室を発行します。
      </Body1>

      <Field label="あなたの表示名" required>
        <Input value={name} onChange={(_, d) => setNameLocal(d.value)} placeholder="例: 山田" />
      </Field>

      <Field label="ゴール (会議の最終的な決定 / 成果物)" required>
        <Textarea
          value={goal}
          onChange={(_, d) => setGoal(d.value)}
          placeholder="例: 6 月 30 日のローンチ可否を決定する"
          rows={3}
        />
      </Field>

      <Field label="モード">
        <Dropdown
          value={mode}
          selectedOptions={[mode]}
          onOptionSelect={(_, d) => d.optionValue && setMode(d.optionValue as MeetingMode)}
        >
          {MODES.map((m) => (
            <Option key={m} value={m}>
              {m}
            </Option>
          ))}
        </Dropdown>
      </Field>

      <Field label="予定時間 (分)">
        <Input
          type="number"
          value={String(totalMinutes)}
          min={5}
          max={240}
          onChange={(_, d) => setTotalMinutes(Math.max(5, Math.min(240, Number(d.value) || 60)))}
        />
      </Field>

      <Button
        appearance="primary"
        size="large"
        disabled={!ready || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? (
          <>
            <Spinner size="tiny" /> 論点を分解中...
          </>
        ) : (
          '会議を始める'
        )}
      </Button>

      {mutation.isError && (
        <Body1 style={{ color: tokens.colorPaletteRedForeground1 }}>
          エラー: {String(mutation.error)}
        </Body1>
      )}
    </div>
  );
}
