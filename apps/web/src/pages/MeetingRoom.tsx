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

import { BotStatusStrip } from '@/components/BotStatusStrip';
import { CostCard } from '@/components/CostCard';
import { DocumentUpload } from '@/components/DocumentUpload';
import { GoalEditor } from '@/components/GoalEditor';
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
    gridTemplateColumns: '1fr 320px',
    minHeight: '100vh',
    '@media (max-width: 900px)': {
      gridTemplateColumns: '1fr',
    },
  },
  main: {
    padding: '24px 32px 48px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  eyebrow: {
    color: tokens.colorNeutralForeground3,
    fontSize: '11px',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '12px',
    flexWrap: 'wrap',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: 600,
    letterSpacing: '-0.01em',
  },
  meta: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
  },
  feedRow: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: '16px',
  },
  tools: {
    marginTop: '8px',
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

  const { data: transcript } = useQuery({
    queryKey: ['transcript', meetingId, organizerId],
    queryFn: () => api.getBotTranscript(meetingId!, organizerId),
    enabled: !!meetingId && meeting?.bot_status === 'in_call',
    refetchInterval: 3000,
  });

  if (isLoading || !meeting) {
    return (
      <div className={styles.loading}>
        <Spinner size="large" label="司令室を準備中..." />
      </div>
    );
  }

  const botActive = meeting.bot_status === 'in_call' || meeting.bot_status === 'connecting';
  const liveUtteranceCount = transcript?.utterance_count ?? 0;
  const needsDispatch = !botActive;
  const showOnboarding = needsDispatch && !meeting.teams_meeting_url;

  return (
    <div className={styles.root}>
      <div className={styles.main}>
        <header className={styles.header}>
          <span className={styles.eyebrow}>Mission Control</span>
          <Title2 as="h1" className={styles.title}>
            {meeting.goal || '派遣セッション (ゴール未設定)'}
          </Title2>
          <div className={styles.titleRow}>
            <Caption1 className={styles.meta}>
              {meeting.mode} · {meeting.total_minutes} min · {meeting.state}
            </Caption1>
            <GoalEditor meeting={meeting} organizerId={organizerId} />
          </div>
        </header>

        <BotStatusStrip meeting={meeting} liveUtteranceCount={liveUtteranceCount} />

        {showOnboarding && <OnboardingSteps />}

        {needsDispatch && <TeamsBotInvite meeting={meeting} organizerId={organizerId} />}

        <div className={styles.feedRow}>
          <InterventionFeed meeting={meeting} />
          <LiveTranscript meetingId={meeting.id} organizerId={organizerId} />
        </div>

        <div className={styles.tools}>
          <Accordion collapsible multiple>
            <AccordionItem value="cost">
              <AccordionHeader>LLM コスト</AccordionHeader>
              <AccordionPanel>
                <CostCard usage={meeting.usage} />
              </AccordionPanel>
            </AccordionItem>
            <AccordionItem value="docs">
              <AccordionHeader>
                参考文書 ({meeting.document_ids.length})
              </AccordionHeader>
              <AccordionPanel>
                <DocumentUpload
                  meetingId={meeting.id}
                  organizerId={organizerId}
                  uploadedBy={userId}
                />
              </AccordionPanel>
            </AccordionItem>
            <AccordionItem value="dev-stt">
              <AccordionHeader>Browser STT (dev fallback)</AccordionHeader>
              <AccordionPanel>
                <Body1
                  style={{ color: tokens.colorNeutralForeground3, marginBottom: 8 }}
                >
                  Teams Bot を使わず手動で発言を入れる時のみ。
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
