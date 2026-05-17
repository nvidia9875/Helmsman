import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Body1,
  Spinner,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'react-router-dom';

import { CostCard } from '@/components/CostCard';
import { DocumentUpload } from '@/components/DocumentUpload';
import { LiveTranscript } from '@/components/LiveTranscript';
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
    padding: '32px',
    overflowY: 'auto',
  },
  loading: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  devFallback: {
    marginTop: '24px',
    border: `1px dashed ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '4px 16px',
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

  if (isLoading || !meeting) {
    return (
      <div className={styles.loading}>
        <Spinner size="large" label="会議を読み込み中..." />
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <div className={styles.main}>
        <Title2>{meeting.goal}</Title2>
        <Body1 style={{ color: tokens.colorNeutralForeground2, marginTop: 8 }}>
          モード: {meeting.mode} ／ 予定: {meeting.total_minutes} 分 ／ 状態: {meeting.state}
        </Body1>

        <TeamsBotInvite meeting={meeting} organizerId={organizerId} />

        <LiveTranscript meetingId={meeting.id} organizerId={organizerId} />

        <CostCard usage={meeting.usage} />

        <DocumentUpload
          meetingId={meeting.id}
          organizerId={organizerId}
          uploadedBy={userId}
        />

        <div className={styles.devFallback}>
          <Accordion collapsible>
            <AccordionItem value="dev-stt">
              <AccordionHeader>
                🛠️ Browser STT (Web Speech API) — 開発用フォールバック
              </AccordionHeader>
              <AccordionPanel>
                <Body1 style={{ color: tokens.colorNeutralForeground3, marginBottom: 8 }}>
                  Teams Bot を使わずに、このブラウザのマイクから発言を入れたい時用。
                  通常デモは上の Bot 招待を使ってください。
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

      <Sidebar meeting={meeting} />
    </div>
  );
}
