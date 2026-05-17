import {
  Badge,
  Body1,
  Caption1,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';

import type { InterventionDelivery, InterventionLevel, Meeting } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    backgroundColor: tokens.colorNeutralBackground1,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  feed: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    maxHeight: '380px',
    overflowY: 'auto',
  },
  card: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    gap: '12px',
    padding: '14px 16px',
    borderRadius: tokens.borderRadiusMedium,
    borderLeftWidth: '4px',
    borderLeftStyle: 'solid',
    backgroundColor: tokens.colorNeutralBackground3,
  },
  cardL1: { borderLeftColor: tokens.colorPaletteLightTealBorderActive },
  cardL2: { borderLeftColor: tokens.colorPaletteMarigoldBorderActive },
  cardL3: { borderLeftColor: tokens.colorPaletteRedBorderActive },
  levelBadge: {
    fontSize: '11px',
    letterSpacing: '0.04em',
    fontWeight: 700,
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.borderRadiusCircular,
    color: '#fff',
  },
  levelL1: { backgroundColor: tokens.colorPaletteLightTealBorderActive },
  levelL2: { backgroundColor: tokens.colorPaletteMarigoldBorderActive },
  levelL3: { backgroundColor: tokens.colorPaletteRedBorderActive },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: 0,
  },
  metaRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  content: {
    lineHeight: 1.5,
  },
  evidence: {
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
    fontSize: '12px',
    paddingLeft: '8px',
    borderLeftWidth: '2px',
    borderLeftStyle: 'solid',
    borderLeftColor: tokens.colorNeutralStroke2,
    marginTop: '4px',
  },
  empty: {
    color: tokens.colorNeutralForeground3,
    fontStyle: 'italic',
    padding: '16px',
    textAlign: 'center',
  },
});

const AGENT_EMOJI: Record<string, string> = {
  GoalDecomposer: '🎯',
  CoverageTracker: '📊',
  SteeringAgent: '🧭',
  DecisionCapture: '✅',
  QuietActivator: '🔔',
  DissentSurface: '🌊',
  TimeKeeper: '⏰',
  InterventionArbiter: '⚖️',
};

const LEVEL_LABEL: Record<InterventionLevel, string> = {
  L1: 'ささやき',
  L2: 'サイドバー',
  L3: '音声介入',
};

function levelClass(level: InterventionLevel, styles: ReturnType<typeof useStyles>): string {
  if (level === 'L3') return styles.cardL3;
  if (level === 'L2') return styles.cardL2;
  return styles.cardL1;
}

function levelBadgeClass(level: InterventionLevel, styles: ReturnType<typeof useStyles>): string {
  if (level === 'L3') return styles.levelL3;
  if (level === 'L2') return styles.levelL2;
  return styles.levelL1;
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function InterventionFeed({ meeting }: { meeting: Meeting }) {
  const styles = useStyles();
  // 新しい順
  const items: InterventionDelivery[] = [...meeting.delivered_interventions].reverse();

  return (
    <section className={styles.root} aria-label="介入フィード">
      <div className={styles.header}>
        <Title3 as="h2" style={{ margin: 0 }}>
          🪧 介入フィード
        </Title3>
        <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
          直近 {meeting.delivered_interventions.length} 件
        </Caption1>
      </div>

      <div className={styles.feed}>
        {items.length === 0 ? (
          <Body1 className={styles.empty}>
            まだ介入はありません。会議が進むと AI 提案がここに流れます。
          </Body1>
        ) : (
          items.map((d) => (
            <article key={d.id} className={`${styles.card} ${levelClass(d.level, styles)}`}>
              <div className={`${styles.levelBadge} ${levelBadgeClass(d.level, styles)}`}>
                {d.level}
              </div>
              <div className={styles.body}>
                <div className={styles.metaRow}>
                  <strong>
                    {AGENT_EMOJI[d.agent] ?? '🤖'} {d.agent}
                  </strong>
                  <Badge appearance="tint" size="small">
                    {LEVEL_LABEL[d.level]}
                  </Badge>
                  <Caption1 style={{ marginLeft: 'auto', color: tokens.colorNeutralForeground3 }}>
                    {fmtTime(d.delivered_at)}
                  </Caption1>
                </div>
                <Body1 className={styles.content}>{d.content}</Body1>
                {d.evidence_quote && (
                  <Body1 className={styles.evidence}>「{d.evidence_quote}」</Body1>
                )}
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
