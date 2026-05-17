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
        <Title1>議事録は完成、次は会議そのものを成功させる時代へ。</Title1>
        <Body1 className={styles.pitch}>
          会議のゴールを宣言するだけで、6+1 のエージェントが論点を分解し、時間を管理し、
          議論の脱線を戻し、押し殺された反対意見を浮かび上がらせ、決定を構造化します。
          どんな会議ツールでも、物理会議室でも、全員のデバイスに同期するサイドバーで会議の質を変える。
        </Body1>

        <div className={styles.actions}>
          <Button appearance="primary" size="large" onClick={() => navigate('/new')}>
            + 新規会議を作る
          </Button>
          <Button
            appearance="secondary"
            size="large"
            onClick={() => {
              const id = window.prompt('参加する会議 ID は？');
              if (id) navigate(`/m/${id}/join`);
            }}
          >
            既存会議に参加
          </Button>
        </div>
      </div>

      <div className={styles.features}>
        <Card>
          <CardHeader header={<Title3>🎯 ゴール駆動</Title3>} description="ゴールから論点を MECE 分解。" />
        </Card>
        <Card>
          <CardHeader header={<Title3>📋 カバレッジ追跡</Title3>} description="リアルタイムで論点状態を更新。" />
        </Card>
        <Card>
          <CardHeader header={<Title3>🧭 ステアリング</Title3>} description="議論が逸れたら自然に戻す。" />
        </Card>
        <Card>
          <CardHeader header={<Title3>🗳️ 決定キャプチャ</Title3>} description="決まった瞬間を構造化記録。" />
        </Card>
      </div>

      <UsageSummaryCard organizerId={userId} />

      <RecentMeetings organizerId={userId} />
    </div>
  );
}
