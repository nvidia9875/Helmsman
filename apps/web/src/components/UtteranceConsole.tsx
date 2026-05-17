import {
  Body1,
  Button,
  Input,
  Spinner,
  Textarea,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { Mic24Filled, Mic24Regular } from '@fluentui/react-icons';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { useBrowserSTT } from '@/hooks/useBrowserSTT';
import { useUtteranceLog } from '@/hooks/useUtteranceLog';
import { api, type Meeting } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '16px',
    marginTop: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  row: { display: 'flex', gap: '8px', alignItems: 'flex-start' },
  log: {
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
    padding: '8px',
    maxHeight: '180px',
    overflowY: 'auto',
    fontFamily: tokens.fontFamilyMonospace,
    fontSize: '12px',
  },
  interventionCard: {
    border: `1px solid ${tokens.colorBrandStroke1}`,
    backgroundColor: tokens.colorBrandBackground2,
    borderRadius: tokens.borderRadiusMedium,
    padding: '12px',
    marginTop: '8px',
  },
});

export function UtteranceConsole({
  meeting,
  organizerId,
  onTickComplete,
}: {
  meeting: Meeting;
  organizerId: string;
  onTickComplete: () => void;
}) {
  const styles = useStyles();
  const { userId, displayName } = useIdentity();
  const { utterances, append, clear } = useUtteranceLog(meeting.id, userId);
  const [text, setText] = useState('');
  const [lastIntervention, setLastIntervention] = useState<{
    agent: string;
    content: string;
    level: string;
  } | null>(null);

  const stt = useBrowserSTT('ja-JP', (finalText) => append(finalText));

  const tickMutation = useMutation({
    mutationFn: () =>
      api.tick(meeting.id, organizerId, {
        recent_utterances: utterances.slice(-15),
        participants: [
          {
            id: userId,
            meeting_id: meeting.id,
            display_name: displayName,
            entra_id: null,
            voiceprint_profile_id: null,
            is_chair: true,
            is_senior: false,
            joined_at: new Date().toISOString(),
            total_speak_seconds: utterances.reduce((s, u) => s + u.duration_sec, 0),
            utterance_count: utterances.length,
          },
        ],
        chair_id: userId,
        current_speaker_id: userId,
      }),
    onSuccess: (res) => {
      if (res.delivery) {
        setLastIntervention({
          agent: res.delivery.agent,
          content: res.delivery.content,
          level: res.delivery.level,
        });
      }
      onTickComplete();
    },
  });

  return (
    <div className={styles.root}>
      <Title3>🎤 発言ログ & 介入</Title3>

      <div className={styles.row}>
        <Textarea
          value={text}
          onChange={(_, d) => setText(d.value)}
          placeholder="発言を入力 (例: 技術完成度のことを話そう)"
          rows={2}
          style={{ flex: 1 }}
        />
        <Button
          appearance="primary"
          onClick={() => {
            append(text);
            setText('');
          }}
          disabled={!text.trim()}
        >
          追加
        </Button>
      </div>

      {stt.available ? (
        <div className={styles.row}>
          <Button
            icon={stt.listening ? <Mic24Filled /> : <Mic24Regular />}
            appearance={stt.listening ? 'primary' : 'secondary'}
            onClick={() => (stt.listening ? stt.stop() : stt.start())}
          >
            {stt.listening ? '聞き取り中... (停止)' : 'マイクで話す (Web Speech API)'}
          </Button>
          {stt.interim && (
            <Input value={stt.interim} readOnly style={{ flex: 1 }} />
          )}
        </div>
      ) : (
        <Body1 style={{ color: tokens.colorNeutralForeground3 }}>
          (Web Speech API 非対応のブラウザです。手入力か Azure Speech 連携を使ってください)
        </Body1>
      )}

      <div className={styles.log}>
        {utterances.length === 0 ? (
          <Body1>(まだ発言なし)</Body1>
        ) : (
          utterances.slice(-15).map((u) => (
            <div key={u.id}>
              [{u.speaker_id.slice(0, 8)}] {u.text}
            </div>
          ))
        )}
      </div>

      <div className={styles.row}>
        <Button
          appearance="primary"
          onClick={() => tickMutation.mutate()}
          disabled={tickMutation.isPending || utterances.length === 0}
        >
          {tickMutation.isPending ? (
            <>
              <Spinner size="tiny" /> エージェント実行中...
            </>
          ) : (
            '⚡ Helmsman を走らせる (Tick)'
          )}
        </Button>
        <Button onClick={clear} disabled={utterances.length === 0}>
          ログをクリア
        </Button>
      </div>

      {lastIntervention && (
        <div className={styles.interventionCard}>
          <strong>🧭 {lastIntervention.agent}</strong> [{lastIntervention.level}]
          <Body1>{lastIntervention.content}</Body1>
        </div>
      )}
    </div>
  );
}
