import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Body1,
  Button,
  Caption1,
  Dropdown,
  Field,
  Input,
  Option,
  Spinner,
  Textarea,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { api, type MeetingMode } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    padding: '48px 24px',
  },
  inner: {
    width: '100%',
    maxWidth: '560px',
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  eyebrow: {
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: tokens.colorNeutralForeground3,
  },
  title: {
    margin: 0,
    fontSize: '28px',
    lineHeight: 1.2,
    letterSpacing: '-0.01em',
    fontWeight: 600,
  },
  intro: {
    color: tokens.colorNeutralForeground2,
    lineHeight: 1.6,
    fontSize: '14px',
    margin: '4px 0 0',
  },
  parentBanner: {
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: '8px',
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    fontSize: '13px',
    color: tokens.colorNeutralForeground2,
  },
  inheritedList: {
    margin: '4px 0 0',
    paddingLeft: '18px',
    color: tokens.colorNeutralForeground2,
    fontSize: '13px',
    lineHeight: 1.6,
  },
  primaryGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  optionalGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    '@media (max-width: 540px)': {
      gridTemplateColumns: '1fr',
    },
  },
  ctaRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginTop: '8px',
  },
  hint: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
  },
  errorText: {
    color: '#fca5a5',
    fontSize: '12px',
  },
  backLink: {
    fontSize: '13px',
    color: tokens.colorNeutralForeground3,
  },
});

const MODES: MeetingMode[] = ['Decision', 'Brainstorm', 'Status', 'Interview', '1on1', 'Kickoff'];
const TEAMS_URL_PATTERN = /^https:\/\/teams\.microsoft\.com\/.+meetup-join/;

export function CreateMeeting() {
  const styles = useStyles();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { userId, displayName, setName } = useIdentity();
  const parentId = searchParams.get('parent');

  const { data: parentMeeting } = useQuery({
    queryKey: ['meeting', parentId, userId],
    queryFn: () => api.getMeeting(parentId!, userId),
    enabled: !!parentId,
  });

  const [teamsUrl, setTeamsUrl] = useState('');
  const [goal, setGoal] = useState('');
  const [mode, setMode] = useState<MeetingMode>('Decision');
  const [totalMinutes, setTotalMinutes] = useState(60);
  const [name, setNameLocal] = useState(displayName === 'Anonymous' ? '' : displayName);

  const dispatchMutation = useMutation({
    mutationFn: () =>
      api.startMeeting({
        organizer_id: userId,
        goal: goal.trim(),
        mode,
        total_minutes: totalMinutes,
        parent_meeting_id: parentId,
        teams_meeting_url: teamsUrl.trim() || null,
      }),
    onSuccess: (meeting) => {
      if (name) setName(name);
      navigate(`/m/${meeting.id}?organizer_id=${encodeURIComponent(userId)}`);
    },
  });

  const inheritedTopics = parentMeeting?.topics.filter((t) => t.state !== 'decided') ?? [];
  const teamsUrlValid = TEAMS_URL_PATTERN.test(teamsUrl.trim());
  const ready = teamsUrlValid && !!name.trim();

  return (
    <div className={styles.root}>
      <div className={styles.inner}>
        <a className={styles.backLink} onClick={() => navigate('/')} href="#" role="button">
          ← Helmsman
        </a>

        <header className={styles.header}>
          <span className={styles.eyebrow}>
            {parentId ? 'Continue from previous' : 'Dispatch'}
          </span>
          <Title2 as="h1" className={styles.title}>
            {parentId ? '前回セッションを引き継いで派遣' : 'Bot を Teams 会議に派遣'}
          </Title2>
          <p className={styles.intro}>
            Helmsman は新しい会議を作りません。Teams カレンダーにある会議の URL を貼ってください。
            Bot が「Helmsman 🧭 (External)」として参加します。
          </p>
        </header>

        {parentMeeting && (
          <div className={styles.parentBanner}>
            <span>
              <strong>前回セッション:</strong>{' '}
              {parentMeeting.goal || '(ゴール未設定)'}
            </span>
            {inheritedTopics.length > 0 ? (
              <>
                <span>引き継ぐ未解決論点 ({inheritedTopics.length} 件)</span>
                <ul className={styles.inheritedList}>
                  {inheritedTopics.map((t) => (
                    <li key={t.id}>{t.name}</li>
                  ))}
                </ul>
              </>
            ) : (
              <Caption1 className={styles.hint}>
                前回の論点は全て決定済。今回は新規の論点構成になります。
              </Caption1>
            )}
          </div>
        )}

        <div className={styles.primaryGroup}>
          <Field label="Teams 会議 URL" required>
            <Input
              value={teamsUrl}
              onChange={(_, d) => setTeamsUrl(d.value)}
              placeholder="https://teams.microsoft.com/l/meetup-join/..."
              size="large"
            />
          </Field>
          {teamsUrl && !teamsUrlValid && (
            <span className={styles.errorText}>
              URL の形式が不正です (https://teams.microsoft.com/.../meetup-join/...)
            </span>
          )}
          <Field label="あなたの表示名" required>
            <Input
              value={name}
              onChange={(_, d) => setNameLocal(d.value)}
              placeholder="例: 山田"
            />
          </Field>
        </div>

        <Accordion collapsible>
          <AccordionItem value="goal">
            <AccordionHeader>会議のゴール (任意)</AccordionHeader>
            <AccordionPanel>
              <Field
                hint="入れると Bot が論点を分解 + 進捗を追跡。空でも『監視のみ』モードで派遣できます。"
              >
                <Textarea
                  value={goal}
                  onChange={(_, d) => setGoal(d.value)}
                  placeholder="例: 6 月 30 日のローンチ可否を決定する"
                  rows={3}
                />
              </Field>
            </AccordionPanel>
          </AccordionItem>
          <AccordionItem value="mode">
            <AccordionHeader>会議モード · 想定時間 (任意)</AccordionHeader>
            <AccordionPanel>
              <div className={styles.optionalGrid}>
                <Field label="モード">
                  <Dropdown
                    value={mode}
                    selectedOptions={[mode]}
                    onOptionSelect={(_, d) =>
                      d.optionValue && setMode(d.optionValue as MeetingMode)
                    }
                  >
                    {MODES.map((m) => (
                      <Option key={m} value={m}>
                        {m}
                      </Option>
                    ))}
                  </Dropdown>
                </Field>
                <Field label="想定時間 (分)">
                  <Input
                    type="number"
                    value={String(totalMinutes)}
                    min={5}
                    max={240}
                    onChange={(_, d) =>
                      setTotalMinutes(Math.max(5, Math.min(240, Number(d.value) || 60)))
                    }
                  />
                </Field>
              </div>
            </AccordionPanel>
          </AccordionItem>
        </Accordion>

        <div className={styles.ctaRow}>
          <Button
            appearance="primary"
            size="large"
            disabled={!ready || dispatchMutation.isPending}
            onClick={() => dispatchMutation.mutate()}
          >
            {dispatchMutation.isPending ? (
              <>
                <Spinner size="tiny" /> 派遣中…
              </>
            ) : (
              'Bot を派遣して司令室を開く'
            )}
          </Button>
        </div>

        {dispatchMutation.isError && (
          <Body1 className={styles.errorText}>
            エラー: {String(dispatchMutation.error)}
          </Body1>
        )}
      </div>
    </div>
  );
}
