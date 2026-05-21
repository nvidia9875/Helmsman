import { Button, makeStyles, mergeClasses } from '@fluentui/react-components';
import {
  ArrowRight24Regular,
  Code24Regular,
  CompassNorthwestRegular,
  Mic24Regular,
  Rocket24Regular,
  Sparkle24Regular,
} from '@fluentui/react-icons';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { CountUp } from '@/components/primitives/CountUp';
import { useInView } from '@/hooks/useInView';

const useStyles = makeStyles({
  page: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: 'calc(100vh - 52px)',
    overflow: 'hidden',
  },

  // ============ HERO ============
  hero: {
    position: 'relative',
    minHeight: 'min(720px, 85vh)',
    padding: '64px 32px 56px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    borderBottom: '1px solid var(--border-hairline)',
    overflow: 'hidden',
  },
  // 背景: 3 つの放射 orb と ambient drift。global.css の body::after と重ねる
  heroOrbA: {
    position: 'absolute',
    top: '-12%',
    left: '50%',
    width: '900px',
    height: '900px',
    pointerEvents: 'none',
    transform: 'translateX(-50%)',
    background:
      'radial-gradient(circle, rgba(91, 141, 239, 0.18) 0%, rgba(91, 141, 239, 0) 55%)',
    filter: 'blur(40px)',
    zIndex: 0,
  },
  heroOrbB: {
    position: 'absolute',
    bottom: '-20%',
    right: '5%',
    width: '500px',
    height: '500px',
    pointerEvents: 'none',
    background:
      'radial-gradient(circle, rgba(176, 124, 255, 0.13) 0%, rgba(176, 124, 255, 0) 60%)',
    filter: 'blur(40px)',
    zIndex: 0,
  },
  heroOrbC: {
    position: 'absolute',
    top: '20%',
    left: '5%',
    width: '420px',
    height: '420px',
    pointerEvents: 'none',
    background:
      'radial-gradient(circle, rgba(92, 240, 245, 0.10) 0%, rgba(92, 240, 245, 0) 60%)',
    filter: 'blur(36px)',
    zIndex: 0,
  },
  // 細かい星座 (constellation) — 8 つの agent を表す pulsing dots
  constellation: {
    position: 'absolute',
    inset: 0,
    pointerEvents: 'none',
    zIndex: 0,
  },
  star: {
    position: 'absolute',
    width: '4px',
    height: '4px',
    borderRadius: '999px',
    backgroundColor: 'var(--accent-cyan)',
    boxShadow: '0 0 12px rgba(92, 240, 245, 0.7)',
    opacity: 0.4,
    animationName: {
      '0%, 100%': { opacity: 0.25, transform: 'scale(1)' },
      '50%': { opacity: 0.9, transform: 'scale(1.4)' },
    },
    animationDuration: '4s',
    animationIterationCount: 'infinite',
    animationTimingFunction: 'ease-in-out',
    '@media (prefers-reduced-motion: reduce)': {
      animationName: 'none',
      opacity: 0.4,
    },
  },

  // ヒーロー中身
  heroInner: {
    position: 'relative',
    zIndex: 1,
    maxWidth: '960px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '20px',
  },
  eyebrow: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
    color: 'var(--accent-cyan)',
    fontFamily: 'var(--font-mono)',
    padding: '6px 14px',
    borderRadius: '999px',
    backgroundColor: 'rgba(92, 240, 245, 0.07)',
    border: '1px solid rgba(92, 240, 245, 0.22)',
  },
  eyebrowDot: {
    width: '6px',
    height: '6px',
    borderRadius: '999px',
    backgroundColor: 'var(--accent-cyan)',
    boxShadow: '0 0 8px rgba(92, 240, 245, 0.9)',
    animationName: {
      '0%, 100%': { opacity: 0.5 },
      '50%': { opacity: 1 },
    },
    animationDuration: '1.6s',
    animationIterationCount: 'infinite',
  },
  headline: {
    margin: 0,
    fontSize: 'clamp(36px, 6.2vw, 76px)',
    lineHeight: 1.02,
    letterSpacing: '-0.032em',
    fontWeight: 600,
    color: 'var(--text-1)',
  },
  // gradient で強調する単語
  headlineAccent: {
    background:
      'linear-gradient(120deg, var(--accent-cyan) 0%, var(--accent) 45%, var(--accent-violet) 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    color: 'transparent',
  },
  subhead: {
    color: 'var(--text-2)',
    fontSize: 'clamp(15px, 1.4vw, 18px)',
    lineHeight: 1.6,
    maxWidth: '640px',
    margin: 0,
  },
  ctaRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: '12px',
  },
  ctaPrimary: {
    minWidth: '200px',
  },
  ctaSecondary: {
    color: 'var(--text-2)',
    border: '1px solid var(--border-default)',
    backgroundColor: 'transparent',
    padding: '0 22px',
    height: '40px',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    transitionProperty: 'background-color, color, border-color',
    transitionDuration: '160ms',
    ':hover': {
      color: 'var(--text-1)',
      backgroundColor: 'var(--bg-1)',
      border: '1px solid var(--border-default)',
    },
  },
  // hero KPI ticker
  ticker: {
    marginTop: '36px',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '24px',
    padding: '12px 22px',
    borderRadius: '999px',
    border: '1px solid var(--border-hairline)',
    backgroundColor: 'rgba(13, 13, 16, 0.55)',
    backdropFilter: 'blur(8px)',
    WebkitBackdropFilter: 'blur(8px)',
    flexWrap: 'wrap',
    justifyContent: 'center',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-2)',
    letterSpacing: '0.02em',
  },
  tickerItem: {
    display: 'inline-flex',
    alignItems: 'baseline',
    gap: '8px',
  },
  tickerValue: {
    color: 'var(--text-1)',
    fontSize: '14px',
    fontWeight: 700,
    fontVariantNumeric: 'tabular-nums',
  },
  tickerLabel: {
    color: 'var(--text-3)',
    fontSize: '10px',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
  },
  tickerSep: {
    width: '1px',
    height: '18px',
    backgroundColor: 'var(--border-hairline)',
  },
  scrollHint: {
    position: 'absolute',
    bottom: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    color: 'var(--text-4)',
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    zIndex: 1,
    animationName: {
      '0%, 100%': { transform: 'translateX(-50%) translateY(0)' },
      '50%': { transform: 'translateX(-50%) translateY(4px)' },
    },
    animationDuration: '2.8s',
    animationIterationCount: 'infinite',
    animationTimingFunction: 'ease-in-out',
  },

  // ============ SECTIONS COMMON ============
  section: {
    padding: '96px 32px',
    borderBottom: '1px solid var(--border-hairline)',
    position: 'relative',
  },
  sectionInner: {
    maxWidth: '1180px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '40px',
  },
  sectionHeader: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    maxWidth: '720px',
  },
  sectionEyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    color: 'var(--accent)',
    fontFamily: 'var(--font-mono)',
  },
  sectionTitle: {
    margin: 0,
    fontSize: 'clamp(26px, 3vw, 40px)',
    lineHeight: 1.12,
    letterSpacing: '-0.022em',
    fontWeight: 600,
    color: 'var(--text-1)',
  },
  sectionLede: {
    color: 'var(--text-2)',
    fontSize: '15px',
    lineHeight: 1.6,
    maxWidth: '620px',
  },

  // ============ PILLARS (3-bento) ============
  pillarsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px',
    '@media (max-width: 920px)': {
      gridTemplateColumns: '1fr',
    },
  },
  pillar: {
    position: 'relative',
    padding: '32px 28px',
    borderRadius: '14px',
    border: '1px solid var(--border-hairline)',
    background: 'linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%)',
    overflow: 'hidden',
    transitionProperty: 'transform, border-color, box-shadow',
    transitionDuration: '320ms',
    transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
    ':hover': {
      transform: 'translateY(-4px)',
      border: '1px solid rgba(91, 141, 239, 0.4)',
      boxShadow: '0 20px 60px -20px rgba(91, 141, 239, 0.35)',
    },
  },
  pillarA: {
    '::before': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      height: '2px',
      background:
        'linear-gradient(90deg, var(--accent), var(--accent-cyan))',
    },
  },
  pillarB: {
    '::before': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      height: '2px',
      background:
        'linear-gradient(90deg, var(--accent-cyan), var(--accent-violet))',
    },
  },
  pillarC: {
    '::before': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      height: '2px',
      background:
        'linear-gradient(90deg, var(--accent-violet), var(--accent))',
    },
  },
  pillarIcon: {
    width: '44px',
    height: '44px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(91, 141, 239, 0.10)',
    color: 'var(--accent)',
    marginBottom: '18px',
  },
  pillarKpi: {
    fontSize: 'clamp(38px, 4.6vw, 56px)',
    fontWeight: 700,
    lineHeight: 1,
    letterSpacing: '-0.03em',
    color: 'var(--text-1)',
    fontFamily: 'var(--font-mono)',
    fontVariantNumeric: 'tabular-nums',
  },
  pillarKpiUnit: {
    fontSize: '0.42em',
    color: 'var(--text-3)',
    marginLeft: '6px',
    fontWeight: 500,
  },
  pillarTitle: {
    margin: '14px 0 6px',
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-1)',
    letterSpacing: '-0.01em',
  },
  pillarBody: {
    fontSize: '13px',
    color: 'var(--text-2)',
    lineHeight: 1.6,
    margin: 0,
  },

  // ============ HOW IT WORKS ============
  steps: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '8px',
    '@media (max-width: 920px)': {
      gridTemplateColumns: '1fr',
    },
  },
  step: {
    position: 'relative',
    padding: '28px 24px',
    borderRadius: '12px',
    border: '1px solid var(--border-hairline)',
    backgroundColor: 'var(--bg-1)',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  stepIndex: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--accent-cyan)',
    letterSpacing: '0.16em',
  },
  stepTitle: {
    margin: 0,
    fontSize: '17px',
    fontWeight: 600,
    color: 'var(--text-1)',
    lineHeight: 1.3,
  },
  stepBody: {
    color: 'var(--text-2)',
    fontSize: '13px',
    lineHeight: 1.6,
    margin: 0,
  },

  // ============ FINAL CTA BAND ============
  ctaBand: {
    position: 'relative',
    padding: '88px 32px',
    overflow: 'hidden',
    background:
      'radial-gradient(ellipse 80% 100% at 50% 0%, rgba(91, 141, 239, 0.15), transparent 65%), var(--bg-0)',
    borderBottom: '1px solid var(--border-hairline)',
  },
  ctaBandInner: {
    maxWidth: '720px',
    margin: '0 auto',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
    alignItems: 'center',
    position: 'relative',
    zIndex: 1,
  },
  ctaBandTitle: {
    margin: 0,
    fontSize: 'clamp(28px, 3.6vw, 44px)',
    fontWeight: 600,
    color: 'var(--text-1)',
    letterSpacing: '-0.025em',
    lineHeight: 1.15,
  },
  ctaBandHint: {
    color: 'var(--text-3)',
    fontSize: '13px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
  },

  // ============ Reveal animation (driven by useInView) ============
  reveal: {
    opacity: 0,
    transform: 'translateY(16px)',
    transitionProperty: 'opacity, transform',
    transitionDuration: '600ms',
    transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
  revealOn: {
    opacity: 1,
    transform: 'translateY(0)',
  },
});

