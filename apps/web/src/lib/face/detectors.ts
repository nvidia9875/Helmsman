/**
 * 顔シグナル検出器 (Phase 6) — 純関数の集合。
 *
 * すべて in/out 同期で副作用なし。集計の状態は呼び出し側 (Aggregator) が
 * リングバッファとして保持し、これらに渡す。
 *
 * - nod: head pitch の時系列を 0.5-2Hz の周期性 + 振幅閾値で検出
 * - confusion: ARKit blendshape の組み合わせ加重
 * - engagement: 顔が見えている割合 + 横向き角度の小ささ
 */
import type { FaceFrame } from '@/lib/face/landmarker';

// ---------- nod ----------

/**
 * pitch の時系列から「うなずき回数」をカウントする。
 *
 * 検出ルール:
 *   - サンプル間で pitch が「上向き→下向き→上向き」の山を 1 回作る (零交差)
 *   - 1 山あたり振幅 (peak-to-trough) が NOD_AMPLITUDE_MIN_DEG 以上
 *   - 連続 2 サンプルだけのスパイクは捨てる (chatter 抑制)
 *
 * 入力 pitches は新しい順でも古い順でも OK (window 全体を走査)。
 */
const NOD_AMPLITUDE_MIN_DEG = 5.0; // 5° 以上の振幅で「うなずき」とみなす
const NOD_AMPLITUDE_MAX_DEG = 25.0; // 大振りすぎは別動作 (首を振る等) として除外

export function countNods(pitches: number[]): number {
  if (pitches.length < 4) return 0;
  // 平均から差分系列を作る (DC 除去)
  const mean = pitches.reduce((s, x) => s + x, 0) / pitches.length;
  const centered = pitches.map((p) => p - mean);

  let nods = 0;
  let lastPeak: number | null = null;
  let lastTrough: number | null = null;
  // 単純な極値検出: 隣 3 点の中央が最大/最小なら極値
  for (let i = 1; i < centered.length - 1; i++) {
    const a = centered[i - 1];
    const b = centered[i];
    const c = centered[i + 1];
    const isPeak = b > a && b > c;
    const isTrough = b < a && b < c;
    if (isPeak) {
      if (lastTrough !== null) {
        const amp = b - lastTrough;
        if (amp >= NOD_AMPLITUDE_MIN_DEG && amp <= NOD_AMPLITUDE_MAX_DEG) {
          nods += 1;
        }
        lastTrough = null;
      }
      lastPeak = b;
    } else if (isTrough) {
      if (lastPeak !== null) {
        const amp = lastPeak - b;
        if (amp >= NOD_AMPLITUDE_MIN_DEG && amp <= NOD_AMPLITUDE_MAX_DEG) {
          nods += 1;
        }
        lastPeak = null;
      }
      lastTrough = b;
    }
  }
  return nods;
}

// ---------- confusion ----------

/**
 * 1 frame の困惑スコア (0.0-1.0)。
 *
 * 加重平均:
 *   - 眉を寄せる (browDownLeft / browDownRight)
 *   - 唇を結ぶ (mouthPressLeft / mouthPressRight)
 *   - 鼻に皺 (noseSneer*)
 *
 * 顔が検出されていない (detected=false) frame は 0 を返す。
 */
export function confusionScore(frame: FaceFrame): number {
  if (!frame.detected) return 0;
  const b = frame.blendshapes;
  const brow = ((b.browDownLeft ?? 0) + (b.browDownRight ?? 0)) / 2;
  const press = ((b.mouthPressLeft ?? 0) + (b.mouthPressRight ?? 0)) / 2;
  const sneer = ((b.noseSneerLeft ?? 0) + (b.noseSneerRight ?? 0)) / 2;
  const score = brow * 0.5 + press * 0.3 + sneer * 0.2;
  return Math.max(0, Math.min(1, score));
}

// ---------- engagement ----------

/**
 * 1 frame の集中度 (0.0-1.0)。
 *
 * - 顔が検出されている (検出失敗時は 0)
 * - 瞬き (eyeBlink) は瞬間的な値、3 frame 程度の窓で見るのが本来。
 *   1 frame 関数では「瞬きしていない時の eye 開度 = 1 - blink」を取る
 * - 視線方向 (eyeLookOut/In) で逸らしを軽くペナルティ
 */
export function engagementScore(frame: FaceFrame): number {
  if (!frame.detected) return 0;
  const b = frame.blendshapes;
  const blink = ((b.eyeBlinkLeft ?? 0) + (b.eyeBlinkRight ?? 0)) / 2;
  const lookOut = ((b.eyeLookOutLeft ?? 0) + (b.eyeLookOutRight ?? 0)) / 2;
  const eyeOpen = 1 - blink;
  // 顔が大きく横を向くと engagement 低下 (±20° で線形ペナルティ)
  const pitchAbs = Math.min(20, Math.abs(frame.headPitchDeg)) / 20;
  const facing = 1 - pitchAbs * 0.3 - lookOut * 0.4;
  return Math.max(0, Math.min(1, eyeOpen * facing));
}

// ---------- aggregator ----------

export interface FaceWindow {
  /** window 開始時刻 (performance.now() 基準、ms) */
  windowStart: number;
  /** この window 内のサンプル数 */
  sampleCount: number;
  /** うなずき回数 (countNods 適用後) */
  nodCount: number;
  /** confusion の平均 */
  confusion: number;
  /** engagement の平均 */
  engagement: number;
  /** 顔が見えていた割合 (detected ratio) */
  faceVisibleRatio: number;
}

/**
 * 直近の frame 列を 1 つの集計窓 (FaceWindow) に畳む。
 *
 * 通常 2 秒 (= 約 20 frame @ 10Hz) を渡す。閾値判定は agent 側で。
 */
export function aggregateFrames(frames: FaceFrame[]): FaceWindow | null {
  if (frames.length === 0) return null;
  const windowStart = frames[0].timestamp;
  const sampleCount = frames.length;

  const pitches = frames.map((f) => f.headPitchDeg);
  const nodCount = countNods(pitches);

  let confusionSum = 0;
  let engagementSum = 0;
  let visibleCount = 0;
  for (const f of frames) {
    confusionSum += confusionScore(f);
    engagementSum += engagementScore(f);
    if (f.detected) visibleCount += 1;
  }

  return {
    windowStart,
    sampleCount,
    nodCount,
    confusion: confusionSum / sampleCount,
    engagement: engagementSum / sampleCount,
    faceVisibleRatio: visibleCount / sampleCount,
  };
}
