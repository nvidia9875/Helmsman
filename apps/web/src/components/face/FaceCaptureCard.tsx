/**
 * FaceCaptureCard (Phase 6) — Webcam を opt-in で起動するカード。
 *
 * UX 方針 (ADR-107):
 *   - デフォルト OFF、明示的なトグルで起動
 *   - 起動中は「📷 face signals ON」常時表示
 *   - 1-click で OFF にできる
 *   - 生フレームはサーバー送信しない (短い disclosure 表示)
 *   - エラー / 拒否時は graceful な誘導 UI
 *
 * 注: シグナル送信 (POST /meetings/{id}/face-signals) と
 *      集計ロジック (nod/confusion/engagement) は Task 6-2 / 6-3 で。
 *      ここでは「カメラを使う UI 体験」までを担う。
 */
import { Button, Switch, makeStyles } from '@fluentui/react-components';
import { Video24Filled, Video24Regular, VideoOff24Regular } from '@fluentui/react-icons';
import { useCallback, useEffect, useRef, useState } from 'react';

import { useFaceSignals } from '@/hooks/useFaceSignals';
import type { FaceFrame } from '@/lib/face/landmarker';

const useStyles = makeStyles({
  root: {
    border: '1px solid rgba(92, 240, 245, 0.28)',
    borderRadius: '12px',
    backgroundColor: 'rgba(92, 240, 245, 0.04)',
    padding: '16px 18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
    flexWrap: 'wrap',
  },
  headerLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
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
    fontSize: '14px',
    fontWeight: 600,
    margin: 0,
    color: 'var(--text-1)',
  },
  desc: {
    fontSize: '12px',
    color: 'var(--text-3)',
    margin: 0,
    lineHeight: 1.55,
  },
  body: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    gap: '14px',
    alignItems: 'flex-start',
    '@media (max-width: 720px)': {
      gridTemplateColumns: '1fr',
    },
  },
  videoWrap: {
    position: 'relative',
    width: '180px',
    aspectRatio: '4/3',
    borderRadius: '8px',
    overflow: 'hidden',
    backgroundColor: '#000',
    border: '1px solid var(--border-hairline)',
  },
  video: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transform: 'scaleX(-1)', // 鏡像 (ユーザーが直感的に分かる)
  },
  badge: {
    position: 'absolute',
    top: '6px',
    left: '6px',
    fontSize: '9px',
    fontWeight: 700,
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.1em',
    padding: '2px 6px',
    borderRadius: '4px',
    backgroundColor: 'rgba(255, 71, 87, 0.85)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  badgeDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#fff',
    animation: '$pulse 1.4s ease-in-out infinite',
  },
  '@keyframes pulse': {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.3 },
  },
  emptyPreview: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-4)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  status: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    minWidth: 0,
  },
  statusRow: {
    fontSize: '12px',
    color: 'var(--text-2)',
    lineHeight: 1.55,
  },
  metric: {
    display: 'inline-flex',
    gap: '6px',
    padding: '2px 8px',
    border: '1px solid var(--border-hairline)',
    borderRadius: '999px',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    fontVariantNumeric: 'tabular-nums',
    color: 'var(--text-2)',
  },
  metricRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    marginTop: '6px',
  },
  privacy: {
    fontSize: '11px',
    color: 'var(--text-3)',
    lineHeight: 1.5,
    margin: 0,
    padding: '10px 12px',
    backgroundColor: 'var(--bg-0)',
    borderRadius: '8px',
    border: '1px dashed var(--border-hairline)',
  },
  error: {
    fontSize: '12px',
    color: '#fca5a5',
    lineHeight: 1.5,
    margin: 0,
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
});

interface Props {
  /** 1 frame 毎に呼ばれる callback。集計や送信は親側で行う。 */
  onFrame?: (frame: FaceFrame) => void;
}

