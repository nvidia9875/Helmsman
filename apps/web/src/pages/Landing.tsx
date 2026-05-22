/**
 * Landing — tool-first トップページ。
 *
 * 設計方針 (ユーザ指示):
 *   - マーケコピー / ハッカソン表記 / pillar 等は一切置かない (/help へ退避済)
 *   - 中央に URL 入力 + 派遣ボタンだけ。**詳細設定は折りたたみ**
 *   - 詳細設定 = AI ファシリテーター名 / ゴール / モード / 時間 / グループ
 *   - 動きは「気持ちいい」レベル: aurora drift / focus glow / submit ripple
 *
 * 流れ:
 *   1. URL を貼る → 検証パス → ボタン active
 *   2. (任意) "詳細設定" を expand
 *   3. 派遣 → /m/:id へ
 */
import {
  Button,
  Dropdown,
  Field,
  Input,
  Option,
  Spinner,
  Textarea,
  makeStyles,
} from '@fluentui/react-components';
import {
  ChevronDown20Regular,
  ChevronUp20Regular,
  Rocket24Regular,
} from '@fluentui/react-icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api, type MeetingMode } from '@/lib/api';
import { useIdentity } from '@/lib/store';

const NO_GROUP = '__none__';
const TEAMS_URL_PATTERN = /^https:\/\/teams\.microsoft\.com\/(.+meetup-join|meet\/\d+)/;
const DEFAULT_FACILITATOR_NAME = 'Helmsman';
const MODES: MeetingMode[] = ['Decision', 'Brainstorm', 'Status', 'Interview', '1on1', 'Kickoff'];

