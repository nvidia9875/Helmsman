import {
  Body1,
  Button,
  Card,
  CardHeader,
  Title1,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { Sparkle24Filled } from '@fluentui/react-icons';
import { useNavigate } from 'react-router-dom';

import { RecentMeetings } from '@/components/RecentMeetings';
import { UsageSummaryCard } from '@/components/UsageSummaryCard';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 24px',
    gap: '24px',
    textAlign: 'center',
  },
  hero: {
    maxWidth: '720px',
  },
  brand: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '12px',
    color: tokens.colorBrandForeground1,
    marginBottom: '16px',
  },
  pitch: {
    color: tokens.colorNeutralForeground2,
    marginTop: '16px',
    lineHeight: '1.8',
  },
  actions: {
    display: 'flex',
    gap: '12px',
    marginTop: '32px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  features: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '16px',
    maxWidth: '960px',
    width: '100%',
    marginTop: '48px',
  },
});

export function Landing() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { userId } = useIdentity();

  return (
    <div className={styles.root}>
      <div className={styles.hero}>
        <div className={styles.brand}>
          <Sparkle24Filled />
          <Title3>Helmsman</Title3>
        </div>
        <Title1>Teams 会議に AI 副操縦士を派遣する。</Title1>
        <Body1 className={styles.pitch}>
          Helmsman は<strong>会議を作るアプリではありません</strong>。
          Teams カレンダーに既にある会議の URL を貼ると、Bot が「Helmsman 🧭 (External)」として参加し、
          論点を分解し、時間を管理し、議論の脱線を戻し、押し殺された反対意見を浮上させ、
          決定を構造化します。
        </Body1>

        <div className={styles.actions}>
          <Button appearance="primary" size="large" onClick={() => navigate('/new')}>
            🤖 Bot を Teams 会議に派遣
          </Button>
        </div>
      </div>

      <div className={styles.features}>
        <Card>
          <CardHeader
            header={<Title3>📅 既存 Teams 会議に</Title3>}
            description="新規会議を作らない。URL を貼って派遣するだけ。"
          />
        </Card>
        <Card>
          <CardHeader
            header={<Title3>📋 8 並列エージェント</Title3>}
            description="論点・時間・決定・沈黙・反対をリアルタイム分析。"
          />
        </Card>
        <Card>
          <CardHeader
            header={<Title3>🔊 音声で介入</Title3>}
            description="L3 介入は Bot が日本語で会議で発話する。"
          />
        </Card>
        <Card>
          <CardHeader
            header={<Title3>💰 1 円単位のコスト</Title3>}
            description="Azure OpenAI 課金を会議単位で表示。"
          />
        </Card>
      </div>

      <UsageSummaryCard organizerId={userId} />

      <RecentMeetings organizerId={userId} />
    </div>
  );
}
