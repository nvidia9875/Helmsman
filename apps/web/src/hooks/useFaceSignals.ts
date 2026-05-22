/**
 * useFaceSignals (Phase 6) — Webcam を MediaPipe FaceLandmarker に流す React hook。
 *
 * 責務:
 *   - getUserMedia でカメラ取得 (1-click 取消可能、cleanup 完璧に)
 *   - FaceLandmarker を 10Hz で回す (rAF loop + 100ms interval)
 *   - 解析結果 (FaceFrame) を onFrame callback で吐く (生 frame は親に渡さない)
 *   - 集計 (nod/confusion/engagement) は呼び出し側 (lib/face/*.ts) でやる
 *
 * 設計判断:
 *   - ライブラリ依存 import は dynamic、初回 enable まで遅延
 *   - permission denial は graceful (state で表現、throw しない)
 *   - 解析後の raw blendshape は外に流さない、callback でだけ渡す
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { buildFaceFrame, getFaceLandmarker } from '@/lib/face/landmarker';
import type { FaceFrame } from '@/lib/face/landmarker';

type Status = 'idle' | 'starting' | 'running' | 'denied' | 'error';

interface Options {
  /** 解析間隔 (ms)。デフォルト 100ms = 10Hz。 */
  intervalMs?: number;
  /** 1 frame ごとの callback。集計はここで呼び出し側がやる。 */
  onFrame?: (frame: FaceFrame) => void;
}

interface State {
  status: Status;
  /** プレビュー用の MediaStream (ローカル <video> に流す)。停止時は null。 */
  stream: MediaStream | null;
  /** ユーザー向けエラーメッセージ (denied / NotFound 等)。 */
  errorMessage: string | null;
}

interface Controls {
  start: () => Promise<void>;
  stop: () => void;
}

export function useFaceSignals(opts: Options = {}): State & Controls {
  const { intervalMs = 100, onFrame } = opts;

  const [status, setStatus] = useState<Status>('idle');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const rafIdRef = useRef<number | null>(null);
  const lastTickRef = useRef<number>(0);
  // onFrame を ref で持つことで毎レンダで loop を再生成しない
  const onFrameRef = useRef<typeof onFrame>(onFrame);
  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  const stop = useCallback(() => {
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
    setStream((cur) => {
      cur?.getTracks().forEach((t) => t.stop());
      return null;
    });
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setStatus('idle');
  }, []);

  const start = useCallback(async () => {
    setStatus('starting');
    setErrorMessage(null);
    let media: MediaStream | null = null;
    try {
      media = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: 'user' },
        audio: false,
      });
    } catch (e: unknown) {
      const name = (e as { name?: string })?.name ?? '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setStatus('denied');
        setErrorMessage('カメラ許可がありません。ブラウザの設定から許可してください。');
      } else if (name === 'NotFoundError' || name === 'OverconstrainedError') {
        setStatus('error');
        setErrorMessage('カメラが見つかりませんでした。');
      } else {
        setStatus('error');
        setErrorMessage('カメラの開始に失敗しました: ' + String(e));
      }
      return;
    }

    setStream(media);

    // <video> 要素を裏で作って frame を抽出する
    // (UI 側でプレビューする場合は別の <video> に同じ stream を流す)
    const video = document.createElement('video');
    video.srcObject = media;
    video.muted = true;
    video.playsInline = true;
    videoRef.current = video;
    await video.play().catch(() => {
      /* autoplay 失敗時は loop で待つ */
    });

    let landmarker;
    try {
      landmarker = await getFaceLandmarker();
    } catch (e) {
      setStatus('error');
      setErrorMessage('顔解析モデルのロードに失敗しました: ' + String(e));
      stop();
      return;
    }

    setStatus('running');
    lastTickRef.current = 0;

    const loop = () => {
      if (!videoRef.current) return;
      const v = videoRef.current;
      const now = performance.now();
      if (now - lastTickRef.current >= intervalMs && v.readyState >= 2) {
        lastTickRef.current = now;
        try {
          const result = landmarker.detectForVideo(v, now);
          const frame = buildFaceFrame(result, now);
          onFrameRef.current?.(frame);
        } catch {
          // MediaPipe の単発エラーは無視 (次の frame で復帰する)
        }
      }
      rafIdRef.current = requestAnimationFrame(loop);
    };
    rafIdRef.current = requestAnimationFrame(loop);
  }, [intervalMs, stop]);

  // unmount で必ず cleanup (camera を残さない、メモリリーク防ぐ)
  useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) cancelAnimationFrame(rafIdRef.current);
      // setStream 経由ではなく直接 cleanup (state 更新は unmount 中)
      videoRef.current?.srcObject &&
        ((videoRef.current.srcObject as MediaStream).getTracks().forEach((t) => t.stop()));
      videoRef.current = null;
    };
  }, []);

  return { status, stream, errorMessage, start, stop };
}
