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
} from '@fluentui/react-components';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { Pill } from '@/components/primitives/Pill';
import { api, type MeetingMode } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const NO_GROUP = '__none__';

const useStyles = makeStyles({
  root: {
    padding: '32px 28px 64px',
    width: '100%',
  },
  back: {
    fontSize: '11px',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    textDecoration: 'none',
    cursor: 'pointer',
    transitionProperty: 'color',
    transitionDuration: '120ms',
    ':hover': { color: 'var(--text-1)' },
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    marginTop: '12px',
    marginBottom: '24px',
  },
  eyebrow: {
    color: 'var(--accent)',
    fontSize: '10px',
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  title: {
    margin: 0,
    fontSize: '28px',
    lineHeight: 1.15,
    letterSpacing: '-0.015em',
    fontWeight: 600,
    color: 'var(--text-1)',
  },
  intro: {
    color: 'var(--text-2)',
    lineHeight: 1.55,
    fontSize: '14px',
    margin: '4px 0 0',
    maxWidth: '640px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1.4fr 1fr',
    gap: '24px',
    alignItems: 'flex-start',
    '@media (max-width: 1024px)': {
      gridTemplateColumns: '1fr',
    },
  },
  panel: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-1)',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingBottom: '12px',
    borderBottom: '1px solid var(--border-hairline)',
  },
  panelTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-1)',
    margin: 0,
  },
  sectionLabel: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
  },
  parentBanner: {
    border: '1px solid var(--border-hairline)',
    backgroundColor: 'var(--bg-2)',
    borderRadius: '8px',
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    fontSize: '13px',
    color: 'var(--text-2)',
  },
  inheritedList: {
    margin: '4px 0 0',
    paddingLeft: '18px',
    color: 'var(--text-2)',
    fontSize: '13px',
    lineHeight: 1.6,
  },
  primaryGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
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
    color: 'var(--text-3)',
    fontSize: '12px',
  },
  errorText: {
    color: '#fca5a5',
    fontSize: '12px',
  },
  previewItem: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    gap: '12px',
    alignItems: 'flex-start',
    padding: '12px 0',
    borderTop: '1px solid var(--border-hairline)',
    ':first-child': { borderTop: 'none' },
  },
  previewIdx: {
    width: '24px',
    height: '24px',
    borderRadius: '6px',
    backgroundColor: 'var(--bg-2)',
    border: '1px solid var(--border-hairline)',
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  previewBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  previewLabel: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-1)',
  },
  previewDesc: {
    fontSize: '12px',
    color: 'var(--text-3)',
    lineHeight: 1.5,
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    rowGap: '10px',
    columnGap: '14px',
    fontSize: '13px',
  },
  summaryKey: {
    color: 'var(--text-3)',
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    paddingTop: '2px',
  },
  summaryValue: {
    color: 'var(--text-1)',
    fontSize: '13px',
    wordBreak: 'break-word',
  },
  facilitatorHint: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '11px',
    color: 'var(--text-3)',
    marginTop: '2px',
  },
});

const MODES: MeetingMode[] = ['Decision', 'Brainstorm', 'Status', 'Interview', '1on1', 'Kickoff'];
const TEAMS_URL_PATTERN = /^https:\/\/teams\.microsoft\.com\/(.+meetup-join|meet\/\d+)/;

const PREVIEW_STEPS: { label: string; desc: string }[] = [
  {
    label: 'Bot が会議に参加',
    desc: '「{name} 🧭 (External)」として外部参加者扱いで join。Teams ロビー承認が必要な場合あり。',
  },
  {
    label: 'ACS で音声を取得',
    desc: 'Media Streaming で会議音声を受信し、Azure Speech で 5 秒ごとに文字起こし。',
  },
  {
    label: '8 エージェントが並列分析',
    desc: 'Coverage / Steering / Decision / Quiet / Dissent / TimeKeeper を毎ターン実行。',
  },
  {
    label: 'Intervention が L1/L2/L3 で発火',
    desc: 'Arbiter が重要度を判定し、L1=サイドバー、L3=Bot が会議で発話。',
  },
];

