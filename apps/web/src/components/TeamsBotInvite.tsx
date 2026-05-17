import {
  Body1,
  Button,
  Caption1,
  Field,
  Input,
  Spinner,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { Section } from '@/components/primitives/Section';
import { api, type Meeting } from '@/lib/api';

const useStyles = makeStyles({
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  intro: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
    lineHeight: 1.6,
    margin: 0,
  },
  controls: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    gap: '8px',
    alignItems: 'flex-end',
  },
  errorText: {
    color: '#fca5a5',
    fontSize: '12px',
  },
  meta: {
    color: tokens.colorNeutralForeground3,
    fontSize: '11px',
  },
});

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
    <Section title="Bot を Teams 会議に派遣">
      <div className={styles.body}>
        <p className={styles.intro}>
          Teams カレンダーの会議で「参加リンクをコピー」した URL を貼り付け。
          Bot が「Helmsman 🧭 (External)」として参加します。
        </p>

        <div className={styles.controls}>
          <Field label="Teams 会議 URL">
            <Input
              value={url}
              onChange={(_, d) => setUrl(d.value)}
              placeholder="https://teams.microsoft.com/l/meetup-join/..."
              disabled={isActive}
            />
          </Field>
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
                '派遣'
              )}
            </Button>
          )}
        </div>

        {!isValidUrl && url.length > 0 && (
          <span className={styles.errorText}>
            URL の形式が不正です (https://teams.microsoft.com/.../meetup-join/...)
          </span>
        )}

        {inviteMutation.isError && (
          <Body1 className={styles.errorText}>
            派遣失敗: {String(inviteMutation.error)}
          </Body1>
        )}

        {meeting.bot_call_connection_id && (
          <Caption1 className={styles.meta}>
            Call ID: {meeting.bot_call_connection_id.slice(0, 8)}…
          </Caption1>
        )}
      </div>
    </Section>
  );
}
