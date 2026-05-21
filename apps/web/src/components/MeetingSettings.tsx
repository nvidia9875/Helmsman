/**
 * MeetingSettings — 会議の追加設定 UI。
 * - AI ファシリテーター名 (テキスト)
 * - 議論方向確認 (Steering) on/off
 * - タイムキーパー alerts (CRUD: 何分後・メッセージ・enable)
 *
 * PATCH /meetings/{id}/settings で永続化。
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Field,
  Input,
  Spinner,
  Switch,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { Add20Regular, Delete20Regular } from '@fluentui/react-icons';
import { useState, useEffect } from 'react';
import { api, type Meeting, type TimekeeperAlert } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: '10px',
    backgroundColor: tokens.colorNeutralBackground1,
    padding: '16px 18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  header: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: '8px',
  },
  title: {
    margin: 0,
    fontSize: '13px',
    fontWeight: 600,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    color: tokens.colorNeutralForeground3,
  },
  saveBtn: { minWidth: '70px' },
  row: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  toggleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    paddingTop: '4px',
  },
  toggleLabel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    flex: '1',
  },
  toggleTitle: { fontSize: '14px', fontWeight: 500 },
  toggleHint: {
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
  },
  alertsBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    borderTop: `1px solid ${tokens.colorNeutralStroke3}`,
    paddingTop: '12px',
  },
  alertRow: {
    display: 'grid',
    gridTemplateColumns: '50px 80px 1fr auto',
    gap: '8px',
    alignItems: 'center',
  },
  alertHeader: {
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  firedDot: {
    display: 'inline-block',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: tokens.colorPaletteRedBackground3,
    marginLeft: '4px',
  },
  empty: {
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
  },
  addBtn: { alignSelf: 'flex-start', marginTop: '4px' },
});

interface Props {
  meeting: Meeting;
  organizerId: string;
}

type DraftAlert = {
  id?: string;
  minutes_from_start: number;
  message: string;
  enabled: boolean;
  fired?: boolean;
};

export function MeetingSettings({ meeting, organizerId }: Props) {
  const styles = useStyles();
  const queryClient = useQueryClient();
  const [facilitator, setFacilitator] = useState(meeting.facilitator_name ?? '');
  const [steering, setSteering] = useState(meeting.steering_enabled);
  const [alerts, setAlerts] = useState<DraftAlert[]>(
    meeting.timekeeper_alerts.map(toDraft),
  );

  // meeting が外から再 fetch されたら sync (派遣直後など)
  useEffect(() => {
    setFacilitator(meeting.facilitator_name ?? '');
    setSteering(meeting.steering_enabled);
    setAlerts(meeting.timekeeper_alerts.map(toDraft));
  }, [meeting.id, meeting.facilitator_name, meeting.steering_enabled, meeting.timekeeper_alerts]);

  const save = useMutation({
    mutationFn: () =>
      api.updateSettings(meeting.id, organizerId, {
        facilitator_name: facilitator.trim() || null,
        steering_enabled: steering,
        timekeeper_alerts: alerts.map((a) => ({
          id: a.id ?? null,
          minutes_from_start: a.minutes_from_start,
          message: a.message,
          enabled: a.enabled,
        })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meeting.id, organizerId] });
    },
  });

  const dirty =
    (facilitator.trim() || null) !== (meeting.facilitator_name ?? null) ||
    steering !== meeting.steering_enabled ||
    !alertsEqual(alerts, meeting.timekeeper_alerts);

  const addAlert = () =>
    setAlerts((prev) => [
      ...prev,
      { minutes_from_start: 30, message: 'そろそろ次の議題に移りましょう。', enabled: true },
    ]);

  const updateAlert = (idx: number, patch: Partial<DraftAlert>) =>
    setAlerts((prev) => prev.map((a, i) => (i === idx ? { ...a, ...patch } : a)));

  const removeAlert = (idx: number) =>
    setAlerts((prev) => prev.filter((_, i) => i !== idx));

  return (
    <section className={styles.root} aria-label="会議設定">
      <div className={styles.header}>
        <h2 className={styles.title}>会議設定</h2>
        <Button
          size="small"
          appearance="primary"
          className={styles.saveBtn}
          disabled={!dirty || save.isPending}
          onClick={() => save.mutate()}
        >
          {save.isPending ? <Spinner size="extra-tiny" /> : '保存'}
        </Button>
      </div>

      <Field label="AI ファシリテーター名">
        <Input
          value={facilitator}
          onChange={(_, d) => setFacilitator(d.value)}
          placeholder="例: Helmsman, ナビ, ヘルメス…"
        />
      </Field>

      <div className={styles.toggleRow}>
        <div className={styles.toggleLabel}>
          <span className={styles.toggleTitle}>議論方向確認の音声介入</span>
          <span className={styles.toggleHint}>
            話がずれてきた時に「方向性を確認しますか?」と bot が音声で問いかける
          </span>
        </div>
        <Switch checked={steering} onChange={(_, d) => setSteering(d.checked)} />
      </div>

      <div className={styles.alertsBlock}>
        <div className={styles.toggleRow}>
          <div className={styles.toggleLabel}>
            <span className={styles.toggleTitle}>タイムキーパー音声通知</span>
            <span className={styles.toggleHint}>
              会議開始から指定分後に bot が音声でメッセージを読み上げる
            </span>
          </div>
        </div>

        {alerts.length === 0 ? (
          <div className={styles.empty}>まだ alert がありません。下のボタンで追加。</div>
        ) : (
          <>
            <div className={styles.alertRow} style={{ marginTop: '4px' }}>
              <span className={styles.alertHeader}>有効</span>
              <span className={styles.alertHeader}>分後</span>
              <span className={styles.alertHeader}>メッセージ</span>
              <span />
            </div>
            {alerts.map((a, i) => (
              <div className={styles.alertRow} key={`${a.id ?? 'new'}-${i}`}>
                <Switch
                  checked={a.enabled}
                  onChange={(_, d) => updateAlert(i, { enabled: d.checked })}
                />
                <Input
                  type="number"
                  size="small"
                  value={String(a.minutes_from_start)}
                  onChange={(_, d) =>
                    updateAlert(i, {
                      minutes_from_start: Math.max(1, Math.min(600, Number(d.value) || 1)),
                    })
                  }
                />
                <Input
                  size="small"
                  value={a.message}
                  onChange={(_, d) => updateAlert(i, { message: d.value })}
                  contentAfter={a.fired ? <span className={styles.firedDot} title="発火済み" /> : undefined}
                />
                <Button
                  size="small"
                  appearance="subtle"
                  icon={<Delete20Regular />}
                  onClick={() => removeAlert(i)}
                  aria-label="削除"
                />
              </div>
            ))}
          </>
        )}
        <Button
          size="small"
          appearance="secondary"
          icon={<Add20Regular />}
          className={styles.addBtn}
          onClick={addAlert}
        >
          alert 追加
        </Button>
      </div>
    </section>
  );
}

function toDraft(a: TimekeeperAlert): DraftAlert {
  return {
    id: a.id,
    minutes_from_start: a.minutes_from_start,
    message: a.message,
    enabled: a.enabled,
    fired: a.fired,
  };
}

function alertsEqual(drafts: DraftAlert[], saved: TimekeeperAlert[]): boolean {
  if (drafts.length !== saved.length) return false;
  for (let i = 0; i < drafts.length; i++) {
    const d = drafts[i];
    const s = saved[i];
    if (
      (d.id ?? null) !== s.id ||
      d.minutes_from_start !== s.minutes_from_start ||
      d.message !== s.message ||
      d.enabled !== s.enabled
    ) {
      return false;
    }
  }
  return true;
}
