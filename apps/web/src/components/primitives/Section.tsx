import { makeStyles, tokens } from '@fluentui/react-components';
import type { ReactNode } from 'react';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: '8px',
    backgroundColor: tokens.colorNeutralBackground2,
    overflow: 'hidden',
  },
  header: {
    padding: '12px 16px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
  },
  title: {
    fontSize: '13px',
    fontWeight: 500,
    color: tokens.colorNeutralForeground1,
    letterSpacing: '-0.005em',
    margin: 0,
  },
  body: {
    padding: '16px',
  },
  bodyFlush: {
    padding: '0',
  },
});

interface Props {
  title?: ReactNode;
  trailing?: ReactNode;
  flush?: boolean;
  children: ReactNode;
  /** When true, container has no padding (caller manages spacing). */
  bare?: boolean;
}

/**
 * Linear/Vercel 風のフラットなカード primitive。
 * gradient / shadow なし、border-subtle のみ。
 */
export function Section({ title, trailing, flush, bare, children }: Props) {
  const styles = useStyles();
  return (
    <section className={styles.root}>
      {title && (
        <header className={styles.header}>
          <h3 className={styles.title}>{title}</h3>
          {trailing}
        </header>
      )}
      <div className={bare ? styles.bodyFlush : flush ? styles.bodyFlush : styles.body}>
        {children}
      </div>
    </section>
  );
}
