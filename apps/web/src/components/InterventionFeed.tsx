import { Button, Spinner, makeStyles } from '@fluentui/react-components';
import { Speaker220Regular } from '@fluentui/react-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { LevelBar } from '@/components/primitives/LevelBar';
import { api, type InterventionDelivery, type Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    backdropFilter: 'blur(12px) saturate(140%)',
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    minHeight: '320px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
  },
  title: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
  },
  count: {
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  feed: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    maxHeight: '560px',
  },
  item: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    columnGap: '12px',
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
  },
  itemLast: {
    borderBottom: 'none',
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    minWidth: 0,
  },
  topRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '10px',
    justifyContent: 'space-between',
  },
  agent: {
    fontSize: '11px',
    color: 'var(--text-2)',
    fontWeight: 500,
    letterSpacing: '0.04em',
    fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase',
  },
  level: {
    fontSize: '10px',
    color: 'var(--accent)',
    fontWeight: 700,
    letterSpacing: '0.1em',
    fontFamily: 'var(--font-mono)',
  },
  timestamp: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-3)',
    fontVariantNumeric: 'tabular-nums',
  },
  content: {
    fontSize: '14px',
    color: 'var(--text-1)',
    lineHeight: 1.55,
    margin: 0,
  },
  evidence: {
    fontSize: '12px',
    color: 'var(--text-3)',
    fontStyle: 'italic',
    paddingLeft: '12px',
    borderLeft: '2px solid var(--border-hairline)',
    marginTop: '6px',
    lineHeight: 1.5,
  },
  actionRow: {
    marginTop: '4px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  speakBtn: {
    fontSize: '11px',
    minHeight: '24px',
    paddingTop: '2px',
    paddingBottom: '2px',
  },
  speakHint: {
    fontSize: '10px',
    color: 'var(--text-4)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  speakDone: {
    fontSize: '10px',
    color: 'var(--success)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  speakError: {
    fontSize: '10px',
    color: '#fca5a5',
    fontFamily: 'var(--font-mono)',
  },
  empty: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 24px',
    color: 'var(--text-3)',
    fontSize: '13px',
    gap: '6px',
  },
  emptyMark: {
    fontSize: '24px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-4)',
    letterSpacing: '0.1em',
  },
});

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

interface Props {
  meeting: Meeting;
  organizerId: string;
}

export function InterventionFeed({ meeting, organizerId }: Props) {
  const styles = useStyles();
  const items: InterventionDelivery[] = [...meeting.delivered_interventions].reverse();
  const botInCall = meeting.bot_status === 'in_call';
  const [spokenIds, setSpokenIds] = useState<Record<string, boolean>>({});
  const [errorIds, setErrorIds] = useState<Record<string, string>>({});
  const queryClient = useQueryClient();

  const speakMutation = useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) =>
      api.speakIntoMeeting(meeting.id, organizerId, text).then((res) => ({ id, res })),
    onMutate: ({ id }) => {
      setErrorIds((prev) => {
        const { [id]: _omit, ...rest } = prev;
        return rest;
      });
    },
    onSuccess: ({ id }) => {
      setSpokenIds((prev) => ({ ...prev, [id]: true }));
      queryClient.invalidateQueries({
        queryKey: ['meeting', meeting.id, organizerId],
      });
    },
    onError: (err, variables) => {
      setErrorIds((prev) => ({ ...prev, [variables.id]: String(err) }));
    },
  });

  return (
    <section className={styles.root} aria-label="介入フィード">
      <div className={styles.header}>
        <h2 className={styles.title}>Intervention feed</h2>
        <span className={styles.count}>
          {items.length === 0 ? '— empty —' : `${items.length} delivered`}
        </span>
      </div>

      {items.length === 0 ? (
        <div className={styles.empty}>
          <span className={styles.emptyMark}>· · ·</span>
          <span>arbiter standing by</span>
          <span style={{ color: 'var(--text-4)', fontSize: 11 }}>
            会議が進むと AI 提案がここに流れます
          </span>
        </div>
      ) : (
        <div className={styles.feed}>
          {items.map((d, i) => {
            const promotable = d.level !== 'L3';
            const spoken = spokenIds[d.id];
            const speakingThis =
              speakMutation.isPending && speakMutation.variables?.id === d.id;
            const errorMsg = errorIds[d.id];

            return (
              <article
                key={d.id}
                className={`${styles.item}${i === items.length - 1 ? ` ${styles.itemLast}` : ''} fade-rise`}
              >
                <LevelBar level={d.level} />
                <div className={styles.body}>
                  <div className={styles.topRow}>
                    <span className={styles.agent}>
                      {d.agent} <span className={styles.level}>· {d.level}</span>
                    </span>
                    <span className={styles.timestamp}>{fmtTime(d.delivered_at)}</span>
                  </div>
                  <p className={styles.content}>{d.content}</p>
                  {d.evidence_quote && (
                    <p className={styles.evidence}>「{d.evidence_quote}」</p>
                  )}

                  {promotable && (
                    <div className={styles.actionRow}>
                      <Button
                        appearance="secondary"
                        size="small"
                        icon={<Speaker220Regular />}
                        className={styles.speakBtn}
                        disabled={!botInCall || speakingThis || spoken}
                        title={
                          !botInCall
                            ? 'Bot が会議に参加していないと発話できません'
                            : spoken
                              ? 'すでに発話済み'
                              : 'Bot が音声で会議に介入'
                        }
                        onClick={() =>
                          speakMutation.mutate({ id: d.id, text: d.content })
                        }
                      >
                        {speakingThis ? (
                          <>
                            <Spinner size="tiny" /> 発話中…
                          </>
                        ) : spoken ? (
                          '発話済み'
                        ) : (
                          `音声で介入 (${d.level}→L3)`
                        )}
                      </Button>
                      {!botInCall && (
                        <span className={styles.speakHint}>BOT OFFLINE</span>
                      )}
                      {spoken && (
                        <span className={styles.speakDone}>SPOKEN INTO CALL</span>
                      )}
                      {errorMsg && (
                        <span className={styles.speakError}>FAILED: {errorMsg}</span>
                      )}
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