const PILLARS = [
  {
    kpi: 8,
    unit: 'agents',
    title: '8 並列エージェント',
    body: 'Coverage / Steering / Decision / Quiet / Dissent / TimeKeeper / Goal / Arbiter が同時に会議を観測。役割を細かく分割しているから 1 個壊れても残りで補える。',
    icon: <Sparkle24Regular />,
    klass: 'pillarA' as const,
  },
  {
    kpi: 0.03,
    unit: '$ / 会議',
    title: '会議 1 本 3 円',
    body: 'cheap mode で 25 分会議の LLM コストは ¥3.0。決定 1 件あたり ¥0.30 と既存議事録 SaaS より 1 桁安い。1 円単位のコスト透明性を Dashboard で確認可能。',
    icon: <Code24Regular />,
    klass: 'pillarB' as const,
  },
  {
    kpi: 3,
    unit: '段グラデ介入',
    title: 'L1 / L2 / L3',
    body: '優先度に応じて、ささやき / サイドバーカード / 音声発話 の 3 段で介入。Density-aware + Authority Gradient で「いつ・誰に」を制御し、会議の空気を壊さない。',
    icon: <Mic24Regular />,
    klass: 'pillarC' as const,
  },
];

const STEPS = [
  {
    index: '01',
    title: 'Teams 会議の URL を貼る',
    body: 'いつも通り Teams カレンダーで会議を作り、参加 URL をコピーして Helmsman の Dispatch 画面に貼る。',
  },
  {
    index: '02',
    title: 'Helmsman 🧭 が会議に参加',
    body: '外部参加者として join → Azure Speech で文字起こし → 8 agent が並列に観測。L1/L2/L3 介入を chair の Dashboard に流す。',
  },
  {
    index: '03',
    title: '構造化された決定 + レポート',
    body: '会議終了で 10 件規模の `evidence_quote` 付き決定を取得。自社テンプレ + 手書きメモを貼ればそのまま markdown レポートが完成。',
  },
];

