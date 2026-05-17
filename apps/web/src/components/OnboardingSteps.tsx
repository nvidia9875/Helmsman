import { Body1, Caption1, makeStyles, tokens } from '@fluentui/react-components';

const useStyles = makeStyles({
  root: {
    border: `1px dashed ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  steps: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '10px',
  },
  step: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-start',
    padding: '10px 12px',
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground3,
  },
  num: {
    width: '24px',
    height: '24px',
    minWidth: '24px',
    borderRadius: tokens.borderRadiusCircular,
    backgroundColor: tokens.colorBrandBackground,
    color: '#fff',
    fontSize: '12px',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    minWidth: 0,
  },
  title: {
    fontWeight: 600,
    fontSize: '13px',
    lineHeight: 1.3,
  },
  hint: {
    color: tokens.colorNeutralForeground3,
    fontSize: '11px',
    lineHeight: 1.4,
  },
});

const STEPS = [
  {
    title: 'Teams で会議を作る',
    hint: 'Teams カレンダーから新規会議。Helmsman ではなく Teams 側で作成します。',
  },
  {
    title: '参加リンクをコピー',
    hint: '会議を開いて「リンクをコピー」または招待メールから URL を取得。',
  },
  {
    title: '下のフォームに貼り付け',
    hint: '"🤖 Bot を招待" を押すと Helmsman が外部参加者として join します。',
  },
  {
    title: '会議で普通に話す',
    hint: '発言は自動的に文字起こしされ、論点 / 介入 / コストがこの画面に流れます。',
  },
];

export function OnboardingSteps() {
  const styles = useStyles();
  return (
    <section className={styles.root} aria-label="使い方 4 ステップ">
      <Body1 style={{ fontWeight: 600 }}>はじめに — 4 ステップで会議を開始</Body1>
      <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
        Bot は Teams 会議に <strong>「Helmsman 🧭 (External)」</strong> として参加します。
        参加者は普段通り Teams で話すだけ。
      </Caption1>
      <div className={styles.steps}>
        {STEPS.map((s, i) => (
          <div key={s.title} className={styles.step}>
            <span className={styles.num}>{i + 1}</span>
            <div className={styles.body}>
              <span className={styles.title}>{s.title}</span>
              <span className={styles.hint}>{s.hint}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
