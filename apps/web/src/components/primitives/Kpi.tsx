import { makeStyles, tokens } from '@fluentui/react-components';
import type { ReactNode } from 'react';

const useStyles = makeStyles({
  row: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '12px',
    width: '100%',
  },
  card: {
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: '8px',
    backgroundColor: tokens.colorNeutralBackground2,
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: 0,
  },
  label: {
    fontSize: '11px',
    fontWeight: 500,
    color: tokens.colorNeutralForeground3,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  value: {
    fontSize: '24px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    fontVariantNumeric: 'tabular-nums',
    letterSpacing: '-0.01em',
    lineHeight: 1.2,
  },
  hint: {
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
  },
});

interface KpiProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
}

export function Kpi({ label, value, hint }: KpiProps) {
  const styles = useStyles();
  return (
    <div className={styles.card}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{value}</span>
      {hint && <span className={styles.hint}>{hint}</span>}
    </div>
  );
}

export function KpiRow({ children }: { children: ReactNode }) {
  const styles = useStyles();
  return <div className={styles.row}>{children}</div>;
}
