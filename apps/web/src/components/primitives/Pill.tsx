import { makeStyles, mergeClasses, tokens } from '@fluentui/react-components';
import type { ReactNode } from 'react';

const useStyles = makeStyles({
  pill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    borderRadius: '999px',
    fontSize: '12px',
    fontWeight: 500,
    lineHeight: 1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground2,
    color: tokens.colorNeutralForeground2,
    whiteSpace: 'nowrap',
  },
  brand: {
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    border: '1px solid rgba(59, 130, 246, 0.3)',
    color: '#93c5fd',
  },
  success: {
    backgroundColor: 'rgba(34, 197, 94, 0.1)',
    border: '1px solid rgba(34, 197, 94, 0.3)',
    color: '#86efac',
  },
  warning: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    border: '1px solid rgba(245, 158, 11, 0.3)',
    color: '#fbbf24',
  },
  danger: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
  },
});

export type PillKind = 'neutral' | 'brand' | 'success' | 'warning' | 'danger';

interface Props {
  kind?: PillKind;
  children: ReactNode;
}

export function Pill({ kind = 'neutral', children }: Props) {
  const styles = useStyles();
  return (
    <span
      className={mergeClasses(styles.pill, kind !== 'neutral' && styles[kind])}
    >
      {children}
    </span>
  );
}
