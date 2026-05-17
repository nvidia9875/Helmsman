import {
  Badge,
  Body1,
  Button,
  Spinner,
  makeStyles,
} from '@fluentui/react-components';
import {
  ArrowDownload20Regular,
  Delete20Regular,
  DocumentFolderRegular,
} from '@fluentui/react-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import { api, type DocumentStatus, type MeetingDocument } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    padding: '4px 0',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  intro: {
    color: 'var(--text-3)',
    fontSize: '12px',
    lineHeight: 1.6,
    margin: 0,
  },
  dropzone: {
    border: '1px dashed var(--border-default)',
    borderRadius: '10px',
    padding: '28px',
    textAlign: 'center',
    cursor: 'pointer',
    color: 'var(--text-2)',
    fontSize: '13px',
    backgroundColor: 'var(--bg-0)',
    transitionProperty: 'border-color, background-color, color',
    transitionDuration: '120ms',
    ':hover': {
      border: '1px dashed var(--accent)',
      color: 'var(--text-1)',
    },
  },
  dropzoneActive: {
    border: '1px dashed var(--accent)',
    backgroundColor: 'rgba(91, 141, 239, 0.08)',
    color: 'var(--text-1)',
  },
  emptyHint: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: 'var(--text-3)',
    fontSize: '12px',
    fontStyle: 'italic',
  },
  docList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  docRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto auto',
    gap: '10px',
    alignItems: 'center',
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid var(--border-hairline)',
    backgroundColor: 'var(--bg-2)',
  },
  docName: {
    fontSize: '13px',
    color: 'var(--text-1)',
    fontWeight: 500,
    wordBreak: 'break-all',
  },
  docMeta: {
    color: 'var(--text-3)',
    fontSize: '11px',
    marginTop: '2px',
    fontFamily: 'var(--font-mono)',
  },
  hidden: {
    display: 'none',
  },
  actions: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  iconBtn: {
    minWidth: '32px',
    padding: '4px 8px',
  },
});

const STATUS_COLOR: Record<DocumentStatus, 'subtle' | 'warning' | 'success' | 'danger'> = {
  uploaded: 'subtle',
  extracting: 'warning',
  indexed: 'success',
  failed: 'danger',
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  uploaded: 'アップロード済',
  extracting: '抽出中',
  indexed: '索引化済',
  failed: '失敗',
};

export type DocumentScopeArg =
  | { kind: 'meeting'; meetingId: string; organizerId: string; allowRedecompose?: boolean }
  | { kind: 'group'; groupId: string; organizerId: string };

interface Props {
  scope: DocumentScopeArg;
  uploadedBy: string;
  /** 上に表示する説明文を上書きしたい場合 */
  intro?: string;
}

