/**
 * MemoryEchoCard — Phase 7 (会議横断記憶) の専用カード。
 *
 * 当会議で MemoryRetriever が surface した「過去会議の関連決定」を
 * サイドバーに視覚的に分離して表示する。InterventionFeed にも流れるが、
 * 「これは思い出させてるだけ」という性格が一目で分かるよう独立カードに。
 *
 * 表示ソース:
 *   1. meeting.delivered_interventions のうち agent === "MemoryRetriever"
 *   2. 親会議があれば、その past decisions も読み込んで「引き継ぎ候補」として
 *      展開可能 (オフラインでも見える状態に)
 */
import { makeStyles } from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';

import { api, type Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: '1px solid rgba(176, 124, 255, 0.32)',
    borderRadius: '10px',
    backgroundColor: 'rgba(176, 124, 255, 0.05)',
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  eyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: 'var(--accent-violet)',
    fontFamily: 'var(--font-mono)',
    display: 'flex',
    gap: '6px',
    alignItems: 'center',
  },
  count: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-4)',
    fontVariantNumeric: 'tabular-nums',
  },
  empty: {
    fontSize: '12px',
    color: 'var(--text-3)',
    lineHeight: 1.5,
    fontStyle: 'italic',
    margin: 0,
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  item: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '8px',
    backgroundColor: 'var(--bg-0)',
    padding: '10px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  itemHead: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: '8px',
  },
  itemTopic: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
    lineHeight: 1.3,
  },
  itemMeta: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-3)',
    fontVariantNumeric: 'tabular-nums',
    flexShrink: 0,
  },
  itemBody: {
    fontSize: '12px',
    color: 'var(--text-2)',
    lineHeight: 1.5,
    margin: 0,
  },
  itemOwner: {
    fontSize: '10px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  badge: {
    display: 'inline-flex',
    fontSize: '9px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    padding: '1px 6px',
    borderRadius: '999px',
    backgroundColor: 'rgba(176, 124, 255, 0.16)',
    color: 'var(--accent-violet)',
    fontWeight: 700,
  },
});

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  });
}

interface Props {
  meeting: Meeting;
  organizerId: string;
}

export function MemoryEchoCard({ meeting, organizerId }: Props) {
  const styles = useStyles();

  // 当会議で surface 済の memory intervention だけ抽出
  const memoryDeliveries = meeting.delivered_interventions.filter(
    (d) => d.agent === 'MemoryRetriever',
  );

  // 関連 decision の本体 (UI 表示用) を取得 — surfaced_decision_ids
  // を 1 件ずつ getDecision で引くが、UX 上 ≤ 5 件想定
  const decisionQueries = useQuery({
    queryKey: ['surfaced-decisions', meeting.id, meeting.surfaced_decision_ids],
    queryFn: async () => {
      const ids = meeting.surfaced_decision_ids ?? [];
      if (ids.length === 0) return [];
      const results = await Promise.allSettled(
        ids.map((id) => api.getDecision(id, organizerId)),
      );
      return results.flatMap((r) => (r.status === 'fulfilled' ? [r.value] : []));
    },
    enabled: (meeting.surfaced_decision_ids?.length ?? 0) > 0,
    staleTime: 30_000,
  });

  const surfaced = decisionQueries.data ?? [];
  const total = memoryDeliveries.length;

  return (
    <section className={styles.root} aria-label="過去会議からの引き継ぎ">
      <div className={styles.header}>
        <span className={styles.eyebrow}>
          <span>📜</span> Memory · Cross-meeting
        </span>
        <span className={styles.count}>{total} echo{total === 1 ? '' : 'es'}</span>
      </div>

      {total === 0 && surfaced.length === 0 ? (
        <p className={styles.empty}>
          (過去会議の関連決定がここに出てきます。シリーズ会議やグループ会議で議論を進めると、
          「前回こう決めましたよね」を AI が拾います)
        </p>
      ) : (
        <div className={styles.list}>
          {surfaced.length > 0
            ? surfaced.map((d) => (
                <article key={d.id} className={styles.item}>
                  <div className={styles.itemHead}>
                    <h4 className={styles.itemTopic}>
                      <span className={styles.badge}>recall</span>{' '}
                      {d.topic_name}
                    </h4>
                    <span className={styles.itemMeta}>{fmtDate(d.captured_at)}</span>
                  </div>
                  <p className={styles.itemBody}>{d.decision_text}</p>
                  {d.owner && (
                    <span className={styles.itemOwner}>担当: {d.owner}</span>
                  )}
                </article>
              ))
            : memoryDeliveries.map((m) => (
                <article key={m.id} className={styles.item}>
                  <div className={styles.itemHead}>
                    <h4 className={styles.itemTopic}>
                      <span className={styles.badge}>echo</span> 過去の決定
                    </h4>
                    <span className={styles.itemMeta}>
                      {new Date(m.delivered_at).toLocaleTimeString('ja-JP', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <p className={styles.itemBody}>{m.content}</p>
                </article>
              ))}
        </div>
      )}
    </section>
  );
}
