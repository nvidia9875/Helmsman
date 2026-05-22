/**
 * useFaceSignalUploader (Phase 6) — frame を蓄積し 4 秒 batch でサーバーへ送る。
 *
 * 設計判断 (ADR-105):
 *   - クライアント側で 2 秒窓に集計 (aggregateFrames)
 *   - 4 秒ごとに 2 windows を 1 batch で POST
 *   - 失敗しても retry しない (次の batch で勝手に追いつく、サーバー側もリアルタイム)
 *   - 同梱関数 onFrame() を <FaceCaptureCard> に渡せば全部つながる
 */
import { useCallback, useEffect, useRef } from 'react';

import { aggregateFrames } from '@/lib/face/detectors';
import type { FaceFrame } from '@/lib/face/landmarker';
import { api } from '@/lib/api';

// 2 秒の窓 (= 約 20 frame @ 10Hz)
const WINDOW_MS = 2_000;
// 4 秒に 1 度 POST (= 2 windows / batch)
const FLUSH_INTERVAL_MS = 4_000;

interface Options {
  meetingId: string;
  organizerId: string;
  participantId: string;
  /** 有効化フラグ。OFF なら frame を受けても何もしない (cleanup あり) */
  enabled: boolean;
}

interface Pending {
  windowStartMs: number;
  frames: FaceFrame[];
}

export function useFaceSignalUploader(opts: Options) {
  const { meetingId, organizerId, participantId, enabled } = opts;
  const pendingRef = useRef<Pending | null>(null);
  const pendingWindowsRef = useRef<ReturnType<typeof aggregateFrames>[]>([]);
  const intervalIdRef = useRef<number | null>(null);

  const flush = useCallback(async () => {
    const closedWindows = pendingWindowsRef.current.filter(
      (w): w is NonNullable<typeof w> => w !== null,
    );
    pendingWindowsRef.current = [];
    if (closedWindows.length === 0) return;
    try {
      await api.ingestFaceSignals(meetingId, organizerId, {
        meeting_id: meetingId,
        organizer_id: organizerId,
        participant_id: participantId,
        client_sent_at_ms: performance.now(),
        windows: closedWindows.map((w) => ({
          window_start_ms: w.windowStart,
          sample_count: w.sampleCount,
          nod_count: w.nodCount,
          confusion: w.confusion,
          engagement: w.engagement,
          face_visible_ratio: w.faceVisibleRatio,
        })),
      });
    } catch (e) {
      // 単発の失敗はリトライしない (次の batch で補える)
      // eslint-disable-next-line no-console
      console.warn('[face] upload failed', e);
    }
  }, [meetingId, organizerId, participantId]);

  const onFrame = useCallback((frame: FaceFrame) => {
    if (!enabled) return;

    // 進行中 window が無ければ開始
    let p = pendingRef.current;
    if (!p) {
      p = { windowStartMs: frame.timestamp, frames: [] };
      pendingRef.current = p;
    }
    // 2 秒経過なら閉じて新 window 開始
    if (frame.timestamp - p.windowStartMs >= WINDOW_MS) {
      const w = aggregateFrames(p.frames);
      pendingWindowsRef.current.push(w);
      p = { windowStartMs: frame.timestamp, frames: [] };
      pendingRef.current = p;
    }
    p.frames.push(frame);
  }, [enabled]);

  // enabled が true の間だけ interval flush を回す
  useEffect(() => {
    if (!enabled) {
      pendingRef.current = null;
      pendingWindowsRef.current = [];
      if (intervalIdRef.current !== null) {
        clearInterval(intervalIdRef.current);
        intervalIdRef.current = null;
      }
      return;
    }
    intervalIdRef.current = window.setInterval(flush, FLUSH_INTERVAL_MS);
    return () => {
      if (intervalIdRef.current !== null) {
        clearInterval(intervalIdRef.current);
        intervalIdRef.current = null;
      }
      // 終了時に残りも送る (best effort、await はしない)
      void flush();
    };
  }, [enabled, flush]);

  return { onFrame };
}
