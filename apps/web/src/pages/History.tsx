/**
 * History page (Phase 7) — 主催者の過去会議で確定した「決定」を時系列 + 検索で閲覧。
 *
 * 構成:
 *   - hero: 自然言語検索バー (POST /decisions/search)
 *   - フィルタ chip: series / group
 *   - 時系列カードリスト: 日付見出し + decision カード
 *   - 各カードは meeting_id にリンク (会議詳細へ)
 */
import { Button, Input, Spinner, makeStyles } from '@fluentui/react-components';
import { Search20Regular, Dismiss20Regular } from '@fluentui/react-icons';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Skeleton } from '@/components/primitives/Skeleton';
import { api, type Decision, type DecisionSearchHit } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  page: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: 'calc(100vh - 52px)',
  },
  hero: {
    borderBottom: '1px solid var(--border-hairline)',
    padding: '32px 32px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  eyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    color: 'var(--accent-violet)',
    fontFamily: 'var(--font-mono)',
  },
  headline: {
    margin: 0,
    fontSize: 'clamp(22px, 3vw, 32px)',
    lineHeight: 1.1,
    letterSpacing: '-0.02em',
    fontWeight: 600,
    color: 'var(--text-1)',
    maxWidth: '720px',
  },
  lede: {
    color: 'var(--text-2)',
    fontSize: '13px',
    lineHeight: 1.6,
    maxWidth: '640px',
  },
  searchBar: {
    display: 'flex',
    gap: '8px',
    maxWidth: '720px',
    marginTop: '8px',
  },
  searchInput: {
    flex: 1,
  },
  body: {
    padding: '24px 32px 56px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    maxWidth: '900px',
    width: '100%',
  },
  modeBanner: {
    fontSize: '11px',
    color: 'var(--accent-violet)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  empty: {
    color: 'var(--text-3)',
    fontSize: '13px',
    padding: '32px 0',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  dayGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  dayHeader: {
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-3)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    margin: 0,
    padding: '8px 0 4px',
    borderTop: '1px solid var(--border-hairline)',
  },
  card: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    transitionProperty: 'border-color, background-color',
    transitionDuration: '120ms',
    ':hover': {
      border: '1px solid var(--accent-violet)',
      backgroundColor: 'var(--bg-2)',
    },
  },
  cardHead: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: '12px',
  },
  cardTopic: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
    lineHeight: 1.3,
  },
  cardMeta: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-3)',
    fontVariantNumeric: 'tabular-nums',
    display: 'flex',
    gap: '8px',
    flexShrink: 0,
  },
  cardBody: {
    fontSize: '13px',
    color: 'var(--text-2)',
    lineHeight: 1.55,
    margin: 0,
  },
  cardFooter: {
    display: 'flex',
    gap: '12px',
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  cardLink: {
    color: 'var(--accent)',
    textDecoration: 'none',
    ':hover': { textDecoration: 'underline' },
  },
  scoreBadge: {
    color: 'var(--accent-violet)',
  },
});

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

