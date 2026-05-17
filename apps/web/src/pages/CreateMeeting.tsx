import {
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
    maxWidth: '760px',
    margin: '48px auto',
    padding: '32px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  intro: {
    color: tokens.colorNeutralForeground2,
    lineHeight: 1.7,
  },
  primaryField: {
    border: `1px solid ${tokens.colorBrandStroke2}`,
    backgroundColor: tokens.colorBrandBackground2,
    borderRadius: tokens.borderRadiusLarge,
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  optionalGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
    '@media (max-width: 700px)': {
      gridTemplateColumns: '1fr',
    },
  },
  hint: {
    color: tokens.colorNeutralForeground3,
  },
  parentBanner: {
    border: `1px solid ${tokens.colorBrandStroke2}`,
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: tokens.borderRadiusMedium,
    padding: '12px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  inheritedList: {
    margin: '4px 0 0',
    paddingLeft: '20px',
    color: tokens.colorNeutralForeground2,
    fontSize: '13px',
  },
  actionRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
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
      <Title2 style={{ margin: 0 }}>
        {parentId ? '🔁 前回セッションを引き継いで派遣' : '🤖 Helmsman Bot を Teams 会議に派遣'}
      </Title2>
      <Body1 className={styles.intro}>
        Helmsman は<strong>新しい会議を作るアプリではありません</strong>。
        既に Teams カレンダーに入っている会議の URL を貼ってもらえれば、
        Bot が「Helmsman 🧭 (External)」として参加し、議論を分析します。
      </Body1>

      {parentMeeting && (
        <div className={styles.parentBanner}>
          <Body1>
            <strong>📎 前回セッション:</strong> {parentMeeting.goal || '(ゴール未設定)'}
          </Body1>
          {inheritedTopics.length > 0 ? (
            <>
              <Body1>引き継ぐ未解決論点 ({inheritedTopics.length} 件):</Body1>
              <ul className={styles.inheritedList}>
                {inheritedTopics.map((t) => (
                  <li key={t.id}>{t.name}</li>
                ))}
              </ul>
            </>
          ) : (
            <Body1 className={styles.hint}>
              前回の論点は全て決定済です。今回は新規の論点構成になります。
            </Body1>
          )}
        </div>
      )}

      <div className={styles.primaryField}>
        <Field
          label={
            <span>
              📅 Teams 会議 URL <span style={{ color: tokens.colorPaletteRedForeground1 }}>*</span>
            </span>
          }
          hint="Teams カレンダーで会議を開いて「リンクをコピー」した URL を貼ってください"
        >
          <Input
            value={teamsUrl}
            onChange={(_, d) => setTeamsUrl(d.value)}
            placeholder="https://teams.microsoft.com/l/meetup-join/..."
          />
        </Field>
        {teamsUrl && !teamsUrlValid && (
          <Caption1 style={{ color: tokens.colorPaletteRedForeground1 }}>
            URL の形式が不正です (https://teams.microsoft.com/.../meetup-join/...)
          </Caption1>
        )}
      </div>

      <Field label="あなたの表示名 (派遣ホスト)" required>
        <Input value={name} onChange={(_, d) => setNameLocal(d.value)} placeholder="例: 山田" />
      </Field>

      <Field
        label="会議のゴール (任意)"
        hint="入れると Bot が論点を分解 + 進捗を追跡。空のままでも「監視のみ」モードで派遣できます。"
      >
        <Textarea
          value={goal}
          onChange={(_, d) => setGoal(d.value)}
          placeholder="例: 6 月 30 日のローンチ可否を決定する  /  未設定でも OK"
          rows={2}
        />
      </Field>

      <div className={styles.optionalGrid}>
        <Field label="会議モード">
          <Dropdown
            value={mode}
            selectedOptions={[mode]}
            onOptionSelect={(_, d) => d.optionValue && setMode(d.optionValue as MeetingMode)}
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

      <div className={styles.actionRow}>
        <Button
          appearance="primary"
          size="large"
          disabled={!ready || dispatchMutation.isPending}
          onClick={() => dispatchMutation.mutate()}
        >
          {dispatchMutation.isPending ? (
            <>
              <Spinner size="tiny" /> Bot を派遣中…
            </>
          ) : (
            '🤖 Bot を派遣して司令室を開く'
          )}
        </Button>
        <Caption1 className={styles.hint}>
          派遣すると Helmsman が会議に外部参加者として join します。
        </Caption1>
      </div>

      {dispatchMutation.isError && (
        <Body1 style={{ color: tokens.colorPaletteRedForeground1 }}>
          エラー: {String(dispatchMutation.error)}
        </Body1>
      )}
    </div>
  );
}
