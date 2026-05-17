import { makeStyles, tokens } from '@fluentui/react-components';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    padding: '10px 12px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: '8px',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  step: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: tokens.colorNeutralForeground2,
  },
  num: {
    width: '18px',
    height: '18px',
    minWidth: '18px',
    borderRadius: '999px',
    backgroundColor: tokens.colorBrandBackground,
    color: '#fff',
    fontSize: '10px',
    fontWeight: 600,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  arrow: {
    color: tokens.colorNeutralForeground4,
  },
});

const STEPS = ['Teams で会議を作る', '参加 URL をコピー', '下に貼り付け', '会議で話す'];

export function OnboardingSteps() {
  const styles = useStyles();
  return (
    <div className={styles.root} aria-label="使い方 4 ステップ">
      {STEPS.map((label, i) => (
        <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
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