export function DocumentUpload({ scope, uploadedBy, intro }: Props) {
  const styles = useStyles();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  const queryKey =
    scope.kind === 'meeting'
      ? ['documents', scope.meetingId, scope.organizerId]
      : ['group-documents', scope.groupId, scope.organizerId];

  const { data: documents } = useQuery({
    queryKey,
    queryFn: () =>
      scope.kind === 'meeting'
        ? api.listDocuments(scope.meetingId, scope.organizerId)
        : api.listGroupDocuments(scope.groupId, scope.organizerId),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      scope.kind === 'meeting'
        ? api.uploadDocument(scope.meetingId, scope.organizerId, file, uploadedBy)
        : api.uploadGroupDocument(scope.groupId, scope.organizerId, file, uploadedBy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      if (scope.kind === 'meeting') {
        queryClient.invalidateQueries({
          queryKey: ['meeting', scope.meetingId, scope.organizerId],
        });
      } else {
        queryClient.invalidateQueries({
          queryKey: ['group', scope.groupId, scope.organizerId],
        });
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (doc: MeetingDocument) =>
      scope.kind === 'meeting'
        ? api.deleteDocument(scope.meetingId, doc.id, scope.organizerId)
        : api.deleteGroupDocument(scope.groupId, doc.id, scope.organizerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      if (scope.kind === 'meeting') {
        queryClient.invalidateQueries({
          queryKey: ['meeting', scope.meetingId, scope.organizerId],
        });
      } else {
        queryClient.invalidateQueries({
          queryKey: ['group', scope.groupId, scope.organizerId],
        });
      }
    },
  });

  const redecomposeMutation = useMutation({
    mutationFn: () => {
      if (scope.kind !== 'meeting') throw new Error('redecompose is meeting-scope only');
      return api.redecompose(scope.meetingId, scope.organizerId);
    },
    onSuccess: () => {
      if (scope.kind === 'meeting') {
        queryClient.invalidateQueries({
          queryKey: ['meeting', scope.meetingId, scope.organizerId],
        });
      }
    },
  });

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => uploadMutation.mutate(f));
  };

  const handleDownload = async (doc: MeetingDocument) => {
    try {
      const res =
        scope.kind === 'meeting'
          ? await api.getDocumentDownloadUrl(scope.meetingId, doc.id, scope.organizerId)
          : await api.getGroupDocumentDownloadUrl(scope.groupId, doc.id, scope.organizerId);
      window.open(res.url, '_blank', 'noopener');
    } catch (e) {
      alert(`プレビュー URL の取得に失敗: ${String(e)}`);
    }
  };

  const handleDelete = (doc: MeetingDocument) => {
    if (!confirm(`「${doc.filename}」を削除しますか? AIの参照からも外れます。`)) return;
    deleteMutation.mutate(doc);
  };

  const showRedecompose =
    scope.kind === 'meeting' &&
    (scope.allowRedecompose ?? true) &&
    documents &&
    documents.length > 0;

  return (
    <section className={styles.root} aria-label="参考文書">
      <p className={styles.intro}>
        {intro ??
          'PDF / Word / PPT / TXT / MD をドラッグ&ドロップ。' +
            (scope.kind === 'group'
              ? ' グループ配下の全会議で AI が参照します。'
              : ' アップロード後、論点を再分解できます。')}
      </p>

      <label
        className={`${styles.dropzone} ${dragActive ? styles.dropzoneActive : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        {uploadMutation.isPending ? 'アップロード中…' : 'クリック または ドラッグして追加'}
        <input
          ref={inputRef}
          type="file"
          multiple
          className={styles.hidden}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>

      {documents && documents.length === 0 && (
        <div className={styles.emptyHint}>
          <DocumentFolderRegular />
          まだ書類はありません。
        </div>
      )}

      {documents && documents.length > 0 && (
        <div className={styles.docList}>
          {documents.map((d: MeetingDocument) => (
            <div key={d.id} className={styles.docRow}>
              <div>
                <div className={styles.docName}>{d.filename}</div>
                <div className={styles.docMeta}>
                  {(d.size_bytes / 1024).toFixed(1)} KB · {d.chunk_count} chunks
                  {d.error_message && ` · ${d.error_message}`}
                </div>
              </div>
              <Badge appearance="filled" color={STATUS_COLOR[d.status]}>
                {STATUS_LABEL[d.status]}
              </Badge>
              <div style={{ display: 'flex', gap: 4 }}>
                <Button
                  appearance="subtle"
                  size="small"
                  icon={<ArrowDownload20Regular />}
                  onClick={() => handleDownload(d)}
                  className={styles.iconBtn}
                  aria-label={`${d.filename} をダウンロード`}
                  title="プレビュー / ダウンロード"
                />
                <Button
                  appearance="subtle"
                  size="small"
                  icon={<Delete20Regular />}
                  onClick={() => handleDelete(d)}
                  disabled={deleteMutation.isPending}
                  className={styles.iconBtn}
                  aria-label={`${d.filename} を削除`}
                  title="削除"
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {showRedecompose && (
        <div className={styles.actions}>
          <Button
            appearance="primary"
            onClick={() => redecomposeMutation.mutate()}
            disabled={redecomposeMutation.isPending}
          >
            {redecomposeMutation.isPending ? (
              <>
                <Spinner size="tiny" /> 論点を再分解中…
              </>
            ) : (
              '添付文書をもとに論点を再分解する'
            )}
          </Button>
        </div>
      )}

      {uploadMutation.isError && (
        <Body1 style={{ color: '#fca5a5', fontSize: 12 }}>
          アップロード失敗: {String(uploadMutation.error)}
        </Body1>
      )}
      {deleteMutation.isError && (
        <Body1 style={{ color: '#fca5a5', fontSize: 12 }}>
          削除失敗: {String(deleteMutation.error)}
        </Body1>
      )}
    </section>
  );
}
