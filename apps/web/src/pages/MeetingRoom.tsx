import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Body1,
  Caption1,
  Spinner,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'react-router-dom';

import { BotMissionCard } from '@/components/BotMissionCard';
import { CostCard } from '@/components/CostCard';
import { DocumentUpload } from '@/components/DocumentUpload';
import { InterventionFeed } from '@/components/InterventionFeed';
import { LiveTranscript } from '@/components/LiveTranscript';
import { OnboardingSteps } from '@/components/OnboardingSteps';
import { Sidebar } from '@/components/Sidebar';
import { TeamsBotInvite } from '@/components/TeamsBotInvite';
import { UtteranceConsole } from '@/components/UtteranceConsole';
import { api } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    display: 'grid',
    gridTemplateColumns: '1fr 360px',
    minHeight: '100vh',
  },
  main: {
    padding: '32px 36px 48px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  goalRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  meta: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
    letterSpacing: '0.02em',
  },
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
    '@media (max-width: 1100px)': {
      gridTemplateColumns: '1fr',
    },
  },
  utilsRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
    '@media (max-width: 1100px)': {
      gridTemplateColumns: '1fr',
    },
  },
  devFallback: {
    marginTop: '8px',
    border: `1px dashed ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '4px 16px',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  loading: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export function MeetingRoom() {
  const styles = useStyles();
  const { meetingId } = useParams<{ meetingId: string }>();
  const [searchParams] = useSearchParams();
  const { userId } = useIdentity();
  const queryClient = useQueryClient();
  const organizerId = searchParams.get('organizer_id') ?? userId;

  const { data: meeting, isLoading } = useQuery({
    queryKey: ['meeting', meetingId, organizerId],
    queryFn: () => api.getMeeting(meetingId!, organizerId),
    enabled: !!meetingId,
    refetchInterval: 4000,
  });

  // 発言数だけ知りたい (ヒーローカード用) — bot 動作中のみ polling
  const { data: transcript } = useQuery({
    queryKey: ['transcript', meetingId, organizerId],
    queryFn: () => api.getBotTranscript(meetingId!, organizerId),
    enabled: !!meetingId && meeting?.bot_status === 'in_call',
    refetchInterval: 3000,
  });

  if (isLoading || !meeting) {
    return (
      <div className={styles.loading}>
        <Spinner size="large" label="会議を読み込み中..." />
      </div>
    );
  }

  const botIdle = meeting.bot_status === 'idle';
  const botActive = meeting.bot_status === 'in_call' || meeting.bot_status === 'connecting';
  const liveUtteranceCount = transcript?.utterance_count ?? 0;

  return (
    <div className={styles.root}>
      <div className={styles.main}>
        <div className={styles.goalRow}>
          <Title2 style={{ margin: 0 }}>{meeting.goal}</Title2>
          <Caption1 className={styles.meta}>
            モード {meeting.mode} ・ 予定 {meeting.total_minutes} 分 ・ 状態 {meeting.state}
          </Caption1>
        </div>

        <BotMissionCard meeting={meeting} liveUtteranceCount={liveUtteranceCount} />

        {botIdle && <OnboardingSteps />}

        <TeamsBotInvite meeting={meeting} organizerId={organizerId} />

        <div className={styles.twoCol}>
          <InterventionFeed meeting={meeting} />
          <LiveTranscript meetingId={meeting.id} organizerId={organizerId} />
        </div>

        {botActive ? (
          // Bot 動作中は補助カードは折りたたみで邪魔しない
          <div className={styles.devFallback}>
            <Accordion collapsible>
              <AccordionItem value="cost">
                <AccordionHeader>💰 LLM コスト & 利用</AccordionHeader>
                <AccordionPanel>
                  <CostCard usage={meeting.usage} />
                </AccordionPanel>
              </AccordionItem>
              <AccordionItem value="docs">
                <AccordionHeader>
                  📎 参考文書 ({meeting.document_ids.length})
                </AccordionHeader>
                <AccordionPanel>
                  <DocumentUpload
                    meetingId={meeting.id}
                    organizerId={organizerId}
                    uploadedBy={userId}
                  />
                </AccordionPanel>
              </AccordionItem>
            </Accordion>
          </div>
        ) : (
          // 待機中はカードを展開して文書アップロード等を促す
          <div className={styles.utilsRow}>
            <CostCard usage={meeting.usage} />
            <DocumentUpload
              meetingId={meeting.id}
              organizerId={organizerId}
              uploadedBy={userId}
            />
          </div>
        )}

        <div className={styles.devFallback}>
          <Accordion collapsible>
            <AccordionItem value="dev-stt">
              <AccordionHeader>
                🛠️ Browser STT — Bot を使わず手動で発言を入れる (デバッグ用)
              </AccordionHeader>
              <AccordionPanel>
                <Body1 style={{ color: tokens.colorNeutralForeground3, marginBottom: 8 }}>
                  通常デモは Teams Bot を使ってください。
                </Body1>
                <UtteranceConsole
                  meeting={meeting}
                  organizerId={organizerId}
                  onTickComplete={() =>
                    queryClient.invalidateQueries({
                      queryKey: ['meeting', meetingId, organizerId],
                    })
                  }
                />
              </AccordionPanel>
            </AccordionItem>
          </Accordion>
        </div>
      </div>

      <Sidebar meeting={meeting} organizerId={organizerId} />
    </div>
  );
}
