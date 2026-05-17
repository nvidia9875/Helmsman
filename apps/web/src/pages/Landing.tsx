import {
  Body1,
  Button,
  Title1,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useNavigate } from 'react-router-dom';

import { Pill } from '@/components/primitives/Pill';
import { RecentMeetings } from '@/components/RecentMeetings';
import { UsageSummaryCard } from '@/components/UsageSummaryCard';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '64px 24px 96px',
    gap: '48px',
  },
  hero: {
    maxWidth: '640px',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    gap: '20px',
  },
  brand: {
    fontSize: '13px',
    fontWeight: 600,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    color: tokens.colorNeutralForeground2,
  },
  headline: {
    margin: 0,
    fontSize: '40px',
    lineHeight: 1.15,
    letterSpacing: '-0.02em',
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
  },
  lead: {
    fontSize: '16px',
    lineHeight: 1.6,
    color: tokens.colorNeutralForeground2,
    margin: 0,
    maxWidth: '560px',
  },
  cta: {
    marginTop: '8px',
  },
  badges: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: '4px',
  },
  footnote: {
    fontSize: '12px',
    lineHeight: 1.6,
    color: tokens.colorNeutralForeground3,
    maxWidth: '520px',
    textAlign: 'center',
    margin: '8px 0 0',
  },
  link: {
    color: tokens.colorBrandForeground1,
  },
  diff: {
    width: '100%',
    maxWidth: '720px',
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    '@media (max-width: 640px)': {
      gridTemplateColumns: '1fr',
    },
  },
  diffCol: {
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: '8px',
    padding: '16px 18px',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  diffTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground2,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    margin: '0 0 8px',
  },
  diffList: {
    margin: 0,
    paddingLeft: '18px',
    color: tokens.colorNeutralForeground2,
    fontSize: '13px',
    lineHeight: 1.7,
  },
  sectionWrap: {
    width: '100%',
    maxWidth: '720px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
});

export function Landing() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { userId } = useIdentity();

  return (
    <div className={styles.root}>
      <section className={styles.hero}>
        <span className={styles.brand}>Helmsman</span>
        <Title1 as="h1" className={styles.headline}>
          Teams 会議に AI 副操縦士を派遣する。
        </Title1>
        <Body1 as="p" className={styles.lead}>
          会議を作るアプリではありません。Teams カレンダーに既にある会議の URL を貼ると、
          Bot が外部参加者として join し、論点を追い、時間を管理し、必要なら音声で介入します。
        </Body1>

        <Button
          appearance="primary"
          size="large"
          className={styles.cta}
          onClick={() => navigate('/new')}
        >
          Bot を Teams 会議に派遣
        </Button>

        <div className={styles.badges}>
          <Pill kind="success">Copilot ライセンス不要</Pill>
          <Pill kind="success">外部参加者として join</Pill>
          <Pill kind="success">AI が音声で介入</Pill>
          <Pill kind="brand">MIT OSS</Pill>
        </div>

        <p className={styles.footnote}>
          Microsoft Teams ネイティブの{' '}
          <a
            href="https://learn.microsoft.com/ja-jp/microsoftteams/facilitator-teams"
            target="_blank"
            rel="noreferrer"
            className={styles.link}
          >
            Facilitator
          </a>{' '}
          (Copilot エージェント) との比較は{' '}
          <a
            href="https://github.com/nvidia9875/Helmsman#microsoft-teams-facilitator-との違い-補完関係"
            target="_blank"
            rel="noreferrer"
            className={styles.link}
          >
            README
          </a>{' '}
          を参照。補完関係で同じ会議で同時に使えます。
        </p>
      </section>

      <section className={styles.diff} aria-label="Facilitator との簡易比較">
        <div className={styles.diffCol}>
          <p className={styles.diffTitle}>Microsoft Teams Facilitator</p>
          <ul className={styles.diffList}>
            <li>Copilot ライセンス必須 (~$30/user/月)</li>
            <li>テキスト中心 (チャット mention)</li>
            <li>1on1 / 外部会議は未対応</li>
            <li>単一 AI アシスタント</li>
          </ul>
        </div>
        <div className={styles.diffCol}>
          <p className={styles.diffTitle}>Helmsman 🧭</p>
          <ul className={styles.diffList}>
            <li>追加ライセンス不要 (Azure サブスクのみ)</li>
            <li>音声介入 (L3) + 8 並列エージェント</li>
            <li>外部参加者として any 会議に join</li>
            <li>会議学アルゴリズム + OSS で拡張可能</li>
          </ul>
        </div>
      </section>

      <div className={styles.sectionWrap}>
        <UsageSummaryCard organizerId={userId} />
        <RecentMeetings organizerId={userId} />
      </div>
    </div>
  );
}
