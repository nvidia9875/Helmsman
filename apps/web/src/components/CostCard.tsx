import { Caption1, ProgressBar, makeStyles, tokens } from '@fluentui/react-components';

import type { MeetingUsage } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  label: {
    color: tokens.colorNeutralForeground2,
    fontSize: '12px',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  totalCost: {
    fontSize: '24px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    fontVariantNumeric: 'tabular-nums',
    letterSpacing: '-0.01em',
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
    paddingTop: '8px',
    paddingBottom: '12px',
    borderTop: `1px solid ${tokens.colorNeutralStroke2}`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  metaCell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  metaValue: {
    fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
    fontVariantNumeric: 'tabular-nums',
    fontSize: '13px',
    color: tokens.colorNeutralForeground1,
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
    color: tokens.colorNeutralForeground2,
  },
  empty: {
    color: tokens.colorNeutralForeground3,
    fontSize: '13px',
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
          <Caption1>Total tokens</Caption1>
          <span className={styles.metaValue}>{formatTokens(usage.total_tokens)}</span>
        </div>
        <div className={styles.metaCell}>
          <Caption1>In / Out</Caption1>
          <span className={styles.metaValue}>
            {formatTokens(usage.total_prompt_tokens)} / {formatTokens(usage.total_completion_tokens)}
          </span>
        </div>
        <div className={styles.metaCell}>
          <Caption1>呼び出し</Caption1>
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
                  <span>{agent.agent_name}</span>
                  <span style={{ fontVariantNumeric: 'tabular-nums' }}>
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
