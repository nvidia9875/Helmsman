import { makeStyles } from '@fluentui/react-components';

const useStyles = makeStyles({
  block: {
    backgroundColor: 'var(--bg-2)',
    borderRadius: '6px',
    animationName: {
      '0%, 100%': { opacity: 0.6 },
      '50%': { opacity: 0.3 },
    },
    animationDuration: '1.4s',
    animationIterationCount: 'infinite',
    animationTimingFunction: 'ease-in-out',
  },
});

interface Props {
  width?: string | number;
  height?: string | number;
  radius?: string | number;
}

export function Skeleton({ width = '100%', height = '14px', radius = 6 }: Props) {
  const styles = useStyles();
  return (
    <div
      className={styles.block}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        borderRadius: typeof radius === 'number' ? `${radius}px` : radius,
      }}
      aria-hidden
    />
  );
}
