/**
 * Phase 6: MediaPipe FaceLandmarker の WASM + モデルを self-host する。
 *
 * Teams Tab の CSP 制限と CDN 依存を回避するため、ビルド時に
 * public/mediapipe/ に取り込んでおく。git には入れない (.gitignore 済)。
 */
import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const PUBLIC_DIR = resolve(ROOT, 'public/mediapipe');
const WASM_SRC = resolve(ROOT, 'node_modules/@mediapipe/tasks-vision/wasm');
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';
const MODEL_PATH = join(PUBLIC_DIR, 'face_landmarker.task');

const WASM_FILES = [
  'vision_wasm_internal.js',
  'vision_wasm_internal.wasm',
  'vision_wasm_module_internal.js',
  'vision_wasm_module_internal.wasm',
  'vision_wasm_nosimd_internal.js',
  'vision_wasm_nosimd_internal.wasm',
];

function ensureDir(p) {
  if (!existsSync(p)) mkdirSync(p, { recursive: true });
}

async function ensureModel() {
  if (existsSync(MODEL_PATH)) {
    const { size } = statSync(MODEL_PATH);
    if (size > 1_000_000) {
      // すでに 1MB 超で存在 → 再取得しない
      return;
    }
  }
  console.log(`[fetch-face-model] downloading ${MODEL_URL}`);
  const res = await fetch(MODEL_URL);
  if (!res.ok) {
    throw new Error(`Failed to download model: ${res.status} ${res.statusText}`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  const { writeFileSync } = await import('node:fs');
  writeFileSync(MODEL_PATH, buf);
  console.log(`[fetch-face-model] saved ${(buf.length / 1_000_000).toFixed(2)}MB`);
}

function copyWasm() {
  if (!existsSync(WASM_SRC)) {
    console.warn(
      `[fetch-face-model] WASM source not found at ${WASM_SRC}. ` +
        `Run \`pnpm install\` first.`,
    );
    return;
  }
  let copied = 0;
  for (const name of WASM_FILES) {
    const src = join(WASM_SRC, name);
    const dst = join(PUBLIC_DIR, name);
    if (!existsSync(src)) continue;
    if (existsSync(dst)) continue;  // 既存ならスキップ (高速化)
    copyFileSync(src, dst);
    copied += 1;
  }
  if (copied > 0) {
    console.log(`[fetch-face-model] copied ${copied} WASM file(s) → public/mediapipe/`);
  }
}

(async () => {
  ensureDir(PUBLIC_DIR);
  copyWasm();
  await ensureModel();
})();
