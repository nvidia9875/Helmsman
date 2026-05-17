import { Button, makeStyles, tokens } from '@fluentui/react-components';
import { ArrowRight24Regular, Rocket24Regular } from '@fluentui/react-icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { Pill } from '@/components/primitives/Pill';
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
    display: 'grid',
    gridTemplateColumns: '1.4fr 1fr',
    gap: '32px',
    alignItems: 'end',
    '@media (max-width: 960px)': {
      gridTemplateColumns: '1fr',
    },
  },
  heroLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    minWidth: 0,
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
    fontSize: 'clamp(28px, 4vw, 44px)',
    lineHeight: 1.05,
    letterSpacing: '-0.025em',
    fontWeight: 600,
    color: 'var(--text-1)',
    maxWidth: '720px',
  },
  lead: {
    fontSize: '15px',
    lineHeight: 1.65,
    color: 'var(--text-2)',
    margin: 0,
    maxWidth: '640px',
  },
  ctaRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginTop: '4px',
  },
  badges: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
    marginTop: '2px',
  },
  heroRight: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    padding: '18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    fontSize: '12px',
  },
  heroRightTitle: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
  },
  diff: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
    fontSize: '12px',
  },
  diffCol: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '8px',
    padding: '12px',
    backgroundColor: 'var(--bg-2)',
  },
  diffColAccent: {
    border: '1px solid var(--accent-soft)',
    borderRadius: '8px',
    padding: '12px',
    backgroundColor: 'var(--accent-soft)',
  },
  diffTitle: {
    fontSize: '10px',
    fontWeight: 700,
    color: 'var(--text-2)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    margin: '0 0 8px',
    fontFamily: 'var(--font-mono)',
  },
  diffList: {
    margin: 0,
    padding: 0,
    listStyle: 'none',
    color: 'var(--text-2)',
    lineHeight: 1.6,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  diffDot: {
    color: 'var(--text-4)',
    fontFamily: 'var(--font-mono)',
    marginRight: '6px',
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
  link: {
    color: 'var(--accent)',
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

export function Landing() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { userId } = useIdentity();

  const { data: summary, isLoading } = useQuery({
    queryKey: ['usage-summary', userId],
    queryFn: () => api.getUsageSummary(userId, 30),
    staleTime: 60_000,
  });

  const trendData =
    summary?.by_day?.map((d) => ({
      label: d.date.slice(5), // MM-DD
      value: d.cost_usd,
    })) ?? [];

  // Pad to at least 7 points for visual continuity
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
        <div className={styles.heroLeft}>
          <span className={styles.eyebrow}>AI MEETING CO-PILOT · v0.1</span>
          <h1 className={styles.headline}>
            Teams 会議に AI 副操縦士を派遣する
          </h1>
          <p className={styles.lead}>
            会議は作らない。<strong>カレンダーに既にある</strong> Teams 会議の URL を貼ると、
            Bot が外部参加者として join し、議論を 8 並列エージェントで分析、
            必要なら音声で介入します。
          </p>
          <div className={styles.ctaRow}>
            <Button
              appearance="primary"
              size="large"
              icon={<Rocket24Regular />}
              onClick={() => navigate('/new')}
            >
              Bot を派遣
            </Button>
            <Button
              appearance="subtle"
              icon={<ArrowRight24Regular />}
              iconPosition="after"
              as="a"
              href="https://github.com/nvidia9875/Helmsman"
              target="_blank"
            >
              GitHub で見る
            </Button>
          </div>
          <div className={styles.badges}>
            <Pill kind="success">Copilot 不要</Pill>
            <Pill kind="success">外部参加者として join</Pill>
            <Pill kind="success">音声介入 (L3)</Pill>
            <Pill kind="brand">MIT OSS</Pill>
          </div>
        </div>

        <aside className={styles.heroRight}>
          <div className={styles.heroRightTitle}>
            <span>vs Microsoft Facilitator</span>
            <a
              className={styles.link}
              href="https://learn.microsoft.com/ja-jp/microsoftteams/facilitator-teams"
              target="_blank"
              rel="noreferrer"
              style={{ fontSize: '11px' }}
            >
              docs ↗
            </a>
          </div>
          <div className={styles.diff}>
            <div className={styles.diffCol}>
              <p className={styles.diffTitle}>FACILITATOR</p>
              <ul className={styles.diffList}>
                <li><span className={styles.diffDot}>—</span>Copilot $30/月</li>
                <li><span className={styles.diffDot}>—</span>テキストのみ</li>
                <li><span className={styles.diffDot}>—</span>外部会議 NG</li>
                <li><span className={styles.diffDot}>—</span>単一 AI</li>
              </ul>
            </div>
            <div className={styles.diffColAccent}>
              <p className={styles.diffTitle} style={{ color: 'var(--accent)' }}>
                HELMSMAN
              </p>
              <ul className={styles.diffList}>
                <li><span className={styles.diffDot}>＋</span>追加課金なし</li>
                <li><span className={styles.diffDot}>＋</span>音声介入 L3</li>
                <li><span className={styles.diffDot}>＋</span>外部 OK</li>
                <li><span className={styles.diffDot}>＋</span>8 並列 agents</li>
              </ul>
            </div>
          </div>
        </aside>
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
