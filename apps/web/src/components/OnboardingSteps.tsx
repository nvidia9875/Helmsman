import { makeStyles } from '@fluentui/react-components';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap',
    padding: '12px 16px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    alignItems: 'center',
  },
  eyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    paddingRight: '12px',
    borderRight: '1px solid var(--border-hairline)',
    marginRight: '4px',
  },
  step: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: 'var(--text-2)',
  },
  num: {
    width: '18px',
    height: '18px',
    minWidth: '18px',
    borderRadius: '999px',
    backgroundColor: 'var(--accent)',
    color: '#fff',
    fontSize: '10px',
    fontWeight: 700,
    fontFamily: 'var(--font-mono)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  arrow: {
    color: 'var(--text-4)',
    fontFamily: 'var(--font-mono)',
  },
});

const STEPS = ['Teams で会議を作る', '参加 URL をコピー', '下に貼り付け', '会議で話す'];

export function OnboardingSteps() {
  const styles = useStyles();
  return (
    <div className={styles.root} aria-label="使い方 4 ステップ">
      <span className={styles.eyebrow}>HOW IT WORKS</span>
      {STEPS.map((label, i) => (
        <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          {i > 0 && <span className={styles.arrow}>→</span>}
          <span className={styles.step}>
            <span className={styles.num}>{i + 1}</span>
            {label}
          </span>
        </span>
      ))}
    </div>
  );
}
