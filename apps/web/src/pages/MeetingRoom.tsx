import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Body1,
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
import { GroupAttachment } from '@/components/GroupAttachment';
import { InterventionFeed } from '@/components/InterventionFeed';
import { LiveTranscript } from '@/components/LiveTranscript';
import { MeetingPulse } from '@/components/MeetingPulse';
import { MeetingSettings } from '@/components/MeetingSettings';
import { OnboardingSteps } from '@/components/OnboardingSteps';
import { CountUp } from '@/components/primitives/CountUp';
import { Sidebar } from '@/components/Sidebar';
import { TeamsBotInvite } from '@/components/TeamsBotInvite';
import { UtteranceConsole } from '@/components/UtteranceConsole';
import { Kpi, KpiRow } from '@/components/primitives/Kpi';
import { Skeleton } from '@/components/primitives/Skeleton';
import { api } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  page: {
    display: 'grid',
    gridTemplateColumns: '1fr 320px',
    minHeight: 'calc(100vh - 52px)',
    '@media (max-width: 1100px)': {
      gridTemplateColumns: '1fr',
    },
  },
  main: {
    padding: '24px 28px 48px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    minWidth: 0,
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  eyebrow: {
    color: 'var(--accent)',
    fontSize: '10px',
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  titleRow: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '16px',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: 600,
    letterSpacing: '-0.015em',
    lineHeight: 1.2,
    color: 'var(--text-1)',
    maxWidth: '760px',
  },
  meta: {
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  metaInline: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
  },
  metaSep: {
    color: 'var(--text-4)',
  },
  feedGrid: {
    display: 'grid',
    gridTemplateColumns: '1.4fr 1fr',
    gap: '14px',
    '@media (max-width: 1280px)': {
      gridTemplateColumns: '1fr',
    },
  },
  tools: {
    marginTop: '8px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    overflow: 'hidden',
    backgroundColor: 'var(--bg-1)',
  },
  docsPanel: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    overflow: 'hidden',
  },
  docsHeader: {
    padding: '14px 18px',
    borderBottom: '1px solid var(--border-hairline)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '10px',
  },
  docsTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
  },
  docsBody: {
    padding: '16px 18px 18px',
  },
  docsCount: {
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
  },
  groupBanner: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-2)',
    padding: '12px 16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
  },
  groupBannerText: {
    fontSize: '12px',
    color: 'var(--text-2)',
  },
  loading: {
    padding: '24px 28px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  loadingKpi: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: '12px',
  },
  loadingFeed: {
    display: 'grid',
    gridTemplateColumns: '1.4fr 1fr',
    gap: '14px',
  },
});

