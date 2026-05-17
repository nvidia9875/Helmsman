import {
  Body1,
  Caption1,
  ProgressBar,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';

import type { MeetingUsage } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '16px',
    marginTop: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: '12px',
    flexWrap: 'wrap',
  },
  totalCost: {
    fontSize: '28px',
    fontWeight: 600,
    color: tokens.colorBrandForeground1,
    fontVariantNumeric: 'tabular-nums',
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '8px',
    paddingBottom: '8px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  metaCell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  metaValue: {
    fontFamily: tokens.fontFamilyMonospace,
    fontVariantNumeric: 'tabular-nums',
    fontSize: '14px',
  },
  agentList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  agentRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    gap: '6px',
    alignItems: 'baseline',
  },
  agentRowHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '8px',
    fontSize: '12px',
  },
  empty: {
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
  },
});

const AGENT_LABEL: Record<string, string> = {
  GoalDecomposer: '🎯 GoalDecomposer',
  CoverageTracker: '📊 CoverageTracker',
  SteeringAgent: '🧭 SteeringAgent',
  DecisionCapture: '✅ DecisionCapture',
  QuietActivator: '🔔 QuietActivator',
  DissentSurface: '🌊 DissentSurface',
};

function formatUsd(value: number): string {
  if (value < 0.01) {
    return `$${value.toFixed(4)}`;
  }
  return `$${value.toFixed(2)}`;
}

function formatTokens(value: number): string {
  if (value >= 10_000) {
    return `${(value / 1000).toFixed(1)}k`;
  }
  return value.toLocaleString();
}

export function CostCard({ usage }: { usage: MeetingUsage }) {
  const styles = useStyles();
  const agents = Object.values(usage.by_agent).sort(
    (a, b) => b.cost_usd - a.cost_usd,
  );
  const maxCost = agents.length > 0 ? agents[0].cost_usd : 0;

  return (
    <section className={styles.root} aria-label="LLM コスト集計">
      <div className={styles.headerRow}>
        <Title3 as="h2" style={{ margin: 0 }}>
          💰 LLM コスト
        </Title3>
        <span className={styles.totalCost}>{formatUsd(usage.total_cost_usd)}</span>
      </div>

      <div className={styles.metaGrid}>
        <div className={styles.metaCell}>
          <Caption1>Total tokens</Caption1>
          <span className={styles.metaValue}>{formatTokens(usage.total_tokens)}</span>
        </div>
        <div className={styles.metaCell}>
          <Caption1>Input / Output</Caption1>
          <span className={styles.metaValue}>
            {formatTokens(usage.total_prompt_tokens)} / {formatTokens(usage.total_completion_tokens)}
          </span>
        </div>
        <div className={styles.metaCell}>
          <Caption1>呼び出し回数</Caption1>
          <span className={styles.metaValue}>{usage.call_count}</span>
        </div>
      </div>

      {agents.length === 0 ? (
        <Body1 className={styles.empty}>
          まだ LLM 呼び出しがありません。会議を開始すると集計が始まります。
        </Body1>
      ) : (
        <div className={styles.agentList}>
          {agents.map((agent) => {
            const pct = maxCost > 0 ? agent.cost_usd / maxCost : 0;
            return (
              <div key={agent.agent_name} className={styles.agentRow}>
                <div>
                  <div className={styles.agentRowHeader}>
                    <span>
                      {AGENT_LABEL[agent.agent_name] ?? agent.agent_name}{' '}
                      <Caption1 as="span">({agent.model_deployment})</Caption1>
                    </span>
                    <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                      {formatUsd(agent.cost_usd)} ・ {formatTokens(agent.total_tokens)} tok ・ ×{agent.call_count}
                    </span>
                  </div>
                  <ProgressBar value={pct} thickness="medium" />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
