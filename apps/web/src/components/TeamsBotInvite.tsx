import {
  Badge,
  Body1,
  Button,
  Caption1,
  Field,
  Input,
  Spinner,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { api, type BotStatus, type Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorBrandStroke2}`,
    backgroundColor: tokens.colorBrandBackground2,
    borderRadius: tokens.borderRadiusLarge,
    padding: '20px',
    marginTop: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  controls: {
    display: 'flex',
    gap: '8px',
    alignItems: 'flex-end',
  },
  inputWrap: {
    flex: 1,
  },
  hint: {
    color: tokens.colorNeutralForeground3,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
  },
});

const STATUS_LABEL: Record<BotStatus, string> = {
  idle: '未参加',
  connecting: '接続中…',
  in_call: '会議に参加中',
  disconnected: '退出済',
  failed: '失敗',
};

const STATUS_COLOR: Record<BotStatus, 'subtle' | 'informative' | 'success' | 'warning' | 'danger'> = {
  idle: 'subtle',
  connecting: 'warning',
  in_call: 'success',
  disconnected: 'subtle',
  failed: 'danger',
};

interface Props {
  meeting: Meeting;
  organizerId: string;
}

export function TeamsBotInvite({ meeting, organizerId }: Props) {
  const styles = useStyles();
  const queryClient = useQueryClient();
  const [url, setUrl] = useState(meeting.teams_meeting_url ?? '');

  const inviteMutation = useMutation({
    mutationFn: () => api.inviteBot(meeting.id, organizerId, url),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meeting.id, organizerId] });
    },
  });

  const leaveMutation = useMutation({
    mutationFn: () => api.leaveBot(meeting.id, organizerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meeting.id, organizerId] });
    },
  });

  const status = meeting.bot_status;
  const isActive = status === 'connecting' || status === 'in_call';
  const isValidUrl = /^https:\/\/teams\.microsoft\.com\/.+meetup-join/.test(url);

  return (
    <section className={styles.root} aria-label="Teams Bot 招待">
      <div className={styles.header}>
        <Title3 as="h2" style={{ margin: 0 }}>
          🤖 Helmsman Bot を Teams 会議に参加させる
        </Title3>
        <Badge appearance="filled" color={STATUS_COLOR[status]}>
          {STATUS_LABEL[status]}
        </Badge>
      </div>
      <Caption1>
        Teams 会議 (paid Teams テナント) の「参加リンクをコピー」した URL を貼り付けてください。
        Bot が「Helmsman 🧭 (External)」として参加し、音声を Speech SDK で文字起こし → 8 agents で分析します。
      </Caption1>

      <div className={styles.controls}>
        <div className={styles.inputWrap}>
          <Field label="Teams 会議 URL">
            <Input
              value={url}
              onChange={(_, d) => setUrl(d.value)}
              placeholder="https://teams.microsoft.com/l/meetup-join/..."
              disabled={isActive}
            />
          </Field>
        </div>
        {isActive ? (
          <Button
            appearance="secondary"
            onClick={() => leaveMutation.mutate()}
            disabled={leaveMutation.isPending}
          >
            {leaveMutation.isPending ? <Spinner size="tiny" /> : '退出'}
          </Button>
        ) : (
          <Button
            appearance="primary"
            onClick={() => inviteMutation.mutate()}
            disabled={!isValidUrl || inviteMutation.isPending}
          >
            {inviteMutation.isPending ? (
              <>
                <Spinner size="tiny" /> 招待中…
              </>
            ) : (
              '🤖 Bot を招待'
            )}
          </Button>
        )}
      </div>

      {!isValidUrl && url.length > 0 && (
        <Body1 className={styles.errorText}>
          Teams 会議 URL の形式が不正です (https://teams.microsoft.com/.../meetup-join/...)
        </Body1>
      )}

      {inviteMutation.isError && (
        <Body1 className={styles.errorText}>
          招待失敗: {String(inviteMutation.error)}
        </Body1>
      )}

      {meeting.bot_call_connection_id && (
        <Caption1>Call ID: {meeting.bot_call_connection_id.slice(0, 8)}…</Caption1>
      )}
    </section>
  );
}