function fmtDayKey(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

type ListItem = (Decision | DecisionSearchHit) & { score?: number };

function groupByDay(items: ListItem[]): Array<{ day: string; items: ListItem[] }> {
  const buckets: Record<string, ListItem[]> = {};
  for (const d of items) {
    const day = fmtDayKey(d.captured_at);
    if (!buckets[day]) buckets[day] = [];
    buckets[day].push(d);
  }
  return Object.keys(buckets)
    .sort((a, b) => (a > b ? -1 : 1))
    .map((day) => ({ day, items: buckets[day] }));
}

export function History() {
  const styles = useStyles();
  const { userId } = useIdentity();
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState('');

  // listing path (browsing)
  const list = useQuery({
    queryKey: ['decisions', userId],
    queryFn: () => api.listDecisions(userId, { withinDays: 365, limit: 200 }),
    staleTime: 30_000,
  });

  // search path (semantic)
  const search = useQuery({
    queryKey: ['decisions-search', userId, submitted],
    queryFn: () =>
      api.searchDecisions({
        query: submitted,
        organizer_id: userId,
        top_k: 30,
        within_days: 365,
      }),
    enabled: submitted.length > 0,
    staleTime: 30_000,
  });

  const inSearchMode = submitted.length > 0;
  const items: ListItem[] = inSearchMode
    ? (search.data ?? []).map((h) => h as ListItem)
    : (list.data ?? []).map((d) => d as ListItem);

  const grouped = useMemo(() => groupByDay(items), [items]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(query.trim());
  };
  const clearSearch = () => {
    setQuery('');
    setSubmitted('');
  };

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <span className={styles.eyebrow}>HELMSMAN · MEMORY</span>
        <h1 className={styles.headline}>過去の決定を、AI と一緒に思い出す。</h1>
        <p className={styles.lede}>
          シリーズ会議やグループ会議で AI が拾った決定を、自然言語で横断検索できます。
          「あの時こう決めたやつ」を聞けば、AI が ベクトル類似で関連の高い決定から
          並べます。
        </p>
        <form className={styles.searchBar} onSubmit={onSubmit}>
          <Input
            value={query}
            onChange={(_, d) => setQuery(d.value)}
            placeholder="例: 価格、撤退基準、サブスク料金 …"
            contentBefore={<Search20Regular />}
            className={styles.searchInput}
          />
          <Button type="submit" appearance="primary" disabled={!query.trim()}>
            検索
          </Button>
          {inSearchMode && (
            <Button
              appearance="subtle"
              icon={<Dismiss20Regular />}
              onClick={clearSearch}
              title="検索を解除"
            >
              解除
            </Button>
          )}
        </form>
      </header>

      <main className={styles.body}>
        {inSearchMode && (
          <div className={styles.modeBanner}>
            <span>📜</span>
            <span>
              SEARCH RESULTS · 「{submitted}」 · {search.isFetching ? '実行中…' : `${items.length} 件`}
            </span>
          </div>
        )}

        {(list.isLoading && !inSearchMode) || (search.isLoading && inSearchMode) ? (
          <>
            <Skeleton height={64} />
            <Skeleton height={64} />
            <Skeleton height={64} />
          </>
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            {inSearchMode
              ? '(マッチする過去決定が見つかりませんでした)'
              : '(まだ決定が記録されていません — 会議で議論を進めると、DecisionCapture が拾います)'}
          </div>
        ) : (
          grouped.map(({ day, items: dayItems }) => (
            <section key={day} className={styles.dayGroup}>
              <h2 className={styles.dayHeader}>{day}</h2>
              {dayItems.map((d) => (
                <article key={d.id} className={styles.card}>
                  <header className={styles.cardHead}>
                    <h3 className={styles.cardTopic}>{d.topic_name}</h3>
                    <div className={styles.cardMeta}>
                      <span>{fmtDate(d.captured_at)}</span>
                      {d.score !== undefined && (
                        <span className={styles.scoreBadge}>
                          score {d.score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </header>
                  <p className={styles.cardBody}>{d.decision_text}</p>
                  <footer className={styles.cardFooter}>
                    {d.owner && <span>担当: {d.owner}</span>}
                    {d.deadline && <span>期日: {d.deadline}</span>}
                    {d.series_id && <span>series</span>}
                    {d.group_id && <span>group</span>}
                    <Link
                      to={`/m/${d.meeting_id}?organizer_id=${encodeURIComponent(userId)}`}
                      className={styles.cardLink}
                    >
                      会議へ →
                    </Link>
                  </footer>
                </article>
              ))}
            </section>
          ))
        )}

        {(inSearchMode && search.isError) || (!inSearchMode && list.isError) ? (
          <div className={styles.empty}>
            (取得に失敗しました — しばらくしてからやり直してください)
            {inSearchMode && search.isLoading && <Spinner size="tiny" />}
          </div>
        ) : null}
      </main>
    </div>
  );
}