// 星座: hero に散らばせる pulsing dots の位置と animation-delay
const STARS: { top: string; left: string; delay: string }[] = [
  { top: '18%', left: '12%', delay: '0s' },
  { top: '32%', left: '88%', delay: '0.6s' },
  { top: '56%', left: '8%', delay: '1.2s' },
  { top: '70%', left: '24%', delay: '1.8s' },
  { top: '24%', left: '62%', delay: '2.4s' },
  { top: '78%', left: '78%', delay: '3.0s' },
  { top: '46%', left: '92%', delay: '3.6s' },
  { top: '62%', left: '52%', delay: '4.2s' },
];

function RevealSection({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const styles = useStyles();
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.12 });
  return (
    <div
      ref={ref}
      className={mergeClasses(
        styles.reveal,
        inView && styles.revealOn,
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Landing() {
  const styles = useStyles();
  const navigate = useNavigate();

  // hero KPI: 軽い演出のため数値を遅延注入 (count up を意味あるように発火させる)
  const [ticking, setTicking] = useState(false);
  useEffect(() => {
    const id = window.setTimeout(() => setTicking(true), 220);
    return () => window.clearTimeout(id);
  }, []);

  return (
    <div className={styles.page}>
      {/* ============ HERO ============ */}
      <section className={styles.hero} aria-labelledby="hero-headline">
        <div className={styles.heroOrbA} aria-hidden />
        <div className={styles.heroOrbB} aria-hidden />
        <div className={styles.heroOrbC} aria-hidden />
        <div className={styles.constellation} aria-hidden>
          {STARS.map((s, i) => (
            <span
              key={i}
              className={styles.star}
              style={{
                top: s.top,
                left: s.left,
                animationDelay: s.delay,
              }}
            />
          ))}
        </div>

        <div className={`${styles.heroInner} stagger`}>
          <span className={styles.eyebrow}>
            <span className={styles.eyebrowDot} aria-hidden />
            AI MEETING CO-PILOT · MICROSOFT AGENT HACKATHON 2026
          </span>

          <h1 id="hero-headline" className={styles.headline}>
            Teams 会議に、
            <br />
            <span className={styles.headlineAccent}>AI を 1 人</span>
            派遣する。
          </h1>

          <p className={styles.subhead}>
            会議の流れを観測し、決定を構造化し、沈黙を活性化し、
            <br />
            必要なら音声で会議に介入する <strong>8 並列 AI agent</strong> システム。
          </p>

          <div className={styles.ctaRow}>
            <Button
              appearance="primary"
              size="large"
              icon={<Rocket24Regular />}
              className={styles.ctaPrimary}
              onClick={() => navigate('/new')}
            >
              Bot を派遣する
            </Button>
            <a
              href="https://github.com/nvidia9875/Helmsman"
              target="_blank"
              rel="noreferrer"
              className={styles.ctaSecondary}
            >
              <Code24Regular />
              GitHub で見る
            </a>
          </div>

          <div className={styles.ticker} aria-label="ライブ KPI">
            <span className={styles.tickerItem}>
              <span className={styles.tickerLabel}>per meeting</span>
              <span className={styles.tickerValue}>
                $
                <CountUp
                  value={ticking ? 0.03 : 0}
                  fmt={(v) => v.toFixed(2)}
                />
              </span>
            </span>
            <span className={styles.tickerSep} />
            <span className={styles.tickerItem}>
              <span className={styles.tickerLabel}>decisions</span>
              <span className={styles.tickerValue}>
                <CountUp value={ticking ? 10 : 0} />
              </span>
            </span>
            <span className={styles.tickerSep} />
            <span className={styles.tickerItem}>
              <span className={styles.tickerLabel}>topics decided</span>
              <span className={styles.tickerValue}>
                <CountUp value={ticking ? 5 : 0} />
                <span style={{ color: 'var(--text-3)', fontWeight: 400 }}>
                  /5
                </span>
              </span>
            </span>
          </div>
        </div>

        <span className={styles.scrollHint} aria-hidden>
          ↓ scroll
        </span>
      </section>

      {/* ============ PILLARS ============ */}
      <section
        className={styles.section}
        aria-labelledby="pillars-title"
      >
        <div className={styles.sectionInner}>
          <RevealSection>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionEyebrow}>WHY HELMSMAN</span>
              <h2 id="pillars-title" className={styles.sectionTitle}>
                議事録の次は、
                <br />
                <span className={styles.headlineAccent}>
                  会議そのものを成功させる AI
                </span>
                。
              </h2>
              <p className={styles.sectionLede}>
                Otter / Granola / Fathom は事後要約を完成させた。Helmsman は
                <strong> 会議の最中に手を入れる</strong> 領域に踏み込む。
                介入研究 (CHI 2025 OAI) を実運用化したのが本作。
              </p>
            </div>
          </RevealSection>

          <RevealSection>
            <div className={styles.pillarsGrid}>
              {PILLARS.map((p) => {
                const klass =
                  p.klass === 'pillarA'
                    ? styles.pillarA
                    : p.klass === 'pillarB'
                      ? styles.pillarB
                      : styles.pillarC;
                return (
                  <article
                    key={p.title}
                    className={mergeClasses(styles.pillar, klass)}
                  >
                    <div className={styles.pillarIcon}>{p.icon}</div>
                    <div className={styles.pillarKpi}>
                      <CountUp value={p.kpi} />
                      <span className={styles.pillarKpiUnit}>{p.unit}</span>
                    </div>
                    <h3 className={styles.pillarTitle}>{p.title}</h3>
                    <p className={styles.pillarBody}>{p.body}</p>
                  </article>
                );
              })}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section className={styles.section} aria-labelledby="how-title">
        <div className={styles.sectionInner}>
          <RevealSection>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionEyebrow}>HOW IT WORKS</span>
              <h2 id="how-title" className={styles.sectionTitle}>
                3 ステップで派遣。
              </h2>
              <p className={styles.sectionLede}>
                セットアップは Teams 管理者操作 1 回のみ。それ以降は会議のたびに
                <strong> URL を貼って派遣ボタンを押すだけ</strong>。
              </p>
            </div>
          </RevealSection>

          <RevealSection>
            <div className={styles.steps}>
              {STEPS.map((s) => (
                <article key={s.index} className={styles.step}>
                  <span className={styles.stepIndex}>STEP {s.index}</span>
                  <h3 className={styles.stepTitle}>{s.title}</h3>
                  <p className={styles.stepBody}>{s.body}</p>
                </article>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ============ FINAL CTA BAND ============ */}
      <section className={styles.ctaBand} aria-labelledby="cta-title">
        <RevealSection>
          <div className={styles.ctaBandInner}>
            <CompassNorthwestRegular
              style={{
                color: 'var(--accent-cyan)',
                width: 36,
                height: 36,
              }}
            />
            <h2 id="cta-title" className={styles.ctaBandTitle}>
              いまから 1 つ、Helmsman を試してみる。
            </h2>
            <p className={styles.ctaBandHint}>
              10 分の試運転で約 ¥1。クレジットカード不要、ログイン任意。
            </p>
            <div className={styles.ctaRow}>
              <Button
                appearance="primary"
                size="large"
                icon={<ArrowRight24Regular />}
                onClick={() => navigate('/new')}
              >
                Bot を派遣する
              </Button>
              <a
                href="/insights"
                className={styles.ctaSecondary}
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/insights');
                }}
              >
                利用状況を見る
              </a>
            </div>
          </div>
        </RevealSection>
      </section>
    </div>
  );
}