const useStyles = makeStyles({
  page: {
    position: 'relative',
    minHeight: 'calc(100vh - 52px)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 24px',
    overflow: 'hidden',
    backgroundColor: 'var(--bg-0)',
  },

  // ============ 背景アニメ (aurora) ============
  // 3 つの色付き円を巨大に blur して body 上を漂わせる。
  // 全部 transform/opacity アニメで合成 GPU 化、JS スクロール一切なし。
  auroraA: {
    position: 'absolute',
    top: '-20%',
    left: '50%',
    width: 'min(1200px, 130vw)',
    height: 'min(1200px, 130vw)',
    background:
      'radial-gradient(circle at center, rgba(91, 141, 239, 0.28) 0%, rgba(91, 141, 239, 0) 60%)',
    filter: 'blur(60px)',
    transform: 'translate(-50%, 0)',
    pointerEvents: 'none',
    zIndex: 0,
    animationName: {
      '0%, 100%': { transform: 'translate(-50%, 0) scale(1)' },
      '50%': { transform: 'translate(-46%, -2%) scale(1.06)' },
    },
    animationDuration: '18s',
    animationIterationCount: 'infinite',
    animationTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
  auroraB: {
    position: 'absolute',
    bottom: '-30%',
    left: '-10%',
    width: '70vw',
    height: '70vw',
    background:
      'radial-gradient(circle at center, rgba(176, 124, 255, 0.22) 0%, rgba(176, 124, 255, 0) 65%)',
    filter: 'blur(70px)',
    pointerEvents: 'none',
    zIndex: 0,
    animationName: {
      '0%, 100%': { transform: 'translate(0, 0) scale(1)', opacity: 0.7 },
      '50%': { transform: 'translate(4%, -3%) scale(1.08)', opacity: 1 },
    },
    animationDuration: '22s',
    animationIterationCount: 'infinite',
  },
  auroraC: {
    position: 'absolute',
    top: '-10%',
    right: '-10%',
    width: '55vw',
    height: '55vw',
    background:
      'radial-gradient(circle at center, rgba(92, 240, 245, 0.18) 0%, rgba(92, 240, 245, 0) 60%)',
    filter: 'blur(70px)',
    pointerEvents: 'none',
    zIndex: 0,
    animationName: {
      '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
      '50%': { transform: 'translate(-2%, 4%) scale(1.1)' },
    },
    animationDuration: '26s',
    animationIterationCount: 'infinite',
  },

  // 微細なグリッドオーバーレイ — 「ツールっぽさ」を出す
  grid: {
    position: 'absolute',
    inset: 0,
    backgroundImage:
      'linear-gradient(to right, rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.025) 1px, transparent 1px)',
    backgroundSize: '64px 64px',
    pointerEvents: 'none',
    maskImage:
      'radial-gradient(ellipse at center, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 70%)',
    WebkitMaskImage:
      'radial-gradient(ellipse at center, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 70%)',
    zIndex: 0,
  },

  // ============ 中央カード ============
  card: {
    position: 'relative',
    width: '100%',
    maxWidth: '640px',
    zIndex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    padding: '36px 36px 28px',
    borderRadius: '20px',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    backgroundColor: 'rgba(12, 12, 16, 0.72)',
    backdropFilter: 'blur(24px) saturate(160%)',
    WebkitBackdropFilter: 'blur(24px) saturate(160%)',
    boxShadow:
      '0 24px 64px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
    // mount アニメ
    animationName: {
      '0%': { opacity: 0, transform: 'translateY(8px) scale(0.98)' },
      '100%': { opacity: 1, transform: 'translateY(0) scale(1)' },
    },
    animationDuration: '700ms',
    animationTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },

  // ロゴマーク + brand name
  brandRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    fontWeight: 600,
  },
  brandMark: {
    width: '20px',
    height: '20px',
    borderRadius: '6px',
    background: 'linear-gradient(135deg, #5b8def 0%, #3661cf 100%)',
    color: '#fff',
    fontSize: '11px',
    fontWeight: 800,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 0 16px rgba(91, 141, 239, 0.4)',
  },

  // 入力 + ボタン inline
  inputRow: {
    display: 'flex',
    gap: '10px',
    alignItems: 'stretch',
    '@media (max-width: 540px)': {
      flexDirection: 'column',
    },
  },
  urlInputWrap: {
    position: 'relative',
    flex: 1,
    minWidth: 0,
  },
  // Fluent Input のラッパに focus-within で glow
  urlInputShell: {
    position: 'relative',
    borderRadius: '12px',
    transitionProperty: 'box-shadow, transform',
    transitionDuration: '240ms',
    transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
    ':focus-within': {
      boxShadow:
        '0 0 0 1px rgba(91, 141, 239, 0.6), 0 0 32px rgba(91, 141, 239, 0.18)',
    },
  },
  urlInput: {
    width: '100%',
    height: '52px',
    fontSize: '14px',
    fontFamily: 'var(--font-mono)',
    borderRadius: '12px',
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    color: 'var(--text-1)',
    padding: '0 16px',
    outline: 'none',
    transitionProperty: 'border-color, background-color',
    transitionDuration: '200ms',
    '::placeholder': {
      color: 'var(--text-4)',
    },
    ':focus': {
      border: '1px solid rgba(91, 141, 239, 0.6)',
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
    },
  },
  // validate 状態のドット
  validDot: {
    position: 'absolute',
    right: '14px',
    top: '50%',
    transform: 'translateY(-50%)',
    width: '8px',
    height: '8px',
    borderRadius: '999px',
    pointerEvents: 'none',
    transitionProperty: 'background-color, box-shadow',
    transitionDuration: '200ms',
  },
  validDotOk: {
    backgroundColor: '#3ddc97',
    boxShadow: '0 0 12px rgba(61, 220, 151, 0.6)',
  },
  validDotPending: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  validDotError: {
    backgroundColor: '#fca5a5',
    boxShadow: '0 0 12px rgba(252, 165, 165, 0.4)',
  },

  dispatchBtn: {
    height: '52px',
    minWidth: '160px',
    fontSize: '14px',
    fontWeight: 600,
    borderRadius: '12px',
    background: 'linear-gradient(135deg, #5b8def 0%, #4a6dd9 100%)',
    border: '1px solid rgba(91, 141, 239, 0.5)',
    color: '#fff',
    boxShadow: '0 8px 32px rgba(91, 141, 239, 0.35)',
    transitionProperty: 'transform, box-shadow, opacity',
    transitionDuration: '160ms',
    transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
    ':hover': {
      transform: 'translateY(-1px)',
      boxShadow: '0 12px 40px rgba(91, 141, 239, 0.5)',
    },
    ':active': {
      transform: 'translateY(0)',
    },
    ':disabled': {
      opacity: 0.5,
      boxShadow: 'none',
      cursor: 'not-allowed',
    },
  },

  // 詳細設定 toggle
  detailsToggle: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    padding: '8px 4px',
    background: 'transparent',
    border: 'none',
    color: 'var(--text-3)',
    fontSize: '12px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    cursor: 'pointer',
    transitionProperty: 'color',
    transitionDuration: '160ms',
    ':hover': { color: 'var(--text-1)' },
  },
  detailsToggleLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },

  details: {
    display: 'grid',
    gridTemplateRows: '0fr',
    transitionProperty: 'grid-template-rows',
    transitionDuration: '320ms',
    transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
  detailsOpen: {
    gridTemplateRows: '1fr',
  },
  detailsInner: {
    overflow: 'hidden',
  },
  detailsBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    padding: '14px 4px 4px',
    borderTop: '1px solid rgba(255, 255, 255, 0.06)',
  },
  detailsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    '@media (max-width: 540px)': {
      gridTemplateColumns: '1fr',
    },
  },

  // フッター行
  footerRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: '6px',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-4)',
    letterSpacing: '0.06em',
  },
  helpLink: {
    color: 'var(--text-3)',
    textDecoration: 'none',
    transitionProperty: 'color',
    transitionDuration: '160ms',
    ':hover': { color: 'var(--accent)' },
  },

  // エラー / Hint
  errorText: {
    fontSize: '12px',
    color: '#fca5a5',
    fontFamily: 'var(--font-mono)',
    margin: '4px 4px 0',
  },
});

