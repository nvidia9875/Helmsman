/**
 * MediaPipe FaceLandmarker wrapper (Phase 6 マルチモーダル)。
 *
 * 設計判断:
 *   - WASM / model は self-host (/mediapipe/...) で CDN 依存と
 *     Teams Tab CSP の不確実性を回避 (scripts/fetch-face-model.mjs で取得)
 *   - dynamic import で初期 bundle に影響を出さない (~5MB の WASM/model 込み)
 *   - VIDEO mode で 10Hz サンプリング (約 100ms 間隔) を想定
 *   - 78 ARKit blendshapes + transformation matrix で head pose も取れる
 */
import type {
  FaceLandmarker as FaceLandmarkerType,
  FaceLandmarkerResult,
} from '@mediapipe/tasks-vision';

const WASM_BASE_PATH = '/mediapipe';
const MODEL_PATH = '/mediapipe/face_landmarker.task';

let _landmarkerPromise: Promise<FaceLandmarkerType> | null = null;

export interface FaceFrame {
  /** ARKit 52 blendshapes — keys に "browDownLeft" 等の名前が入る */
  blendshapes: Record<string, number>;
  /** Head pose (transformation matrix → Euler) — pitch (頷きで動く軸) のみ抽出 */
  headPitchDeg: number;
  /** Frame 時刻 (performance.now()) */
  timestamp: number;
  /** 顔が検出されたか (検出失敗時は全フィールド 0) */
  detected: boolean;
}

/**
 * FaceLandmarker を 1 度だけ初期化し、以降は同一インスタンスを返す。
 *
 * MediaPipe の vision tasks は大きいので、最初の呼び出しでだけ
 * dynamic import + WASM load を行う。
 */
export async function getFaceLandmarker(): Promise<FaceLandmarkerType> {
  if (_landmarkerPromise) return _landmarkerPromise;

  _landmarkerPromise = (async () => {
    const { FaceLandmarker, FilesetResolver } = await import('@mediapipe/tasks-vision');
    const filesetResolver = await FilesetResolver.forVisionTasks(WASM_BASE_PATH);
    return FaceLandmarker.createFromOptions(filesetResolver, {
      baseOptions: {
        modelAssetPath: MODEL_PATH,
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      outputFaceBlendshapes: true,
      outputFacialTransformationMatrixes: true,
      numFaces: 1,
    });
  })();

  return _landmarkerPromise;
}

/**
 * 4x4 row-major transformation matrix から pitch (頷き軸) を Deg で取得。
 * MediaPipe の matrix は column-major で flatten された length=16 の配列。
 *
 * pitch = atan2( -m[9], sqrt(m[8]^2 + m[10]^2) )
 *   ※ m[i] は column-major flatten: m[col*4 + row]
 *   ※ ここでは row 2, col 1 → m[6] と row 2, col 0/2 → m[2], m[10]
 *
 * 参考: https://en.wikipedia.org/wiki/Rotation_matrix#General_3D_rotations
 */
export function extractHeadPitchDeg(matrix: number[]): number {
  if (matrix.length !== 16) return 0;
  // column-major: m[col*4 + row]
  // pitch = arcsin(-r20) where r20 = m[col=0, row=2] = matrix[2]
  // (MediaPipe convention: y軸が上、x軸が右、z軸が前)
  const r20 = matrix[2];
  const clamped = Math.max(-1, Math.min(1, -r20));
  return (Math.asin(clamped) * 180) / Math.PI;
}

/**
 * MediaPipe の出力を FaceFrame に正規化する純関数。
 * Result が空 (顔未検出) の場合は detected:false で全 0 を返す。
 */
export function buildFaceFrame(
  result: FaceLandmarkerResult,
  timestamp: number,
): FaceFrame {
  const blendshapesCat = result.faceBlendshapes?.[0]?.categories ?? [];
  const matrix = result.facialTransformationMatrixes?.[0]?.data;

  if (blendshapesCat.length === 0) {
    return { blendshapes: {}, headPitchDeg: 0, timestamp, detected: false };
  }

  const blendshapes: Record<string, number> = {};
  for (const c of blendshapesCat) {
    blendshapes[c.categoryName] = c.score;
  }

  const headPitchDeg = matrix
    ? extractHeadPitchDeg(Array.from(matrix))
    : 0;

  return { blendshapes, headPitchDeg, timestamp, detected: true };
}
