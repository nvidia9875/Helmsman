import {
  Badge,
  Button,
  Spinner,
  Textarea,
  makeStyles,
} from '@fluentui/react-components';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import { api } from '@/lib/api';
import type { MeetingReport } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    padding: '4px 0',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  lede: {
    color: 'var(--text-3)',
    fontSize: '12px',
    lineHeight: 1.5,
  },
  inputs: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    '@media (max-width: 720px)': {
      gridTemplateColumns: '1fr',
    },
  },
  fieldLabel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    fontSize: '11px',
    color: 'var(--text-2)',
    fontWeight: 600,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-mono)',
  },
  hint: {
    color: 'var(--text-4)',
    fontSize: '11px',
    fontWeight: 400,
    letterSpacing: '0',
    textTransform: 'none',
    fontFamily: 'inherit',
  },
  textarea: {
    minHeight: '140px',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
  },
  actionsRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  preview: {
    border: '1px solid var(--border-hairline)',
    borderRadius: '12px',
    padding: '18px 22px',
    background: 'var(--surface-1)',
    maxHeight: '480px',
    overflow: 'auto',
  },
  previewMeta: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    color: 'var(--text-3)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    paddingBottom: '8px',
    borderBottom: '1px solid var(--border-hairline)',
    marginBottom: '12px',
  },
  markdown: {
    whiteSpace: 'pre-wrap',
    color: 'var(--text-1)',
    fontSize: '13px',
    lineHeight: 1.7,
    fontFamily: 'var(--font-sans, system-ui)',
  },
  empty: {
    color: 'var(--text-3)',
    fontSize: '12px',
    padding: '14px 0',
  },
  history: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  historyItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 10px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '8px',
    cursor: 'pointer',
    background: 'transparent',
    color: 'var(--text-2)',
    textAlign: 'left',
    fontSize: '12px',
  },
  historyActive: {
    background: 'var(--surface-1)',
    color: 'var(--text-1)',
    border: '1px solid var(--accent)',
  },
  error: {
    color: 'var(--danger, #c5443e)',
    fontSize: '12px',
  },
});

interface ReportPanelProps {
  meetingId: string;
  organizerId: string;
}

const DEFAULT_TEMPLATE_HINT = `# 議事録 — {{title}}

## 開催情報
- 日時:
- 出席:

## 決定事項
{{decisions}}

## 持ち越し論点
{{open_items}}

## 次回までの宿題
{{action_items}}
`;

export function ReportPanel({ meetingId, organizerId }: ReportPanelProps) {
  const styles = useStyles();
  const qc = useQueryClient();
  const [template, setTemplate] = useState('');
  const [memo, setMemo] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const historyQuery = useQuery({
    queryKey: ['reports', meetingId, organizerId],
    queryFn: () => api.listReports(meetingId, organizerId, 20),
  });

  const reports: MeetingReport[] = historyQuery.data ?? [];
  const selected: MeetingReport | undefined = useMemo(() => {
    if (selectedId) return reports.find((r) => r.id === selectedId);
    return reports[0];
  }, [reports, selectedId]);

  // 履歴を読み込んだら直近のテンプレ/メモを復元 (再生成しやすく)
  useEffect(() => {
    if (selected) {
      if (template === '' && selected.template_snapshot) {
        setTemplate(selected.template_snapshot);
      }
      if (memo === '' && selected.memo_snapshot) {
        setMemo(selected.memo_snapshot);
      }
    }
  }, [selected, template, memo]);

  const generate = useMutation({
    mutationFn: () =>
      api.generateReport(meetingId, organizerId, {
        template: template.trim() || null,
        memo: memo.trim() || null,
      }),
    onSuccess: (res) => {
      setSelectedId(res.id);
      qc.invalidateQueries({ queryKey: ['reports', meetingId, organizerId] });
    },
  });

  const copy = async () => {
    if (!selected) return;
    await navigator.clipboard.writeText(selected.report_markdown);
  };

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <span className={styles.lede}>
          会議の goal / 論点 / 決定 / 介入 をベースに markdown レポートを生成します。
          自社テンプレートを貼り付けると章立てを踏襲し、メモを書くとそこが最優先情報源として尊重されます。
        </span>
      </div>

      <div className={styles.inputs}>
        <label className={styles.fieldLabel}>
          <span>
            テンプレート (任意)
            <span className={styles.hint}>
              {' '}空欄ならデフォルト構成。{`{{decisions}}`} 等のプレースホルダを置換します。
            </span>
          </span>
          <Textarea
            className={styles.textarea}
            value={template}
            placeholder={DEFAULT_TEMPLATE_HINT}
            onChange={(_, data) => setTemplate(data.value)}
          />
        </label>
        <label className={styles.fieldLabel}>
          <span>
            メモ (任意)
            <span className={styles.hint}>
              {' '}最優先情報源として扱われます。Helmsman の構造化結果と矛盾があれば
              「⚠️ 事実関係要確認」として明示されます。
            </span>
          </span>
          <Textarea
            className={styles.textarea}
            value={memo}
            placeholder={
              '例: 山田 CTO の発言通り 3H は確定。KPI は議論不十分で次回持ち越し...'
            }
            onChange={(_, data) => setMemo(data.value)}
          />
        </label>
      </div>

      <div className={styles.actionsRow}>
        <Button
          appearance="primary"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
        >
          {generate.isPending ? (
            <>
              <Spinner size="tiny" />
              生成中…
            </>
          ) : (
            'レポートを生成'
          )}
        </Button>
        {selected ? (
          <Button appearance="secondary" onClick={copy}>
            markdown をコピー
          </Button>
        ) : null}
      </div>

      {generate.isError ? (
        <div className={styles.error}>
          生成に失敗しました: {(generate.error as Error).message}
        </div>
      ) : null}

      {reports.length > 1 ? (
        <div className={styles.history}>
          {reports.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => setSelectedId(r.id)}
              className={`${styles.historyItem} ${
                selected?.id === r.id ? styles.historyActive : ''
              }`}
            >
              <span>
                {new Date(r.generated_at).toLocaleString('ja-JP')}{' '}
                {r.template_used ? <Badge appearance="outline">template</Badge> : null}{' '}
                {r.memo_used ? <Badge appearance="outline">memo</Badge> : null}
              </span>
              <span>{r.report_markdown.length} chars</span>
            </button>
          ))}
        </div>
      ) : null}

      {selected ? (
        <article className={styles.preview} aria-label="生成済みレポート">
          <div className={styles.previewMeta}>
            <span>{new Date(selected.generated_at).toLocaleString('ja-JP')}</span>
            {selected.template_used ? <span>· template 使用</span> : null}
            {selected.memo_used ? <span>· memo 使用</span> : null}
            {selected.generator_model ? (
              <span>· {selected.generator_model}</span>
            ) : null}
            {selected.usage ? (
              <span>
                · {selected.usage.prompt_tokens} in / {selected.usage.completion_tokens} out tokens
              </span>
            ) : null}
          </div>
          <pre className={styles.markdown}>{selected.report_markdown}</pre>
        </article>
      ) : (
        <p className={styles.empty}>
          まだレポートはありません。会議が進むと topics と decisions が貯まり、
          より精度の高いレポートが出ます。
        </p>
      )}
    </div>
  );
}
