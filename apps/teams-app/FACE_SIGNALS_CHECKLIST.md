# Face Signals — Teams Tab 動作チェックリスト (Phase 6)

Helmsman の顔シグナル機能 (MediaPipe FaceLandmarker) を Teams Tab 上で
動かす際の確認手順 + トラブルシュート。Solo モード (通常ブラウザ) で動くことは
unit test + Solo ページで担保済み。**ここでは Teams iframe 特有の制約**を扱う。

## 設計上の前提

ADR-106 / ADR-107 で確定済の方針:

- **WASM / model は self-host** (`/mediapipe/*`)
  - 同一オリジン (Static Web App) → CSP の `connect-src 'self'` / `script-src 'self'`
    で必ず読める
  - CDN (storage.googleapis.com) には依存しない
- **getUserMedia は manifest の `devicePermissions: ["media"]` で許可済**
- **デフォルト OFF**、ユーザが Switch を ON にしてカメラ許可を出した時のみ動く
- **生フレームをサーバーに送らない**、集計値のみ POST

## 実機チェックリスト

Teams Desktop (Mac/Windows) と Teams Web (Edge) の両方で以下を確認する。

### ✅ A. Tab 起動 + AppShell の Teams 検出

1. 会議に Helmsman タブを追加 (SIDELOAD.md 参照)
2. タブを開いた時、AppShell が `inTeamsTab=true` を検出してサイドナビを省略する
3. URL は `?meeting_id=...` で動くこと

### ✅ B. Solo モード表示

1. ボットが派遣されていない状態で MeetingRoom を開く
2. SoloMicCard が表示される
3. SoloMicCard の末尾に **FaceCaptureCard** が見える
4. デフォルトで Switch は OFF (顔シグナル機能 OFF)

### ✅ C. カメラ許可

1. Switch を ON にする
2. Teams が「このアプリにカメラを使わせますか?」と聞いてくる
3. 「許可」を押す
4. プレビュー <video> に自分の顔が映る (mirror = 鏡像)
5. 右上に「📷 ON AIR」赤バッジが点滅する

### ✅ D. MediaPipe ロード成功

1. ブラウザ devtools (F12) を開く (Teams Desktop は Help > Developer Tools)
2. Network タブで `/mediapipe/face_landmarker.task` と `/mediapipe/vision_wasm_*.{js,wasm}` が
   200 で返ってきている
3. Console に MediaPipe のエラーが無い

### ✅ E. 解析が回る

1. 顔を画面に映した状態で、FaceCaptureCard 下部に metric pill が出る
   - `pitch 0.0°` (顔を上下に振ると変化する)
   - `brow 0.XX` (眉を寄せると上がる)
   - `blink 0.XX` (瞬きすると上がる)
2. 「顔が 検出されています ✓」が出る

### ✅ F. サーバー送信

1. devtools Network タブを開いたまま 5 秒以上待つ
2. `POST /meetings/{id}/face-signals` が 4 秒間隔で並ぶ
3. レスポンス body に `{ accepted: true, windows_received: 2, ... }` が入る

### ✅ G. ライブバッジ表示

1. MeetingRoom 右サイドバーに「Face Signals · live」セクションが現れる
2. `confusion XX%` / `engagement XX%` / `nods N` が出る
3. 数値が 4 秒ごとに更新される

### ✅ H. 1-click OFF + cleanup

1. Switch を OFF
2. プレビュー <video> が消える
3. ON AIR バッジが消える
4. Teams のカメラ使用中インジケータが消える (重要 — カメラ track が確実に stop している)
5. Network タブで `POST /face-signals` が止まる

## トラブルシュート

### 症状: Switch を ON にしても何も起きない / プレビューが黒い

- Teams Desktop の場合: macOS の **システム設定 → プライバシーとセキュリティ → カメラ**
  で Teams にカメラ許可が出ているか確認
- 別アプリ (Zoom 等) がカメラを掴んでいないか確認
- ブラウザコンソールに `NotAllowedError` / `NotFoundError` が出ていないか

### 症状: MediaPipe model のロードが遅い (10s+)

- 初回は ~3.6MB の `.task` を fetch する
- SW (Service Worker) で precache されていない (`globIgnores: ['**/mediapipe/**']`)
- 2 回目以降はブラウザ HTTP cache でほぼ即時

### 症状: Teams iframe で CSP error

- 報告例なし (self-host 戦略で同一オリジン化済)
- もし起きたら `connect-src 'self'` を CSP に明示的に入れることを検討
- Teams 側 CSP は manifest の `validDomains` に hostname が入っていれば緩む

### 症状: GET /face-signals/recent が常に空サマリを返す

- 顔シグナルが send されていない (上記 F が通っていない) → カメラを再起動
- buffer がプロセス再起動でクリアされた → 通常運用で 1 度カメラ ON にすれば復帰
- meeting_id が一致していない (URL のものとリクエスト送信時のものが揃っているか)

## 既知の制限

- **Teams モバイル (iOS/Android)**: MediaPipe Web SIMD は対応しているが、Tab iframe 内
  での WebGL 利用が制限されることがある。本機能はデスクトップ / Web 推奨
- **同時カメラ利用**: Teams 会議の自分のカメラと Solo モードの Helmsman カメラを
  同時に ON にすると、片方は黒画になる場合あり (デバイス占有)
- **複数参加者**: 現状 1 タブ = 1 participant_id。多人数で同時に顔シグナルを送る
  シナリオは Phase 6 完了範囲外 (各自のブラウザで個別 opt-in)

## 関連ドキュメント

- ADR-106 (Phase 6 デプロイ範囲): `actions.md` / Zenn §4.10
- ADR-107 (Privacy / Responsible AI): Zenn §11
- 永続化スキーマ: `src/helmsman/models/face_signal.py`
- 集計ロジック: `src/helmsman/services/face_signal_buffer.py`
