/**
 * OnboardingSteps — 派遣前のヒーロー。
 *
 * 初めての人が「次に何をすればいいか」一目で分かるよう、
 * 縦並びの 3 ステップ + 大きな番号 + breathing アニメで強調する。
 */
import { makeStyles } from '@fluentui/react-components';
import { ArrowDown20Regular } from '@fluentui/react-icons';

const useStyles = makeStyles({
  root: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    padding: '24px 28px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '14px',
    backgroundColor: 'var(--bg-1)',
    backdropFilter: 'blur(12px) saturate(140%)',
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: '12px',
    paddingBottom: '4px',
  },
  eyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: 'var(--accent-cyan)',
    fontFamily: 'var(--font-mono)',
  },
  title: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
  },
  hint: {
    fontSize: '12px',
    color: 'var(--text-3)',
    margin: 0,
  },
  stepsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginTop: '4px',
  },
  step: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '14px',
  },
  num: {
    width: '28px',
    height: '28px',
    minWidth: '28px',
    borderRadius: '50%',
    border: '1px solid var(--accent)',
    backgroundColor: 'var(--accent-soft)',
    color: 'var(--accent)',
    fontSize: '13px',
    fontWeight: 700,
    fontFamily: 'var(--font-mono)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    flex: 1,
  },
  stepTitle: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-1)',
  },
  stepDesc: {
    fontSize: '12px',
    color: 'var(--text-3)',
  },
  pointer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    paddingTop: '8px',
    color: 'var(--accent-cyan)',
    fontSize: '12px',
    fontWeight: 500,
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
});

const STEPS = [
  {
    title: 'Teams カレンダーで会議を作る',
    desc: '「新しい会議」→ 開始時刻は今、終了は適当で OK',
  },
  {
    title: '参加 URL をコピーして下に貼る',
    desc: '「会議のリンクをコピー」or イベント詳細から',
  },
  {
    title: '🚀 派遣ボタンで Helmsman を会議に送り出す',
    desc: 'admin@helmsmanjp で会議に居続けてください',
  },
];

export function OnboardingSteps() {
  const styles = useStyles();
  return (
    <section className={styles.root} aria-label="Helmsman を使うための 3 ステップ">
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>STEPS · GETTING STARTED</div>
          <h3 className={styles.title}>初めての場合は下の 3 ステップで会議に Helmsman を派遣できます</h3>
        </div>
        <p className={styles.hint}>慣れている場合はそのまま下の URL 欄に貼ってください</p>
      </header>

      <ol className={styles.stepsList} style={{ margin: 0, paddingLeft: 0, listStyle: 'none' }}>
        {STEPS.map((step, i) => (
          <li key={step.title} className={styles.step}>
            <span className={styles.num}>{i + 1}</span>
            <div className={styles.stepBody}>
              <span className={styles.stepTitle}>{step.title}</span>
              <span className={styles.stepDesc}>{step.desc}</span>
            </div>
          </li>
        ))}
      </ol>

      <div className={`${styles.pointer} breathing`} aria-hidden>
        <ArrowDown20Regular />
        <span>派遣フォームへ</span>
        <ArrowDown20Regular />
      </div>

      <p
        style={{
          fontSize: 11,
          color: 'var(--text-4)',
          margin: 0,
          paddingTop: 8,
          borderTop: '1px dashed var(--border-hairline)',
          lineHeight: 1.55,
        }}
      >
        💡 オプション: Solo モードで「📷 顔シグナル」を ON にすると、うなずき / 困惑 /
        集中度を AI が読み取ってくれます。動画はサーバーに送りません。
      </p>
    </section>
  );
}
