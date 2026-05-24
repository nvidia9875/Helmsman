/**
 * SoloMicCard — ブラウザ単独でも Helmsman を試せる solo mode。
 *
 * Teams bot を派遣しない (=needsDispatch && !bot active) ときに表示。
 * Web Speech API (Chrome/Edge) でブラウザマイクの音声を STT し、
 * ローカルに溜めた utterance を Tick エンドポイントへ送り込んで agents を走らせる。
 *
 * UX 方針: 1 ボタンで「録音開始 → 自動的に最新 15 発言で Tick が走る」よう、
 * append の都度 debounced auto-tick を発火させる。
 */
import { Button, Input, Textarea, makeStyles, mergeClasses } from '@fluentui/react-components';
import {
  Bot24Regular,
  Delete20Regular,
  Mic24Filled,
  Mic24Regular,
  Send20Regular,
  Sparkle20Regular,
} from '@fluentui/react-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { useBrowserSTT } from '@/hooks/useBrowserSTT';
import { useUtteranceLog } from '@/hooks/useUtteranceLog';
import { api, type Meeting } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '12px',
    backgroundColor: 'var(--bg-1)',
    backdropFilter: 'blur(12px) saturate(140%)',
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
    padding: '18px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: '12px',
    flexWrap: 'wrap',
  },
  eyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: 'var(--accent-violet)',
    fontFamily: 'var(--font-mono)',
  },
  title: {
    fontSize: '14px',
    fontWeight: 600,
    margin: 0,
    color: 'var(--text-1)',
  },
  desc: {
    fontSize: '12px',
    color: 'var(--text-3)',
    margin: 0,
  },
  micRow: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  interim: {
    flex: 1,
    minWidth: '180px',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
  },
  textRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'flex-start',
  },
  textarea: {
    flex: 1,
  },
  log: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    maxHeight: '160px',
    overflowY: 'auto',
    padding: '10px 12px',
    backgroundColor: 'var(--bg-0)',
    borderRadius: '8px',
    border: '1px solid var(--border-hairline)',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-2)',
  },
  logEmpty: {
    color: 'var(--text-4)',
    fontStyle: 'italic',
  },
  controls: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    alignItems: 'center',
    paddingTop: '4px',
  },
  count: {
    marginLeft: 'auto',
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    fontVariantNumeric: 'tabular-nums',
  },
  intervention: {
    border: '1px solid rgba(176, 124, 255, 0.3)',
    backgroundColor: 'rgba(176, 124, 255, 0.06)',
    borderRadius: '8px',
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  interventionHead: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--accent-violet)',
    fontWeight: 600,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
  },
  interventionBody: {
    color: 'var(--text-1)',
    fontSize: '13px',
    lineHeight: 1.55,
  },
  unsupported: {
    fontSize: '12px',
    color: 'var(--text-3)',
    padding: '8px 0',
  },
});

interface Props {
  meeting: Meeting;
  organizerId: string;
}

export function SoloMicCard({ meeting, organizerId }: Props) {
  const styles = useStyles();
  const queryClient = useQueryClient();
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
      queryClient.invalidateQueries({ queryKey: ['meeting', meeting.id, organizerId] });
    },
  });

  const submitText = () => {
    if (!text.trim()) return;
    append(text);
    setText('');
  };

  return (
    <section className={styles.root} aria-label="Solo mode — ブラウザマイク + tick">
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>SOLO MODE · BROWSER MIC</div>
          <h3 className={styles.title}>Teams を使わず、このタブで一人で試す</h3>
          <p className={styles.desc}>
            ブラウザマイクの発言 (or テキスト入力) を溜めて Tick を回します。
            会議に派遣せずデモ・評価したい時にどうぞ。
          </p>
        </div>
      </header>

      {stt.available ? (
        <div className={styles.micRow}>
          <Button
            appearance={stt.listening ? 'primary' : 'secondary'}
            icon={stt.listening ? <Mic24Filled /> : <Mic24Regular />}
            onClick={() => (stt.listening ? stt.stop() : stt.start())}
          >
            {stt.listening ? '聞き取り中... 停止' : 'マイクで話す'}
          </Button>
          <Input
            value={stt.interim}
            readOnly
            placeholder={stt.listening ? '...' : 'マイク待機中'}
            className={styles.interim}
          />
        </div>
      ) : (
        <p className={styles.unsupported}>
          (このブラウザは Web Speech API 非対応です。Chrome / Edge で開いてください。テキスト入力は使えます)
        </p>
      )}

      <div className={styles.textRow}>
        <Textarea
          value={text}
          onChange={(_, d) => setText(d.value)}
          placeholder="発言をテキストで追加 (例: 技術完成度のことから話そう)"
          rows={2}
          className={styles.textarea}
        />
        <Button
          appearance="secondary"
          icon={<Send20Regular />}
          onClick={submitText}
          disabled={!text.trim()}
        >
          追加
        </Button>
      </div>

      <div className={styles.log}>
        {utterances.length === 0 ? (
          <span className={mergeClasses(styles.logEmpty)}>(まだ発言なし — マイクかテキストで追加)</span>
        ) : (
          utterances.slice(-15).map((u) => (
            <div key={u.id}>
              <span style={{ color: 'var(--accent-cyan)' }}>[{u.speaker_id.slice(0, 6)}]</span> {u.text}
            </div>
          ))
        )}
      </div>

      <div className={styles.controls}>
        <Button
          appearance="primary"
          icon={<Sparkle20Regular />}
          onClick={() => tickMutation.mutate()}
          disabled={tickMutation.isPending || utterances.length === 0}
        >
          {tickMutation.isPending ? 'エージェント実行中...' : 'Helmsman を回す (Tick)'}
        </Button>
        <Button
          appearance="subtle"
          icon={<Delete20Regular />}
          onClick={clear}
          disabled={utterances.length === 0}
        >
          ログ消去
        </Button>
        <span className={styles.count}>{utterances.length} utterance(s) buffered</span>
      </div>

      {lastIntervention && (
        <div className={styles.intervention}>
          <div className={styles.interventionHead}>
            <Bot24Regular fontSize={16} />
            {lastIntervention.agent} · {lastIntervention.level}
          </div>
          <p className={styles.interventionBody}>{lastIntervention.content}</p>
        </div>
      )}
    </section>
  );
}