export function FaceCaptureCard({ onFrame }: Props) {
  const styles = useStyles();
  const videoElRef = useRef<HTMLVideoElement | null>(null);
  const [latestFrame, setLatestFrame] = useState<FaceFrame | null>(null);

  // 直近 frame を UI とコールバック両方に渡す
  const handleFrame = useCallback(
    (f: FaceFrame) => {
      setLatestFrame(f);
      onFrame?.(f);
    },
    [onFrame],
  );

  const face = useFaceSignals({ intervalMs: 100, onFrame: handleFrame });

  // stream が出来たらプレビュー <video> に接続
  useEffect(() => {
    if (videoElRef.current) {
      videoElRef.current.srcObject = face.stream;
    }
  }, [face.stream]);

  const running = face.status === 'running';
  const starting = face.status === 'starting';
  const denied = face.status === 'denied';
  const errored = face.status === 'error';
  const enabled = running || starting;

  return (
    <section className={styles.root} aria-label="顔シグナル (任意)">
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.eyebrow}>FACE SIGNALS · OPT-IN</span>
          <h3 className={styles.title}>うなずき / 困惑 / 集中度を AI に渡す</h3>
          <p className={styles.desc}>
            ブラウザのカメラで表情を読み取って、議論中の signal を AI に渡します。
            動画は <strong>送信されません</strong>。集計値だけがサーバーへ流れます。
          </p>
        </div>
        <div className={styles.toggle}>
          <Switch
            checked={enabled}
            onChange={(_, d) => (d.checked ? face.start() : face.stop())}
            disabled={starting}
            label={running ? 'ON' : 'OFF'}
          />
        </div>
      </header>

      <div className={styles.body}>
        <div className={styles.videoWrap}>
          {face.stream ? (
            <>
              <video
                ref={videoElRef}
                autoPlay
                muted
                playsInline
                className={styles.video}
              />
              {running && (
                <span className={styles.badge} aria-label="顔シグナル 動作中">
                  <span className={styles.badgeDot} /> ON AIR
                </span>
              )}
            </>
          ) : (
            <div className={styles.emptyPreview}>
              {denied ? (
                <VideoOff24Regular />
              ) : starting ? (
                <Video24Filled />
              ) : (
                <Video24Regular />
              )}
            </div>
          )}
        </div>

        <div className={styles.status}>
          {denied || errored ? (
            <p className={styles.error}>{face.errorMessage}</p>
          ) : starting ? (
            <p className={styles.statusRow}>カメラを起動しています…</p>
          ) : running ? (
            <>
              <p className={styles.statusRow}>
                解析中 — 顔が
                {latestFrame?.detected ? ' 検出されています ✓' : ' 見えていません'}
              </p>
              {latestFrame && (
                <div className={styles.metricRow}>
                  <span className={styles.metric}>
                    pitch {latestFrame.headPitchDeg.toFixed(1)}°
                  </span>
                  <span className={styles.metric}>
                    brow {(
                      ((latestFrame.blendshapes.browDownLeft ?? 0) +
                        (latestFrame.blendshapes.browDownRight ?? 0)) /
                      2
                    ).toFixed(2)}
                  </span>
                  <span className={styles.metric}>
                    blink {(
                      ((latestFrame.blendshapes.eyeBlinkLeft ?? 0) +
                        (latestFrame.blendshapes.eyeBlinkRight ?? 0)) /
                      2
                    ).toFixed(2)}
                  </span>
                </div>
              )}
            </>
          ) : (
            <p className={styles.statusRow}>
              トグルで ON にすると、AI に「うなずき」「困惑」「集中度」が伝わります。
            </p>
          )}

          <p className={styles.privacy}>
            🔒 プライバシー: フレーム画像はあなたのブラウザの中だけで処理されます。
            サーバーには 2 秒ごとの集計値 (うなずき回数 / 困惑度 / 集中度) のみが送られます。
            データは 30 日で自動削除されます。
            <br />
            <Button
              appearance="subtle"
              size="small"
              onClick={() => face.stop()}
              disabled={!enabled}
              style={{ marginTop: 6, fontSize: 11 }}
            >
              いつでも OFF にできます
            </Button>
          </p>
        </div>
      </div>
    </section>
  );
}
