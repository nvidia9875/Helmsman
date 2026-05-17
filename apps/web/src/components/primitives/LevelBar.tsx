import { makeStyles, mergeClasses } from '@fluentui/react-components';

import type { InterventionLevel } from '@/lib/api';

const useStyles = makeStyles({
  bar: {
    width: '3px',
    flexShrink: 0,
    borderRadius: '2px',
    alignSelf: 'stretch',
  },
  L1: { backgroundColor: 'rgba(59, 130, 246, 0.4)' },
  L2: { backgroundColor: 'rgba(59, 130, 246, 0.7)' },
  L3: { backgroundColor: 'rgba(59, 130, 246, 1)' },
});

/** 介入レベル (L1/L2/L3) をブランド色の luminosity ladder で表現する細い縦バー。 */
export function LevelBar({ level }: { level: InterventionLevel }) {
  const styles = useStyles();
  return <span className={mergeClasses(styles.bar, styles[level])} aria-label={level} />;
}
