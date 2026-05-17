import { ProgressBar, makeStyles } from '@fluentui/react-components';

import type { MeetingUsage } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    padding: '4px 0',
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  label: {
    color: 'var(--text-3)',
    fontSize: '10px',
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  totalCost: {
    fontFamily: 'var(--font-mono)',
    fontSize: '26px',
    fontWeight: 600,
    color: 'var(--text-1)',
    fontVariantNumeric: 'tabular-nums',
    letterSpacing: '-0.02em',
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
    paddingTop: '12px',
    paddingBottom: '12px',
    borderTop: '1px solid var(--border-hairline)',
    borderBottom: '1px solid var(--border-hairline)',
  },
  metaCell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  metaCellLabel: {
    fontSize: '10px',
    color: 'var(--text-3)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-mono)',
  },
  metaValue: {
    fontFamily: 'var(--font-mono)',
    fontVariantNumeric: 'tabular-nums',
    fontSize: '14px',
    color: 'var(--text-1)',
  },
  agentList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  agentRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  agentRowHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '8px',
    fontSize: '12px',
    color: 'var(--text-2)',
  },
  agentName: {
    color: 'var(--text-1)',
    fontSize: '12px',
    fontWeight: 500,
  },
  agentMeta: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-3)',
    fontVariantNumeric: 'tabular-nums',
  },
  empty: {
    color: 'var(--text-3)',
    fontSize: '13px',
    fontStyle: 'italic',
  },
});

function formatUsd(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function formatTokens(value: number): string {
  if (value >= 10_000) return `${(value / 1000).toFixed(1)}k`;
  return value.toLocaleString();
}

export function CostCard({ usage }: { usage: MeetingUsage }) {
  const styles = useStyles();
  const agents = Object.values(usage.by_agent).sort((a, b) => b.cost_usd - a.cost_usd);
  const maxCost = agents.length > 0 ? agents[0].cost_usd : 0;

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <span className={styles.label}>LLM コスト</span>
        <span className={styles.totalCost}>{formatUsd(usage.total_cost_usd)}</span>
      </div>

      <div className={styles.metaGrid}>
        <div className={styles.metaCell}>
          <span className={styles.metaCellLabel}>Total tokens</span>
          <span className={styles.metaValue}>{formatTokens(usage.total_tokens)}</span>
        </div>
        <div className={styles.metaCell}>
          <span className={styles.metaCellLabel}>In / Out</span>
          <span className={styles.metaValue}>
            {formatTokens(usage.total_prompt_tokens)} / {formatTokens(usage.total_completion_tokens)}
          </span>
        </div>
        <div className={styles.metaCell}>
          <span className={styles.metaCellLabel}>呼び出し</span>
          <span className={styles.metaValue}>{usage.call_count}</span>
        </div>
      </div>

      {agents.length === 0 ? (
        <p className={styles.empty}>まだ LLM 呼び出しがありません。</p>
      ) : (
        <div className={styles.agentList}>
          {agents.map((agent) => {
            const pct = maxCost > 0 ? agent.cost_usd / maxCost : 0;
            return (
              <div key={agent.agent_name} className={styles.agentRow}>
                <div className={styles.agentRowHeader}>
                  <span className={styles.agentName}>{agent.agent_name}</span>
                  <span className={styles.agentMeta}>
                    {formatUsd(agent.cost_usd)} · {formatTokens(agent.total_tokens)} tok · ×{agent.call_count}
                  </span>
                </div>
                <ProgressBar value={pct} thickness="medium" />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