export function Landing() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { userId, displayName, setName } = useIdentity();
  const initialName =
    displayName && displayName !== 'Anonymous' ? displayName : DEFAULT_FACILITATOR_NAME;

  const [teamsUrl, setTeamsUrl] = useState('');
  const [showDetails, setShowDetails] = useState(false);
  const [goal, setGoal] = useState('');
  const [mode, setMode] = useState<MeetingMode>('Decision');
  const [totalMinutes, setTotalMinutes] = useState(60);
  const [groupId, setGroupId] = useState<string>(NO_GROUP);
  const [facilitatorName, setFacilitatorName] = useState(initialName);

  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    // mount 後に軽くフォーカスして "ここから始める" を示す
    const id = window.setTimeout(() => inputRef.current?.focus(), 350);
    return () => window.clearTimeout(id);
  }, []);

  const { data: groups } = useQuery({
    queryKey: ['groups', userId],
    queryFn: () => api.listGroups(userId),
    enabled: showDetails,  // expand されるまで読み込まない
  });

  const dispatchMutation = useMutation({
    mutationFn: () =>
      api.startMeeting({
        organizer_id: userId,
        goal: goal.trim(),
        mode,
        total_minutes: totalMinutes,
        teams_meeting_url: teamsUrl.trim() || null,
        group_id: groupId === NO_GROUP ? null : groupId,
        facilitator_name: facilitatorName.trim() || null,
      }),
    onSuccess: (meeting) => {
      if (facilitatorName) setName(facilitatorName);
      navigate(`/m/${meeting.id}?organizer_id=${encodeURIComponent(userId)}`);
    },
  });

  const urlTrimmed = teamsUrl.trim();
  const urlValid = TEAMS_URL_PATTERN.test(urlTrimmed);
  const urlEmpty = urlTrimmed.length === 0;
  const facilitatorOk = facilitatorName.trim().length > 0;
  const ready = urlValid && facilitatorOk && !dispatchMutation.isPending;

  const dotClass = urlEmpty
    ? styles.validDotPending
    : urlValid
      ? styles.validDotOk
      : styles.validDotError;

  return (
    <main className={styles.page} aria-label="Helmsman dispatch">
      <div className={styles.auroraA} aria-hidden />
      <div className={styles.auroraB} aria-hidden />
      <div className={styles.auroraC} aria-hidden />
      <div className={styles.grid} aria-hidden />

      <section className={styles.card}>
        <div className={styles.brandRow}>
          <span className={styles.brandMark} aria-hidden>
            H
          </span>
          <span>Helmsman · dispatch</span>
        </div>

        <div className={styles.inputRow}>
          <div className={styles.urlInputWrap}>
            <div className={styles.urlInputShell}>
              <input
                ref={inputRef}
                className={styles.urlInput}
                type="url"
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
                placeholder="https://teams.microsoft.com/meet/..."
                value={teamsUrl}
                onChange={(e) => setTeamsUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && ready) dispatchMutation.mutate();
                }}
                aria-label="Teams 会議の URL"
                aria-invalid={!urlEmpty && !urlValid}
              />
              <span className={`${styles.validDot} ${dotClass}`} aria-hidden />
            </div>
          </div>
          <Button
            appearance="primary"
            size="large"
            icon={
              dispatchMutation.isPending ? <Spinner size="tiny" /> : <Rocket24Regular />
            }
            className={styles.dispatchBtn}
            disabled={!ready}
            onClick={() => dispatchMutation.mutate()}
          >
            {dispatchMutation.isPending ? '派遣中…' : '派遣'}
          </Button>
        </div>

        {!urlEmpty && !urlValid && (
          <p className={styles.errorText}>
            Teams 会議 URL の形式を確認してください
          </p>
        )}
        {dispatchMutation.isError && (
          <p className={styles.errorText}>
            派遣に失敗しました — {String(dispatchMutation.error)}
          </p>
        )}

        <button
          type="button"
          className={styles.detailsToggle}
          onClick={() => setShowDetails((s) => !s)}
          aria-expanded={showDetails}
          aria-controls="dispatch-details"
        >
          <span className={styles.detailsToggleLeft}>
            <span>詳細設定</span>
            <span style={{ color: 'var(--text-4)' }}>
              · ゴール / モード / 時間 / グループ
            </span>
          </span>
          {showDetails ? <ChevronUp20Regular /> : <ChevronDown20Regular />}
        </button>

        <div
          id="dispatch-details"
          className={`${styles.details} ${showDetails ? styles.detailsOpen : ''}`}
        >
          <div className={styles.detailsInner}>
            <div className={styles.detailsBody}>
              <Field label="AI ファシリテーター名">
                <Input
                  value={facilitatorName}
                  onChange={(_, d) => setFacilitatorName(d.value)}
                  placeholder="例: Helmsman"
                />
              </Field>
              <Field label="ゴール (任意 — 入れると論点を分解)">
                <Textarea
                  value={goal}
                  onChange={(_, d) => setGoal(d.value)}
                  placeholder="例: 6 月 30 日のローンチ可否を決定する"
                  rows={2}
                />
              </Field>
              <div className={styles.detailsGrid}>
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
              <Field label="グループ (任意 — 共有書類を AI に読ませる)">
                <Dropdown
                  placeholder="(なし — 単独で派遣)"
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
            </div>
          </div>
        </div>

        <div className={styles.footerRow}>
          <span>Enter キーで派遣</span>
          <a className={styles.helpLink} href="/help">
            Helmsman とは →
          </a>
        </div>
      </section>
    </main>
  );
}
