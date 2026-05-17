import {
  Badge,
  Body1,
  Button,
  Caption1,
  Spinner,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import { api, type DocumentStatus, type MeetingDocument } from '@/lib/api';

const useStyles = makeStyles({
  root: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: '16px',
    marginTop: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  dropzone: {
    border: `2px dashed ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusMedium,
    padding: '24px',
    textAlign: 'center',
    cursor: 'pointer',
    transitionProperty: 'background-color',
    transitionDuration: '100ms',
    transitionTimingFunction: 'ease',
  },
  dropzoneActive: {
    backgroundColor: tokens.colorBrandBackground2,
    border: `2px dashed ${tokens.colorBrandStroke1}`,
  },
  docList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  docRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    gap: '8px',
    alignItems: 'center',
    padding: '8px 12px',
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground2,
  },
  docMeta: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
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
    mutationFn: (file: File) =>
      api.uploadDocument(meetingId, organizerId, file, uploadedBy),
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
      <Title3 as="h2" style={{ margin: 0 }}>
        📎 参考文書 ({documents?.length ?? 0})
      </Title3>
      <Caption1>
        PDF / Word / PPT / TXT / MD をドラッグ&ドロップ。アップロード後、論点を再分解できます。
      </Caption1>

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
        <Body1>{uploadMutation.isPending ? 'アップロード中…' : 'クリック または ドラッグして追加'}</Body1>
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
                <Body1>{d.filename}</Body1>
                <div className={styles.docMeta}>
                  {(d.size_bytes / 1024).toFixed(1)} KB ・ {d.chunk_count} chunks
                  {d.error_message && ` ・ ${d.error_message}`}
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
              '🔄 添付文書をもとに論点を再分解する'
            )}
          </Button>
        </div>
      )}

      {uploadMutation.isError && (
        <Body1 style={{ color: tokens.colorPaletteRedForeground1 }}>
          アップロード失敗: {String(uploadMutation.error)}
        </Body1>
      )}
    </section>
  );
}
