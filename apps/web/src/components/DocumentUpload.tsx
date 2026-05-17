import { Badge, Body1, Button, Spinner, makeStyles } from '@fluentui/react-components';
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
  docList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  docRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    gap: '12px',
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

interface Props {
  meetingId: string;
  organizerId: string;
  uploadedBy: string;
}

export function DocumentUpload({ meetingId, organizerId, uploadedBy }: Props) {
  const styles = useStyles();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  const { data: documents } = useQuery({
    queryKey: ['documents', meetingId, organizerId],
    queryFn: () => api.listDocuments(meetingId, organizerId),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadDocument(meetingId, organizerId, file, uploadedBy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', meetingId, organizerId] });
    },
  });

  const redecomposeMutation = useMutation({
    mutationFn: () => api.redecompose(meetingId, organizerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId, organizerId] });
    },
  });

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => uploadMutation.mutate(f));
  };

  return (
    <section className={styles.root} aria-label="参考文書アップロード">
      <p className={styles.intro}>
        PDF / Word / PPT / TXT / MD をドラッグ&ドロップ。アップロード後、論点を再分解できます。
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
            </div>
          ))}
        </div>
      )}

      {documents && documents.length > 0 && (
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
    </section>
  );
}