function fmtUsd(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function fmtTokens(value: number): string {
  if (value >= 10_000) return `${(value / 1000).toFixed(1)}k`;
  return value.toLocaleString();
}

const STATUS_LABEL: Record<string, string> = {
  idle: 'STAND BY',
  connecting: 'JOINING',
  in_call: 'LISTENING',
  disconnected: 'LEFT',
  failed: 'FAILED',
};

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
        <Skeleton height={56} />
        <Skeleton height={88} />
        <div className={styles.loadingKpi}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} height={80} />
          ))}
        </div>
        <div className={styles.loadingFeed}>
          <Skeleton height={320} />
          <Skeleton height={320} />
        </div>
      </div>
    );
  }

  const botActive = meeting.bot_status === 'in_call' || meeting.bot_status === 'connecting';
  const liveUtteranceCount = transcript?.utterance_count ?? 0;
  const needsDispatch = !botActive;
  const showOnboarding = needsDispatch && !meeting.teams_meeting_url;
  const decidedCount = meeting.topics.filter((t) => t.state === 'decided').length;

  return (
    <div className={styles.page}>
      <div className={styles.main}>
        <header className={styles.header}>
          <span className={styles.eyebrow}>
            MISSION CONTROL · session
            {meeting.facilitator_name && ` · ${meeting.facilitator_name}`}
          </span>
          <div className={styles.titleRow}>
            <Title2 as="h1" className={styles.title}>
              {meeting.goal || (
                <span style={{ color: 'var(--text-3)' }}>派遣セッション (ゴール未設定)</span>
              )}
            </Title2>
            <div className={styles.meta}>
              <span className={styles.metaInline}>{meeting.mode}</span>
              <span className={styles.metaSep}>·</span>
              <span className={styles.metaInline}>{meeting.total_minutes} min</span>
              <span className={styles.metaSep}>·</span>
              <span className={styles.metaInline}>{meeting.state.replace('_', ' ')}</span>
              <GoalEditor meeting={meeting} organizerId={organizerId} />
            </div>
          </div>
        </header>

        <BotStatusStrip meeting={meeting} liveUtteranceCount={liveUtteranceCount} />

        <KpiRow>
          <Kpi
            label="Bot status"
            value={STATUS_LABEL[meeting.bot_status] ?? meeting.bot_status}
            hint={meeting.teams_meeting_url ? 'Teams URL wired' : 'awaiting URL'}
          />
          <Kpi
            label="Utterances"
            value={<CountUp value={liveUtteranceCount} className="num-mono" />}
            hint={meeting.bot_status === 'in_call' ? 'live · STT' : 'idle'}
          />
          <Kpi
            label="Interventions"
            value={<CountUp value={meeting.delivered_interventions.length} className="num-mono" />}
            hint="L1 / L2 / L3 累計"
          />
          <Kpi
            label="Decisions"
            value={
              <span className="num-mono">
                <CountUp value={decidedCount} />/{meeting.topics.length}
              </span>
            }
            hint={meeting.topics.length === 0 ? 'no topics' : 'decided / total'}
          />
          <Kpi
            label="LLM cost"
            value={
              <CountUp
                value={meeting.usage.total_cost_usd}
                className="num-mono"
                fmt={(v) => fmtUsd(v)}
              />
            }
            hint={`${fmtTokens(meeting.usage.total_tokens)} tok · ${meeting.usage.call_count} calls`}
          />
        </KpiRow>

        {showOnboarding && <OnboardingSteps />}
        {needsDispatch && <TeamsBotInvite meeting={meeting} organizerId={organizerId} />}

        <MeetingSettings meeting={meeting} organizerId={organizerId} />

        <section className={`${styles.docsPanel} glass`} aria-label="参考文書">
          <header className={styles.docsHeader}>
            <h2 className={styles.docsTitle}>
              参考文書 · この会議で AI が読みます
            </h2>
            <span className={styles.docsCount}>
              {meeting.document_ids.length} doc{meeting.document_ids.length === 1 ? '' : 's'}
              {meeting.group_id ? ' + group' : ''}
            </span>
          </header>
          <div className={styles.docsBody}>
            <DocumentUpload
              scope={{
                kind: 'meeting',
                meetingId: meeting.id,
                organizerId,
                allowRedecompose: true,
              }}
              uploadedBy={userId}
            />
          </div>
        </section>

        <GroupAttachment meeting={meeting} organizerId={organizerId} />

        <MeetingPulse meeting={meeting} transcript={transcript} />

        <div className={styles.feedGrid}>
          <InterventionFeed meeting={meeting} organizerId={organizerId} />
          <LiveTranscript meetingId={meeting.id} organizerId={organizerId} />
        </div>

        <div className={styles.tools}>
          <Accordion collapsible multiple>
            <AccordionItem value="cost">
              <AccordionHeader>LLM コスト詳細</AccordionHeader>
              <AccordionPanel>
                <CostCard usage={meeting.usage} />
              </AccordionPanel>
            </AccordionItem>
            <AccordionItem value="dev-stt">
              <AccordionHeader>Browser STT (dev fallback)</AccordionHeader>
              <AccordionPanel>
                <Body1 style={{ color: tokens.colorNeutralForeground3, marginBottom: 8 }}>
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
