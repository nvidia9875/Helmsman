import { makeStyles, mergeClasses, tokens } from '@fluentui/react-components';

const useStyles = makeStyles({
  dot: {
    display: 'inline-block',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  neutral: { backgroundColor: tokens.colorNeutralForeground3 },
  active: { backgroundColor: '#22c55e' },
  warning: { backgroundColor: '#f59e0b' },
  danger: { backgroundColor: '#ef4444' },
  brand: { backgroundColor: tokens.colorBrandBackground },
  pulse: {
    animationName: {
      '0%': { boxShadow: '0 0 0 0 rgba(34, 197, 94, 0.5)' },
      '70%': { boxShadow: '0 0 0 6px rgba(34, 197, 94, 0)' },
      '100%': { boxShadow: '0 0 0 0 rgba(34, 197, 94, 0)' },
    },
    animationDuration: '1.8s',
    animationIterationCount: 'infinite',
    animationTimingFunction: 'ease-out',
  },
});

export type StatusKind = 'neutral' | 'active' | 'warning' | 'danger' | 'brand';

interface Props {
  kind: StatusKind;
  pulse?: boolean;
}

export function StatusDot({ kind, pulse }: Props) {
  const styles = useStyles();
  return (
    <span
      className={mergeClasses(styles.dot, styles[kind], pulse && styles.pulse)}
      aria-hidden
    />
  );
}
