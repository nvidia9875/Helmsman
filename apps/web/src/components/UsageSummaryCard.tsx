import {
  Body1,
  Caption1,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    width: '100%',
    maxWidth: '720px',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
  },
  metaCell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  metaValue: {
    fontSize: '20px',
    fontWeight: 600,
    fontVariantNumeric: 'tabular-nums',
    color: tokens.colorBrandForeground1,
  },
  trendRow: {
    display: 'flex',
    gap: '4px',
    alignItems: 'flex-end',
    height: '36px',
    marginTop: '4px',
  },
  trendBar: {
    flex: 1,
    backgroundColor: tokens.colorBrandBackground,
    borderRadius: '2px',
    minHeight: '2px',
  },
  empty: {
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
  },
});

function fmtUsd(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function fmtTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return value.toLocaleString();
}

export function UsageSummaryCard({ organizerId }: { organizerId: string }) {
  const styles = useStyles();
  const { data, isLoading } = useQuery({
    queryKey: ['usage-summary', organizerId],
    queryFn: () => api.getUsageSummary(organizerId, 30),
    staleTime: 60_000,
  });

  if (isLoading || !data) {
    return null;
  }

  if (data.total_meetings === 0) {
    return null;
  }

  const maxBar = Math.max(0.0001, ...data.by_day.map((d) => d.cost_usd));

  return (
    <section className={styles.root} aria-label="LLM 利用サマリー">
      <Title3 as="h2" style={{ margin: 0 }}>
        💰 LLM 利用サマリー (直近 30 日)
      </Title3>

      <div className={styles.metaGrid}>
        <div className={styles.metaCell}>
          <Caption1>累計コスト</Caption1>
          <span className={styles.metaValue}>{fmtUsd(data.total_cost_usd)}</span>
        </div>
        <div className={styles.metaCell}>
          <Caption1>会議数</Caption1>
          <span className={styles.metaValue}>{data.total_meetings}</span>
        </div>
        <div className={styles.metaCell}>
          <Caption1>1 会議あたり平均</Caption1>
          <span className={styles.metaValue}>{fmtUsd(data.avg_cost_per_meeting_usd)}</span>
        </div>
      </div>

      <div>
        <Caption1>日別コスト推移</Caption1>
        <div className={styles.trendRow}>
          {data.by_day.length === 0 ? (
            <Body1 className={styles.empty}>会議がまだありません</Body1>
          ) : (
            data.by_day.map((d) => (
              <div
                key={d.date}
                className={styles.trendBar}
                style={{ height: `${(d.cost_usd / maxBar) * 36}px` }}
                title={`${d.date}: ${fmtUsd(d.cost_usd)} (${d.meeting_count} 会議, ${fmtTokens(d.total_tokens)} tok)`}
              />
            ))
          )}
        </div>
      </div>

      <Caption1>
        累計 {fmtTokens(data.total_tokens)} tokens / {Object.keys(data.by_agent).length} agents 経由
      </Caption1>
    </section>
  );
}