export function CreateMeeting() {
  const styles = useStyles();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { userId } = useIdentity();
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
  const [groupId, setGroupId] = useState<string>(NO_GROUP);

  const { data: groups } = useQuery({
    queryKey: ['groups', userId],
    queryFn: () => api.listGroups(userId),
  });

  const dispatchMutation = useMutation({
    mutationFn: () =>
      api.startMeeting({
        organizer_id: userId,
        goal: goal.trim(),
        mode,
        total_minutes: totalMinutes,
        parent_meeting_id: parentId,
        teams_meeting_url: teamsUrl.trim() || null,
        group_id: groupId === NO_GROUP ? null : groupId,
      }),
    onSuccess: (meeting) => {
      navigate(`/m/${meeting.id}?organizer_id=${encodeURIComponent(userId)}`);
    },
  });

  const inheritedTopics = parentMeeting?.topics.filter((t) => t.state !== 'decided') ?? [];
  const teamsUrlValid = TEAMS_URL_PATTERN.test(teamsUrl.trim());
  const ready = teamsUrlValid;
  // Bot の Teams 表示名は固定 (アプリ登録名 "Helmsman")。会議ごとには変えられない。
  const displayedFacilitator = 'Helmsman';

  return (
    <div className={styles.root}>
      <a className={styles.back} onClick={() => navigate('/')} href="#" role="button">
        ← back to Overview
      </a>

      <header className={styles.header}>
        <span className={styles.eyebrow}>
          {parentId ? 'CONTINUE FROM PREVIOUS · dispatch' : 'DISPATCH · new bot'}
        </span>
        <Title2 as="h1" className={styles.title}>
          {parentId ? '前回セッションを引き継いで派遣' : 'Bot を Teams 会議に派遣'}
        </Title2>
        <p className={styles.intro}>
          Helmsman は新しい会議を作りません。Teams カレンダーにある会議の URL を貼ってください。
          Bot は「Helmsman 🧭 (External)」として参加します。
        </p>
      </header>

      <div className={styles.grid}>
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Dispatch form</h2>
            <span className={styles.sectionLabel}>required + optional</span>
          </div>

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
                placeholder="https://teams.microsoft.com/meet/... または .../meetup-join/..."
                size="large"
              />
            </Field>
            {teamsUrl && !teamsUrlValid && (
              <span className={styles.errorText}>
                URL の形式が不正です (https://teams.microsoft.com/meet/... または .../meetup-join/...)
              </span>
            )}

          </div>

          <Accordion collapsible>
            <AccordionItem value="goal">
              <AccordionHeader>会議のゴール (任意)</AccordionHeader>
              <AccordionPanel>
                <Field hint="入れると Bot が論点を分解 + 進捗を追跡。空でも『監視のみ』モードで派遣できます。">
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
            <AccordionItem value="group">
              <AccordionHeader>
                グループに所属させる (任意)
              </AccordionHeader>
              <AccordionPanel>
                <Field hint="所属グループの共有書類を AI が参照します。">
                  <Dropdown
                    placeholder="グループを選ぶ (任意)"
                    value={
                      groupId === NO_GROUP
                        ? ''
                        : groups?.find((g) => g.id === groupId)?.name ?? ''
                    }
                    selectedOptions={[groupId]}
                    onOptionSelect={(_, d) => setGroupId(d.optionValue ?? NO_GROUP)}
                  >
                    <Option value={NO_GROUP}>(なし — 単独で派遣)</Option>
                    {(groups ?? []).map((g) => (
                      <Option key={g.id} value={g.id}>
                        {g.name}
                      </Option>
                    ))}
                  </Dropdown>
                </Field>
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
            <span className={styles.hint}>
              派遣後すぐ Mission Control に遷移します。
            </span>
          </div>

          {dispatchMutation.isError && (
            <Body1 className={styles.errorText}>
              エラー: {String(dispatchMutation.error)}
            </Body1>
          )}
        </section>

        <aside className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>What will happen</h2>
            <Pill kind="brand">PREVIEW</Pill>
          </div>

          <div>
            {PREVIEW_STEPS.map((s, i) => (
              <div key={i} className={styles.previewItem}>
                <span className={styles.previewIdx}>{i + 1}</span>
                <div className={styles.previewBody}>
                  <span className={styles.previewLabel}>
                    {s.label.replace('{name}', displayedFacilitator)}
                  </span>
                  <span className={styles.previewDesc}>
                    {s.desc.replace('{name}', displayedFacilitator)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className={styles.panelHeader}>
            <h3 className={styles.panelTitle}>Summary</h3>
            <span className={styles.sectionLabel}>preview</span>
          </div>
          <div className={styles.summaryGrid}>
            <span className={styles.summaryKey}>Facilitator</span>
            <span className={styles.summaryValue}>
              {displayedFacilitator} <span style={{ color: 'var(--text-3)' }}>🧭</span>
            </span>
            <span className={styles.summaryKey}>Teams URL</span>
            <span
              className={styles.summaryValue}
              style={teamsUrl ? {} : { color: 'var(--text-3)' }}
            >
              {teamsUrl
                ? `${teamsUrl.slice(0, 48)}${teamsUrl.length > 48 ? '…' : ''}`
                : '(未入力)'}
            </span>
            <span className={styles.summaryKey}>Mode</span>
            <span className={styles.summaryValue}>{mode}</span>
            <span className={styles.summaryKey}>Duration</span>
            <span className={styles.summaryValue}>
              <span className="num-mono">{totalMinutes}</span> min
            </span>
            <span className={styles.summaryKey}>Goal</span>
            <span
              className={styles.summaryValue}
              style={goal.trim() ? {} : { color: 'var(--text-3)' }}
            >
              {goal.trim() || '(未設定 — 監視のみモード)'}
            </span>
          </div>
        </aside>
      </div>
    </div>
  );
}
