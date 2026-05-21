import { makeStyles, tokens } from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';

import { Kpi, KpiRow } from '@/components/primitives/Kpi';
import { Skeleton } from '@/components/primitives/Skeleton';
import { AreaChart } from '@/components/primitives/AreaChart';
import { RecentMeetings } from '@/components/RecentMeetings';
import { api } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  page: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: 'calc(100vh - 52px)',
  },
  hero: {
    borderBottom: '1px solid var(--border-hairline)',
    padding: '32px 32px 28px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  eyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    color: 'var(--accent)',
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
    marginTop: '4px',
  },
  body: {
    padding: '24px 32px 56px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  panelRow: {
    display: 'grid',
    gridTemplateColumns: '1.5fr 1fr',
    gap: '16px',
    '@media (max-width: 1024px)': {
      gridTemplateColumns: '1fr',
    },
  },
  panel: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    overflow: 'hidden',
  },
  panelHeader: {
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  panelTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
  },
  panelMeta: {
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  chartWrap: {
    padding: '12px 18px 18px',
  },
  agentList: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
  },
  agentRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 18px',
    borderBottom: '1px solid var(--border-hairline)',
    fontSize: '13px',
  },
  agentRowLast: {
    borderBottom: 'none',
  },
  agentName: {
    color: 'var(--text-1)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  agentValue: {
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
    fontVariantNumeric: 'tabular-nums',
    fontSize: '12px',
  },
});

function fmtUsd(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}

function fmtTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return value.toString();
}

export function Insights() {
  const styles = useStyles();
  const { userId } = useIdentity();

  const { data: summary, isLoading } = useQuery({
    queryKey: ['usage-summary', userId],
    queryFn: () => api.getUsageSummary(userId, 30),
    staleTime: 60_000,
  });

  const trendData =
    summary?.by_day?.map((d) => ({
      label: d.date.slice(5),
      value: d.cost_usd,
    })) ?? [];

  const paddedTrend =
    trendData.length === 0
      ? Array.from({ length: 7 }, (_, i) => ({ label: `d-${6 - i}`, value: 0 }))
      : trendData;

  const agents = Object.entries(summary?.by_agent ?? {})
    .map(([name, cost]) => ({ name, cost }))
    .sort((a, b) => b.cost - a.cost)
    .slice(0, 6);

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <span className={styles.eyebrow}>INSIGHTS · last 30 days</span>
        <h1 className={styles.headline}>会議運営の数字</h1>
        <p className={styles.lede}>
          Helmsman がここ 30 日に実行したセッション数 / LLM コスト / agent
          別の負荷を集計します。1 円単位のコスト透明性を担保。
        </p>
      </section>

      <div className={styles.body}>
        {isLoading ? (
          <KpiRow>
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} height={84} />
            ))}
          </KpiRow>
        ) : (
          <KpiRow>
            <Kpi
              label="Sessions"
              value={<span className="num-mono">{summary?.total_meetings ?? 0}</span>}
              hint="last 30 days"
            />
            <Kpi
              label="LLM cost"
              value={
                <span className="num-mono">{fmtUsd(summary?.total_cost_usd ?? 0)}</span>
              }
              hint={`${fmtTokens(summary?.total_tokens ?? 0)} tokens`}
            />
            <Kpi
              label="Avg / session"
              value={
                <span className="num-mono">
                  {fmtUsd(summary?.avg_cost_per_meeting_usd ?? 0)}
                </span>
              }
              hint="LLM only"
            />
            <Kpi
              label="Agents in play"
              value={<span className="num-mono">{Object.keys(summary?.by_agent ?? {}).length}</span>}
              hint="goal · coverage · steering …"
            />
          </KpiRow>
        )}

        <div className={styles.panelRow}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>Cost trend</h2>
              <span className={styles.panelMeta}>
                {paddedTrend.length}d · USD
              </span>
            </div>
            <div className={styles.chartWrap}>
              <AreaChart data={paddedTrend} height={160} showAxis />
            </div>
          </div>

          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>Top agents by spend</h2>
              <span className={styles.panelMeta}>USD</span>
            </div>
            {agents.length === 0 ? (
              <div style={{ padding: '20px 18px', color: tokens.colorNeutralForeground3, fontSize: 13 }}>
                まだ呼び出しがありません。
              </div>
            ) : (
              <ul className={styles.agentList}>
                {agents.map((a, i) => (
                  <li
                    key={a.name}
                    className={`${styles.agentRow}${
                      i === agents.length - 1 ? ` ${styles.agentRowLast}` : ''
                    }`}
                  >
                    <span className={styles.agentName}>{a.name}</span>
                    <span className={styles.agentValue}>{fmtUsd(a.cost)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <RecentMeetings organizerId={userId} />
      </div>
    </div>
  );
}
