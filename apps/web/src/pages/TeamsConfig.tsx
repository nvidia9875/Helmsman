/**
 * Teams Tab Configuration page.
 *
 * Teams の「タブを追加」ダイアログから iframe で開かれ、保存時に
 * contentUrl / suggestedDisplayName を Teams に渡す役割を持つ。
 *
 * manifest.json の `configurableTabs[0].configurationUrl` がこのページを指す。
 */
import { Button, makeStyles } from '@fluentui/react-components';
import { app, pages } from '@microsoft/teams-js';
import { useEffect, useState } from 'react';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    padding: '24px',
    maxWidth: '560px',
    margin: '24px auto',
    border: '1px solid var(--border-hairline)',
    borderRadius: '12px',
    backgroundColor: 'var(--bg-1)',
    backdropFilter: 'blur(12px) saturate(140%)',
    color: 'var(--text-1)',
  },
  eyebrow: {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: 'var(--accent-cyan)',
    fontFamily: 'var(--font-mono)',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
  },
  desc: {
    color: 'var(--text-3)',
    fontSize: '13px',
    margin: 0,
  },
  list: {
    margin: 0,
    paddingLeft: '20px',
    color: 'var(--text-2)',
    fontSize: '13px',
    lineHeight: 1.7,
  },
  status: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-3)',
  },
});

export function TeamsConfig() {
  const styles = useStyles();
  const [status, setStatus] = useState<'init' | 'ready' | 'standalone'>('init');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await app.initialize();
        if (cancelled) return;
        pages.config.registerOnSaveHandler((saveEvent) => {
          const baseUrl = window.location.origin;
          pages.config
            .setConfig({
              contentUrl: `${baseUrl}/?teamsTab=1`,
              websiteUrl: baseUrl,
              entityId: 'helmsman-mission-control',
              suggestedDisplayName: 'Helmsman',
            })
            .then(() => saveEvent.notifySuccess())
            .catch((err) => saveEvent.notifyFailure(String(err)));
        });
        pages.config.setValidityState(true);
        setStatus('ready');
      } catch {
        setStatus('standalone');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={styles.root}>
      <div className={styles.eyebrow}>TEAMS · TAB CONFIG</div>
      <h2 className={styles.title}>Helmsman を会議タブに追加</h2>
      <p className={styles.desc}>
        この会議の Mission Control ダッシュボードをタブとして開きます。
        派遣 / 介入 / 決定構造化をタブ内で確認できます。
      </p>
      <ul className={styles.list}>
        <li>会議内のチャットで Bot に "派遣" すると Helmsman が音声参加</li>
        <li>このタブが会議中の介入・transcript・コストを表示</li>
        <li>会議終了時に決定 / topics / 議事メモが構造化保存</li>
      </ul>
      <span className={styles.status}>
        {status === 'init' && 'Initializing Teams SDK…'}
        {status === 'ready' && '✓ Teams context ready. 右下の Save を押して追加してください。'}
        {status === 'standalone' && '(standalone browser preview — Teams 内ではない。Save ハンドラは未登録)'}
      </span>
      {status === 'standalone' && (
        <Button as="a" href="/" appearance="primary">
          ダッシュボードを開く
        </Button>
      )}
    </div>
  );
}
