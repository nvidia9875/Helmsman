import { Body1, Button, Spinner, Title2, makeStyles, tokens } from '@fluentui/react-components';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { QRCodeSVG } from 'qrcode.react';
import { useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

import { CostCard } from '@/components/CostCard';
import { DocumentUpload } from '@/components/DocumentUpload';
import { Sidebar } from '@/components/Sidebar';
import { UtteranceConsole } from '@/components/UtteranceConsole';
import { api } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    display: 'grid',
    gridTemplateColumns: '1fr 360px',
    minHeight: '100vh',
    '@media (max-width: 900px)': {
      gridTemplateColumns: '1fr',
    },
  },
  main: {
    padding: '32px',
    overflowY: 'auto',
  },
  share: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '16px',
    marginTop: '16px',
    display: 'flex',
    gap: '16px',
    alignItems: 'center',
  },
  qrBox: {
    backgroundColor: tokens.colorNeutralBackground3,
    padding: '8px',
    borderRadius: tokens.borderRadiusMedium,
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
  const [copyState, setCopyState] = useState<'idle' | 'copied'>('idle');

  const { data: meeting, isLoading } = useQuery({
    queryKey: ['meeting', meetingId, organizerId],
    queryFn: () => api.getMeeting(meetingId!, organizerId),
    enabled: !!meetingId,
    refetchInterval: 8000,
  });

  const joinUrl = useMemo(() => {
    if (!meetingId) return '';
    return `${window.location.origin}/m/${meetingId}/join`;
  }, [meetingId]);

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

        <div className={styles.share}>
          <div className={styles.qrBox}>
            <QRCodeSVG value={joinUrl} size={120} bgColor="#1b1b1b" fgColor="#fff" />
          </div>
          <div style={{ flex: 1 }}>
            <Title2 as="h3" style={{ fontSize: 18, marginBottom: 8 }}>
              この会議に参加するリンク
            </Title2>
            <Body1 style={{ wordBreak: 'break-all', color: tokens.colorNeutralForeground2 }}>
              {joinUrl}
            </Body1>
            <Button
              size="small"
              onClick={async () => {
                await navigator.clipboard.writeText(joinUrl);
                setCopyState('copied');
                setTimeout(() => setCopyState('idle'), 1500);
              }}
              style={{ marginTop: 8 }}
            >
              {copyState === 'copied' ? '✓ コピーしました' : 'リンクをコピー'}
            </Button>
          </div>
        </div>

        <CostCard usage={meeting.usage} />

        <DocumentUpload
          meetingId={meeting.id}
          organizerId={organizerId}
          uploadedBy={userId}
        />

        <UtteranceConsole
          meeting={meeting}
          organizerId={organizerId}
          onTickComplete={() =>
            queryClient.invalidateQueries({ queryKey: ['meeting', meetingId, organizerId] })
          }
        />
      </div>

      <Sidebar meeting={meeting} />
    </div>
  );
}
