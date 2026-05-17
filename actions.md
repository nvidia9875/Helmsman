# Helmsman アクション一覧（5/16 → 6/1 提出）

> このファイルは進捗追跡の single source of truth。
> 完了したら `[ ]` → `[x]` に書き換えるだけ。
> 不要になった項目は ~~取り消し線~~ にして残置 (履歴として価値あり)。
>
> **🌐 2026-05-16 ピボット**: Teams Apps SDK を外し、**ブラウザ完結の Web アプリ**として実装する設計に変更。詳細: [pivot-web.md](./pivot-web.md)
>
> **🤖 2026-05-17 二次ピボット**: ACS Call Automation で「Helmsman bot が Teams 会議に参加者として join し、音声を取り、必要なら TTS で介入を喋り返す」モデルに切替。Web フロントは「ホスト/監視者用ダッシュボード」専任に。**PWA / モバイル STT / 声紋識別 / Hybrid マルチデバイスは不要に**。新セクション [8.5.F Teams Bot](#85f-teams-bot-acs-call-automation--speech-sdk---新規) 参照。
>
> **📅 2026-05-17 三次ピボット (UX 修正)**: 「Helmsman で新規会議を作る」UI を撤廃。Teams カレンダーに既に登録されている会議の URL を貼って Bot を派遣するフローに変更。Landing → Dispatch → Mission Control。`StartMeetingRequest.teams_meeting_url` で 1-shot 派遣。ゴール任意化 (空なら「監視のみ」モード)。

## 全体進捗

- **提出締切**: 2026-06-01 (月) 21:00 目標 / 23:59 必達
- **審査期間**: 6/2 - 6/9（アプリ稼働維持必須）
- **進出通知**: 6/10
- **最終審査会**: 6/18

### 北極星マイルストーン

- [x] **D-9 (5/24 日)**: Web MVP（Goal Decomposer + Coverage Tracker + 全 8 agents + Arbiter + Sidebar UI + 介入カード）**5/17 早朝に前倒し達成** ✨
- [x] **D-6 (5/27 水)**: 介入レイヤー L1/L2 + Decision Capture + Arbiter **完成済** ✨
- [ ] **D-3 (5/30 土)**: PWA + 声紋 + マルチデバイス同期
- [ ] **D-2 (5/31 日)**: L3 Speak + Container Apps デプロイ + デモ動画完成
- [ ] **D-1 (6/1 月)**: Zenn 記事公開 + 提出

---

## Day 0 — 5/16 (土) 今日の TODO

セットアップ・申請・調整の日。

- [x] **#1** Microsoft アカウント作成 + ¥30,000 クレジット獲得
- [x] **#2** Azure サブスクリプション + 予算アラート設定
  - [x] 予算 `helmsman-monthly-budget` 作成（¥22,500）
  - [x] 50% / 80% / 100% の3段階アラート設定
- [x] ~~**#3** Microsoft 365 Developer Program 登録~~ **不要に変更**（Web ピボットにより M365 テナント不要に）
- [x] **#4** Azure OpenAI Service 利用 ⚠️
  - [x] リソース作成（aoai-helmsman-dev / East US 2）
  - [x] **gpt-5.4** デプロイ（30K TPM, 高品質推論用）
  - [x] **gpt-5.4-mini** デプロイ（100K TPM, 高頻度用）
  - [x] **gpt-realtime-1.5** デプロイ（10 RPM, L3 Speak 用）
  - [x] `.env` に API キー + エンドポイント保存
  - [x] uv run で動作確認スクリプト成功
- [x] ~~**#5** Hackathon Discord サーバー参加 + 質問投下~~ **見送り**（一人で進める）
- [x] **#6** GitHub リポジトリ `Helmsman` 作成（public/MIT）
  - [x] `git init` + 初回 commit (`0eab582`)
  - [x] Remote 設定 + main push 完了
  - [x] Description + Topics 設定（agentic-ai, azure-openai, copilot-studio, microsoft, hackathon 等）
  - [x] URL: https://github.com/nvidia9875/Helmsman
  - [ ] CI/CD ワークフロー（Container Apps 自動デプロイ）← Day 1 で実施
- [x] **#7** 開発ツール一式インストール
  - [x] Azure CLI 2.86.0
  - [x] Azure Functions Core Tools 4.10.0
  - [x] Node 20.20.0（既存）→ 24 LTS は将来切替
  - [x] uv 0.11.7（既存）
  - [x] **Python 3.14.4**（3.12 から最新化）
  - [x] Bicep 0.43.8
  - [x] プロジェクト初期化（pyproject.toml + 全依存最新化 + .venv + 完全 src/ レイアウト）
- [x] ~~**#8** 友人 4 名にテスト会議協力打診~~ **見送り**（ソロテストに切替）
- [x] **#9** Bicep 雛形作成
  - [x] `infra/main.bicep` + 7 モジュール（monitoring/storage/cosmosdb/signalr/speech/keyvault/containerapps）
  - [x] `infra/main.parameters.json` で環境変数
  - [x] `az deployment group create` で1コマンドデプロイ実行済
- [x] **#10** カレンダーにフェーズ別締切ブロック（自分で対応）
  - 5/24（Web MVP 完成期限）
  - 5/27（マルチデバイス同期完成期限）
  - 5/30（デモ撮影日）
  - 6/1 21:00（提出ブロック）

### ~~Discord 投下用質問~~（見送り・参考までに残置）

<details>
<summary>もし詰まったときに公式サポート (zenn-support@classmethod.jp) に投げる質問テンプレ</summary>

```
1. Copilot Studio Multi-Agent (Public Preview) のハッカソンでの利用制約は？
2. Azure OpenAI の gpt-4o-realtime は東日本リージョンで申請可能？
3. 6/2-6/18 審査期間中のデプロイ要件（SLA・認証方式）の具体は？
4. デモ動画の長さ・形式の上限は？
5. 個人部門の提出フォームは何項目あるか、事前共有可能か？
```

</details>

---

## Day 1 — 5/17 (日) Azure リソース構築 ✅ 5/17 早朝に Bicep 一発で完了

Bicep で一気にデプロイ。

- [x] **Az-1** リソースグループ `rg-helmsman-dev` 作成
- [x] **Az-2** Azure OpenAI デプロイ（**gpt-5.4 / gpt-5.4-mini / gpt-realtime-1.5** に最新化）
- [x] **Az-3** Azure AI Speech リソース作成（Standard, westus2）
- [x] **Az-4** Azure Cosmos DB (Serverless) 作成
  - [x] DB `helmsman`
  - [x] Containers: `meetings` / `participants` / `voiceprints` / `interventions`（snake_case partition key）
- [x] **Az-5** Azure Container Apps Environment 作成（scale-to-zero）
- [ ] ~~**Az-6** Azure Functions Plan 作成~~ **見送り**（VM クォータ問題、Container Apps で代替）
- [x] **Az-7** Azure SignalR Service (Free_F1, Serverless mode) 作成
- [x] **Az-8** Azure Communication Services 作成 ✅ TB-A1 で `infra/modules/acs.bicep` 経由デプロイ済
- [x] **Az-9** Azure AI Search (Basic) 作成 ✅ DOC-3 で Free SKU デプロイ済 (`infra/modules/aisearch.bicep`)
- [x] **Az-10** Azure Key Vault 作成 + シークレット集約
- [x] **Az-11** Application Insights + Log Analytics 作成
- [ ] ~~**Az-12** Microsoft Entra ID アプリ登録（SPA タイプ）~~ ← 提出後 Phase F (dev は X-Helmsman-Key 共有秘密 + organizer_id クエリで運用)
  - [ ] ~~`client_id` 取得~~
  - [ ] ~~Graph API スコープ: User.Read~~
- [x] **Az-13** GitHub Actions に Azure 認証（Service Principal）追加 ✅ F-3 で完了 (Container Apps 自動デプロイ + SWA)
- [x] **Az-14** Container Apps への hello world デプロイ確認（placeholder image で稼働中）

---

## Day 2-5 — Backend Core ✅ 5/17 早朝に全部完了

8 agents + FastAPI + Cosmos + Arbiter、E2E でgpt-5.4 から介入配信まで稼働確認。

- [x] **BE-1** Goal Decomposer 実装（gpt-5.4 / JSON 構造化）
- [x] **BE-2** Coverage Tracker 実装（gpt-5.4-mini / 4 状態遷移）
- [x] **BE-3** Cosmos DB スキーマ + 接続コード（async, snake_case partition keys）
- [x] **BE-4** FastAPI 雛形（main + routers/health + routers/meetings）
- [x] **BE-5** Cosmos DB 書き込み・読み込み動作確認 ✓
- [x] **BE-6** Time Keeper 実装（rule-based, LLM 不要で高速）
- [x] **BE-7** Steering Agent 実装（gpt-5.4-mini / off-topic 検知 → 自然な復帰提案）
- [x] **BE-8** 各エージェントのユニットテスト ✅ T-4/T-5/T-6 で 10+ 件、合計 66 件パス
- [x] **BE-9** Azure Speech リアルタイム STT 統合 ✅ TB-B1/B2/B4 で WebSocket + Speech SDK 連携完了
- [x] **BE-10** 発言ストリームパイプライン（`/tick` で全 agent 並列実行）
- [x] **BE-11** Decision Capture 実装（gpt-5.4 / 決定の構造化）
- [x] **BE-12** Quiet Activator 実装（gpt-5.4-mini / z-score ベース活性化）
- [x] **BE-13** Dissent Surface 実装（gpt-5.4 / 同意連鎖検知）
- [x] **BE-14** 各エージェントのユニットテスト ✅ BE-8 と同時に完了 (T-4〜T-6)
- [x] **BE-15** Intervention Arbiter 実装（新規性の核）
  - [x] レート制限 / Density / Authority gradient / Mode-conditional の全フィルタ
  - [x] L1 / L2 / L3 level 判定ロジック
- [x] **BE-16** 統合テスト（モック会議シナリオ）✅ T-9 で FastAPI TestClient + dispatch flow 8 件パス
- [x] **BE-17** 6+1 エージェント全部 + Arbiter のエンドツーエンド統合 ✓ 動作確認済

---

## Day 6-7 — Web フロントエンド ✅ 5/17 早朝に完了

- [x] **FE-1** Vite 8 + React 19 + TypeScript 5.9 プロジェクト（`apps/web/`）
- [x] **FE-2** Fluent UI v9（dark theme）セットアップ
- [x] **FE-3** ルーティング（`/` `/new` `/m/:roomId` `/m/:roomId/join`）
- [ ] ~~**FE-4** Microsoft Entra ID Web 認証（MSAL.js）統合~~ ← 提出後 Phase F (dev/prod とも X-Helmsman-Key + localStorage の userId で運用中)
- [x] **FE-5** サイドバー基本レイアウト（ゴール / 論点 / 状態バッジ 4色）
- [x] **FE-6** ランディング `/` + 会議室作成 `/new` の UI
- [x] **FE-7** 会議室 `/m/:roomId` の UI（サイドバー + 共有 QR + 介入カード）
- [x] **FE-8** 参加フロー `/m/:roomId/join`（QRコード生成 + リンクコピー）
- [ ] **FE-9** Azure SignalR クライアント統合 ← polling で代用中（5/27 まで）
- [x] **FE-10** ブラウザマイク取得（**Web Speech API でフォールバック実装**, WebRTC は後日）

**達成状況**: Web アプリでゴール入力 → 会議室作成 → 発言追加 → Helmsman 実行 → 介入カード表示、が動く ✓

---

## Day 8 — 5/24 (日) 🎯 フェイルセーフ MVP 完成日

- [x] **MVP-1** E2E テスト: 会議作成 → 6+1 Agent + Arbiter 動作 ✓（5/17 早朝に達成）
- [x] **MVP-2** ソロテスト（curl ベースで本物の gpt-5.4 動作確認済み）
- [x] **MVP-3** スクリプト化した模擬発言で動作確認（off-topic 検知 + L2 配信成功）
- [ ] ~~**MVP-4** Microsoft Planner 連携 or 手元 export 機能~~ ← 提出後 Phase F (Microsoft Graph API スコープ追加と PM 系外部連携は scope crawler)

> ✅ **MVP 達成済**。次フェーズ (Day 8.5) で安定性 + 継続会議 + 文書グラウンディングを追加。

---

## ✨ Day 8.5 追加マイルストーン (5/17-5/19 で実施)

### 8.5.A 安定性 + テスト整備

- [x] **T-1** pytest + pytest-asyncio セットアップ (`pyproject.toml`)
- [x] **T-2** Arbiter のルールベーステスト 16 件 (`tests/test_arbiter.py`)
- [x] **T-3** TimeKeeper のルールベーステスト 4 件 (`tests/test_time_keeper.py`)
- [x] **T-4** Goal Decomposer ユニットテスト (mock LLM、3 件 in `test_agents.py`)
- [x] **T-5** Coverage Tracker ユニットテスト (mock LLM、2 件 + DOC-5 document_reference 検証)
- [x] **T-6** Steering / Decision / Quiet / Dissent ユニットテスト (mock LLM、5 件 + DOC-6 矛盾警告検証)
- [x] **T-7** Meeting / Topic Pydantic モデルテスト 7 件 (`tests/test_models.py`)
- [x] **T-8** Cosmos リポジトリの async モックテスト (`tests/test_repositories.py` 7 件、ContainerProxy AsyncMock 化 + query parameter 検証)
- [x] **T-9** FastAPI 統合テスト (`tests/test_api_smoke.py` 8 件、TestClient + dispatch flow 含)
- [x] **T-10** Frontend vitest セットアップ (`vitest.config.ts` + jsdom + @testing-library、OnboardingSteps + api client URL 組み立て 計 6 件)
- [x] **T-11** GitHub Actions test workflow (`.github/workflows/test.yml`、pytest + ruff + tsc/vite build + vitest を並列実行)

### 8.5.B 会議継続性（前回からの続き）🌟 新規 ✅ 2026-05-17 完了

- [x] **C-1** Meeting model に `parent_meeting_id` + `series_id` フィールド追加 (model 既存 / API 拡張済)
- [x] **C-2** Meeting Repository に `list_by_organizer` / `list_series` メソッド
- [x] **C-3** ランディングに「最近の会議」一覧 + 「続きから」ボタン (`RecentMeetings.tsx`)
- [x] **C-4** `/new?parent={id}` で前回会議バナー + 引き継ぎ論点プレビュー
- [x] **C-5** 引き継ぎ時：未解決論点を `GoalDecomposer.run(inherited_topics=...)` で context 注入
- [x] **C-6** サイドバーに「前回からの引き継ぎ事項」セクション + シリーズバッジ

### 8.5.C 文書ベース・ファシリテーション 🌟 新規 (2026-05-17 着手)

- [x] **DOC-1** Azure Blob Storage `documents` コンテナ (Bicep) + アップロードエンドポイント
- [x] **DOC-2** Azure AI Document Intelligence (Bicep F0) + 抽出サービス (pypdf フォールバック付き)
- [x] **DOC-3** Azure AI Search (Bicep Free SKU) + ベクトル索引 + chunk アップサート
- [x] **DOC-4** Goal Decomposer に `document_excerpts` 引数 + `POST /meetings/{id}/redecompose`
- [x] **DOC-5** Coverage Tracker に document_reference 出力 (例:「提案書 §3 採用要件」) + 軽量 RAG (`fetch_document_excerpts_simple`)
- [x] **DOC-7** MeetingRoom にドラッグ&ドロップ `DocumentUpload` コンポーネント
- [x] **DOC-8** サイドバーに「📎 参考文書」セクション + Topic カードに `document_reference` キャプション
- [x] **DOC-6** Decision Capture が `contradiction_warning` を出力 → 介入文に「⚠️ 文書と矛盾の可能性」プレフィックス + 構造化ログ
- [x] **DOC-9** Sidebar 文書チップに「🔊 読み上げ」ボタン → `POST /meetings/{id}/bot/speak` で TTS 経由会議に発話

### 8.5.D 審査基準ブラッシュアップ

**【ビジネスインパクト】**
- [x] **B-1** 1 会議あたりの ROI 計算を README に明記 (3 ペルソナ別 13-21× ROI 表)
- [x] **B-2** ユーザーペルソナ 3 つ書く (PdM 田中 / マネジャー 佐藤 / CTO 山田)
- [ ] **B-3** デモ動画に "ビフォアアフター" 数値 — フレームワーク 5 指標は README 明記済、実測は Phase E (TB-E2 以降)

**【アプローチの有効性】**
- [x] **A-1** Multi-Agent 並列実行のシーケンス図を README に (Mermaid sequence、ACS join → STT → 8 agents → Arbiter → L3 TTS)
- [x] **A-2** Arbiter のアルゴリズム解説 (6 段階フィルタ + Density-aware silence + Authority gradient のフローチャート)
- [ ] **A-3** Semantic Kernel + Azure AI Agent Service の正式採用 — 提出後 Phase F

**【完成度・実現性】**
- [x] **F-1** エラーハンドリング強化 (Goal Decomposer 失敗時は空 topics で会議継続、Redecompose 失敗時は既存 topics 維持、全 unhandled exception を 500 JSON + 構造化ログで統一)
- [x] **F-2** Application Insights 構造化ログ (`setup_azure_monitor()` で azure-monitor-opentelemetry を lifespan wire、FastAPI/httpx/asyncio 自動 instrumentation、prod は JSONRenderer)
- [x] **F-3** Container Apps 本番デプロイ + 審査員 URL (Bicep + GitHub Actions + Static Web Apps + DEPLOY.md 完備)
- [x] **F-4** コスト試算表を README に (1 会議 ~$0.66、月 50 会議で ~$48、テーブル付き)
- [x] **F-5** API 認証 (`X-Helmsman-Key` ヘッダー + `HELMSMAN_REQUIRE_AUTH` env でトグル、CORS を dev/prod で分岐 + `cors_allowed_origins` env 上書き可能、Entra ID 化は提出後 Phase F)

### 8.5.E コストダッシュボード 🌟 新規 (2026-05-17 着手)

毎朝の Azure Cost Analysis 監視を Web アプリ内に内製。会議単位の LLM コストを可視化。

- [x] **COST-1** `LLMAgent._chat()` で `usage` を捕捉 (`src/helmsman/agents/base.py`)
- [x] **COST-2** Azure OpenAI 価格表 + コスト計算 (`src/helmsman/core/pricing.py`)
- [x] **COST-3** Meeting に `usage` フィールド追加 + tick で自動集計
- [x] **COST-4** `GET /meetings/{id}/usage` エンドポイント
- [x] **COST-5** MeetingRoom にコストカード表示（合計 + agent 別 + token / 呼び出し数）
- [x] **COST-6** ユニットテスト 5 件 (`tests/test_usage.py`)
- [x] **COST-7** ランディング 30 日コストサマリーカード (累計 / 平均 / 日別スパーク bar、`GET /meetings/usage/summary`)

### 8.5.F Teams Bot (ACS Call Automation + Speech SDK) 🌟 新規 (2026-05-17 着手)

ハッカソンの差別化キラー機能、かつ Microsoft Agent Hackathon の本命提出。
Helmsman bot を Teams 会議に「Helmsman 🧭 (External)」として join → 音声取得 → 8 agents → TTS で介入。

**Phase A: Skeleton (Teams 不要で実装可能、deploy 済)**
- [x] **TB-A1** ACS Bicep モジュール (`infra/modules/acs.bicep`、Japan data location) + Bot に必要な env vars 注入
- [x] **TB-A2** Python ACS SDK (`azure-communication-callautomation`) + Speech SDK 設定
- [x] **TB-A3** `services/teams_bot.py` — `invite_bot_to_teams_meeting()` + `hangup_bot()` + operation_context 形式
- [x] **TB-A4** `POST /meetings/{id}/bot/invite` / `POST /meetings/{id}/bot/leave` / `POST /bot/callback` (ACS webhook handler with EventGrid validation handshake)
- [x] **TB-A5** Meeting model に `teams_meeting_url` / `bot_call_connection_id` / `bot_status` / `bot_last_event_at` 追加
- [x] **TB-A6** ユニットテスト 4 件 (operation_context parser)

**Phase B: Real-time STT pipeline (Teams 不要で実装可能、deploy 済)**
- [x] **TB-B1** `services/realtime_transcription.py` — Speech SDK の sync callback を asyncio queue で橋渡し
- [x] **TB-B2** `services/call_buffer.py` — call_connection_id ごとの session registry + consumer/ticker task
- [x] **TB-B3** `services/call_tick.py` — bot 経由で内部 tick (5 agents + Arbiter) を直接呼び出す
- [x] **TB-B4** `/bot/media-stream/{meeting_id}/{organizer_id}` WebSocket route — ACS の AudioMetadata + AudioData JSON frame 受信
- [x] **TB-B5** Dockerfile に Speech SDK の native deps (libssl3 / libasound2 / libgomp1) 追加
- [x] **TB-B6** Container App `minReplicas: 1` (call 中の WebSocket 維持)

**Phase C: TTS playback + L3 voice intervention (要 Teams テナント) — コード完成、smoke 待ち**
- [x] **TB-C1** Bidirectional media stream で TTS audio chunk を会議に送信 (`services/tts.py:play_pcm_into_websocket`)
- [x] **TB-C2** Azure Speech TTS で日本語介入 (`ja-JP-NanamiNeural`、`Raw16Khz16BitMonoPcm`)
- [x] **TB-C3** Arbiter が L3 を選んだら `_run_tick` から TTS 再生フック発火 (`call_tick.py`)
- [ ] **TB-C4** Barge-in 制御 (参加者が喋り始めたら TTS 即停止) ← smoke test 後に調整
- [x] **TB-C5** UI に「🔊 音声で介入する」L2 → L3 昇格ボタン ✅ InterventionFeed に追加 (Bot in_call 時のみ enable、発話済み/エラー状態を inline 表示、`POST /meetings/{id}/bot/speak` 経由)

**Phase D: Frontend invite UI + UX 仕上げ — ヒーロー + 介入 feed + オンボーディング完備**
- [x] **TB-D1** MeetingRoom UI 改修: QR コード → Teams 会議 URL 貼り付けフォーム + 「🤖 Bot を招待」ボタン (`TeamsBotInvite.tsx`)
- [x] **TB-D2** Sidebar bot status badge + ヒーロー `BotMissionCard` (gradient + halo + 経過時間バー + 発言数)
- [x] **TB-D3** リアルタイム発言ログ (`LiveTranscript.tsx`、3 秒 polling)
- [x] **TB-D5** Onboarding 4 ステップ (`OnboardingSteps.tsx`、idle 時のみ表示) ← 新規
- [x] **TB-D6** Intervention Feed (`InterventionFeed.tsx`、L1/L2/L3 色分け) + Backend `Meeting.delivered_interventions` 永続化 (両 tick パス) ← 新規
- [x] **TB-D7** 補助カード (Cost/Docs) は bot active 時に折りたたみ ← 新規
- [x] **TB-D4** Teams app manifest 雛形 (`apps/teams-app/manifest.json` schema 1.17 準拠 + 設計判断 README、アイコン/Bot Framework 登録は提出後)
- [x] **TB-D8** UX ピボット: 「会議を作る」UI 撤廃。Teams カレンダーの既存会議 URL を貼って 1-shot で派遣する Dispatch フローに ← 新規
- [x] **TB-D9** Mission Control branding + `GoalEditor` Dialog (派遣後にゴール後付け可能)、Backend `POST /meetings/{id}/set-goal` ← 新規

**Phase E: User 側準備 + Smoke test (5/19 以降)**
- [-] **TB-E1** USER: 5/19 月 Teams Essentials trial 契約 (5/17 夜 sign-up 済、Microsoft 審査 ~2 営業日 pending)
- [ ] **TB-E2** Teams 会議を作って実 URL で派遣 smoke test
- [ ] **TB-E3** STT 認識精度の手動評価 (日本語 30 分会議で何 % 拾えるか)
- [ ] **TB-E4** L3 TTS の声質 / レイテンシ評価
- [ ] **TB-E5** USER: 6/17 までに trial 解約 (¥7,188 自動課金回避)

### 8.5.G ポジショニング (Microsoft Teams Facilitator との差別化) 🌟 新規 (2026-05-17 着手)

Microsoft Teams ネイティブ Facilitator (Copilot エージェント) との関係を明確化。

- [x] **POS-1** README に「Microsoft Teams Facilitator との違い」セクション追加 (11 行比較表 + 利用ケース整理 + 補完関係明記)
- [x] **POS-2** Landing にバッジ (Copilot ライセンス不要 / 外部参加者として join / AI 音声介入 / OSS) + Facilitator 公式ドキュへの直リンク + README §Facilitator との違い へのアンカー
- [ ] **POS-3** Zenn 記事 / デモ動画に「Facilitator は補完関係」スライド追加 ← Z-1〜Z-4 と一緒に
- [ ] **POS-4** A-3 Semantic Kernel 採用 (提出後 Phase F、SK の Agent Framework 経由で同じ 8 agents を動かす書き換え)

### 8.5.I 会議グループ + 書類管理 🌟 新規 (2026-05-17 完了)

「会議をグループ化して書類を共有」のユーザー要求に応える。書類は **会議 or グループ** どちらにも紐付け可能。グループ書類は配下全会議の AI tick / set-goal / redecompose の RAG に自動マージ。

- [x] **GRP-1** Cosmos `groups` (partition `/organizer_id`) + `group_documents` (`/group_id`) コンテナ追加 (`infra/modules/cosmosdb.bicep`)
- [x] **GRP-2** `MeetingGroup` model + `GroupRepository` + `GroupDocumentRepository`
- [x] **GRP-3** Document model に `scope` / `group_id` / `organizer_id` 追加 (Pydantic validator で「meeting_id or group_id 必須」)
- [x] **GRP-4** Pipeline 分割: `ingest_meeting_document` / `ingest_group_document` 共通 `_process_document`
- [x] **GRP-5** Blob サービス拡張: `delete_document_blob` + `generate_download_sas_url` (15分有効 SAS)
- [x] **GRP-6** `/meetings/{id}/documents/{did}` DELETE + `/{did}/download` SAS 発行エンドポイント
- [x] **GRP-7** `/groups` ルーター: CRUD + `/{id}/meetings/{mid}` attach/detach + group documents upload/list/delete/download
- [x] **GRP-8** RAG (`fetch_document_excerpts_simple` / `retrieve_excerpts_for_goal`) を group docs と合流 + `[GROUP]` プレフィックス
- [x] **GRP-9** Azure AI Search index に `group_id` フィールド追加 + `meeting_id eq X or group_id eq Y` OR フィルタ
- [x] **GRP-10** tick / set-goal / redecompose に `meeting.group_id` を伝搬 (AI が方向判断時にグループ書類も参照)
- [x] **GRP-11** Web: `DocumentUpload` を scope-aware に再構成 + 書類ごと **削除 + プレビュー (SAS)** ボタン
- [x] **GRP-12** Web: MeetingRoom の DocumentUpload を Accordion から**メインパネル**に昇格 (派遣フローで目に入る)
- [x] **GRP-13** Web: `/groups` 一覧 + 作成 / `/groups/:id` 詳細 (共有書類 + メンバー会議 + 削除) ページ
- [x] **GRP-14** Web: `GroupAttachment` コンポーネントで MeetingRoom 内グループ所属切替
- [x] **GRP-15** Web: CreateMeeting (Dispatch) にグループ選択ドロップダウン
- [x] **GRP-16** Web: AppShell に Groups ナビアイテム + breadcrumbs / topbar 検索バー + ユーザー名表示を削除
- [ ] **GRP-17** 起動後 smoke test: 新 Cosmos コンテナ作成 (Bicep 再デプロイ) + Search index 更新 (`ensure_index()` で自動) ← TB-E2 と同じタイミングで

### 8.5.H UI ブラッシュアップ (Linear/Vercel 風ミニマル) 🌟 新規 (2026-05-17 着手)

「ダサい」と user 指摘 → 装飾削減 + 単色化 + flat 化。

- [x] **UI-1** Foundation: `helmsmanDarkTheme` (Fluent token 30 件 override) + `global.css` (Inter font + Linear 風 scrollbar) + 共通 primitives (`Section` / `Pill` / `StatusDot` / `LevelBar`)
- [x] **UI-2** Mission Control 再構成: `BotStatusStrip` (110px gradient hero → 44px flat strip) / `InterventionFeed` 大改修 (LevelBar + mono timestamp) / `LiveTranscript` slim / `Sidebar` 320px の論点専用 / 下部 Tools accordion / `OnboardingSteps` 1 行化
- [x] **UI-3** Landing + Dispatch: hero shrink to 1 CTA + 4 Pill バッジ / Facilitator 2 列比較 / Dispatch を 560px column + ゴール&モード を accordion 化
- [x] **UI-4** 残コンポーネント flatten: `TeamsBotInvite` → Section、`CostCard` chrome 抜きに / 装飾絵文字撤去 / vitest fix
- [x] **UI-5** (2026-05-17) Dashboard shell + 全幅化 (Aavenir 参考、frontend-design skill 適用):
  - **Foundation**: `global.css` を Mission Control Terminal 化 (CSS 変数 `--bg-0..3` / `--border-hairline` / `--text-1..4` / `--accent #5b8def` + JetBrains Mono import + scanlines/fade-rise/skeleton utilities + 2px focus-visible ring) / `theme.ts` を新トークンに同期
  - **Primitives 追加**: `Kpi` + `KpiRow` (mono numerics + tabular-nums) / `Skeleton` (animated placeholder) / `AreaChart` (inline SVG, no lib)
  - **AppShell**: 64px 左 rail (3 セクション: Overview/Dispatch・Sessions/Analytics・Docs/Settings/Sign out) + 52px topbar (breadcrumbs / search / status pill + user) + mobile bottom nav <720px + 36px gradient brand mark (アプリ内で唯一の gradient)
  - **Landing**: hero (1.4fr+1fr、44px headline + 2 CTA + 4 status pill + Facilitator 比較カード) + KPI row (Sessions/LLM cost/Avg/Agents) + 2 panel (Cost trend AreaChart + Top agents) + `RecentMeetings` を `<table>` 化 (UPPERCASE mono 列見出し / hover 行 / pulsing dot)
  - **Mission Control**: 1fr+320px 全幅 grid / `MISSION CONTROL · session` eyebrow + 24px title + meta inline / `BotStatusStrip` を gradient + scanlines + beacon でリブランド (Elapsed/Remaining/Utterances 3 metric col) / 5 列 KPI / `InterventionFeed` を fade-rise + mono timestamp + agent UPPERCASE + LevelBar / `LiveTranscript` を 72px ts grid + auto-scroll + idle empty state / `Sidebar` を mono section header + topic count + legend / loading skeleton 5 件
  - **Dispatch**: 1.4fr+1fr 2 列 (form / preview) / **「あなたの表示名」→「AI ファシリテーター名」** に rename + default `Helmsman` + placeholder `例: Helmsman` + 「参加者には Helmsman 🧭 として表示されます」hint / 右ペインに 4 step preview + Summary grid (Facilitator/Teams URL/Mode/Duration/Goal)
  - **残コンポーネント polish**: `TeamsBotInvite` / `CostCard` / `OnboardingSteps` / `DocumentUpload` を新トークンに揃える (UPPERCASE mono section header + hairline border + dropzone hover が `--accent`)
  - **Build/Test**: `npm run build` ✅ / `npm test` 6 passed
  - **commit**: `b3d2b97` (foundation+shell) / `48ea796` (landing) + 続く 2 commit (mission control + dispatch / polish)

---

## ~~Day 9 — 5/25 (月) PWA 化 + モバイル対応~~ ❌ 不要 (Teams Bot ピボットにより)

> Bot が Teams 会議に直接 join するモデルでは、参加者はそのまま Teams クライアントを使う。
> 自前 PWA でマイクを取る必要がない。Helmsman フロントは「ホスト/監視者用ダッシュボード」専任。

- [ ] ~~**PWA-1** Web アプリの PWA 対応（manifest.json + Service Worker）~~
- [ ] ~~**PWA-2** モバイル UI 最適化（タッチ操作・縦画面対応）~~
- [ ] ~~**PWA-3** Web Push 通知（介入カードを通知として配信）~~
- [ ] ~~**PWA-4** スマホブラウザでのマイク取得確認（iOS Safari / Android Chrome）~~
- [ ] ~~**PWA-5** QR コード生成 + スマホでスキャン → 会議参加フロー~~

---

## ~~Day 10 — 5/26 (火) 声紋識別~~ ❌ 不要 (Teams Bot ピボットにより)

> Teams 会議参加者は Teams 側で認証済 (display name 付き)。ACS Media Streaming
> UNMIXED モードで `participantRawID` が audio chunk と一緒に届くので、声紋を取らずに
> speaker_id を解決できる。Voiceprint enrollment UX も不要。

- [ ] ~~**VI-1** Azure AI Speech Speaker Recognition API 統合~~
- [ ] ~~**VI-2** 声紋エンロールメント UI（30 秒録音）~~
- [ ] ~~**VI-3** 声紋プロファイル → Cosmos DB 保存（Entra ID と紐付け）~~
- [ ] ~~**VI-4** 会議中のリアルタイム 1:N 識別パイプライン~~
- [ ] ~~**VI-5** フォールバック: Diarization (Speaker A/B/C)~~
- [ ] ~~**VI-6** 共有マイクモード（1台のデバイス + 複数声紋の同時識別）~~

---

## ~~Day 11 — 5/27 (水) 🎯 マルチデバイス・ハイブリッド融合~~ ❌ 不要 (Teams Bot ピボットにより)

> ACS が会議全体の混合音声を 1 本 WebSocket で送ってくる。デバイス毎の音源統合は ACS/Teams 側で完結。
> SignalR でフロントを同期する話は Teams Bot ではダッシュボード polling で十分。

- [ ] ~~**HY-1** 物理参加者（共有マイク 1 台）+ リモート参加者（個別マイク）の音源統合~~
- [ ] ~~**HY-2** speaker_id を声紋識別 + ログイン情報の両方から付与~~
- [ ] ~~**HY-3** 全デバイスのサイドバー Azure SignalR 同期~~
- [ ] ~~**HY-4** エコーキャンセル（自分の声が自分のスピーカーから戻ってくる場合）~~
- [ ] ~~**HY-5** ハイブリッド会議の簡易テスト（PC 1 台 + 別ブラウザ + スマホで擬似）~~

---

## ~~Day 12 — 5/28 (木) L3 Speak + Quiet + Dissent~~ → 8.5.F Phase C に統合

> L3-1〜L3-3 は Phase C (TB-C1〜TB-C5) に置き換え。L3-4/L3-5 は既存の Quiet/Dissent agents
> が動作確認待ち (Phase E TB-E2 以降)。L3-6 (Microsoft Purview) は提出後の Phase F 候補。

- [ ] ~~**L3-1** Azure OpenAI gpt-4o-realtime 統合~~ → TB-C1/C2
- [ ] ~~**L3-2** Azure AI Speech TTS 統合~~ → TB-C2
- [ ] ~~**L3-3** Azure Communication Services で両側音声注入~~ → TB-C1
- [ ] **L3-4** Quiet Activator のリアル会議調整 → Phase E (TB-E3)
- [ ] **L3-5** Dissent Surface のリアル会議調整 → Phase E (TB-E3)
- [ ] **L3-6** Microsoft Purview 連携（機微発言ラベリング）→ 提出後 Phase F

---

## Day 13 — 5/29 (金) 仕上げ + 評価実験

- [ ] ~~**F-1** Power BI ダッシュボード（オプション）~~ ← 8.5.E のコスト dashboard で代替済 (Landing + MeetingRoom 内蔵)
- [x] **F-2** Application Insights のログ整備 ✅ 8.5.D F-2 で azure-monitor-opentelemetry 配線 + JSONRenderer 完了
- [x] **F-3** エラーハンドリング全面強化 ✅ 8.5.D F-1 で完了 (Decomposer/Redecompose 失敗時 fallback + 全 unhandled→500 JSON)
- [ ] **F-4** ソロ評価実験: 録音済み会議音声 × 2 セット（Helmsman ON / OFF）で動作差を記録
- [ ] **F-5** メトリクス記録（GAR / 介入受容率 / 決定構造化精度）
- [x] **F-6** 本番デプロイ確認 ✅ 8.5.D F-3 (Container App + SWA + DEPLOY.md)

---

## Day 14 — 5/30 (土) 🎯 デモ動画撮影 + Zenn 記事

- [ ] **D-1** 撮影台本の最終確定
- [ ] **D-2** ソロ撮影セットアップ（PC + iPad + iPhone でマルチ参加者擬似 / 事前録音音声を流す）
- [ ] **D-3** デモ動画 3 パターン撮影
- [ ] **D-4** 動画編集 + 字幕
- [ ] **Z-1** Zenn 記事 章 1-7 ドラフト
- [ ] **Z-2** Mermaid 図 1-7 を埋め込み

---

## Day 15 — 5/31 (日) Zenn 完成 + 提出準備

- [ ] **Z-3** Zenn 記事 章 8-15 + Appendix
- [ ] **Z-4** 推敲 + リンク確認
- [ ] **S-1** 審査員アクセス用 URL（公開デモモード）の準備
- [ ] **S-2** GitHub リポジトリ最終整理（README + LICENSE + CONTRIBUTING）
- [ ] **S-3** Container Apps 本番デプロイ確認 + ドメイン取得任意
- [ ] **S-4** 提出フォーム下書き

---

## Day 16 — 6/1 (月) 🚀 提出

- [ ] **SUB-1** 全成果物の最終動作確認（Web app + マルチデバイス + 声紋識別）
- [ ] **SUB-2** Zenn 記事最終チェック + 公開
- [ ] **SUB-3** GitHub タグ `v1.0.0` 作成（提出スナップショット）
- [ ] **SUB-4** 提出フォーム入力 + 提出（21:00 目標 / 23:59 必達）
- [ ] **SUB-5** X / LinkedIn で公開ツイート

---

## 審査期間 — 6/2 〜 6/18

- [ ] アプリの稼働維持（Container Apps 24/7）
- [ ] Application Insights 監視
- [ ] 審査員からの問い合わせ対応（メール常時チェック）
- [ ] 6/10 進出通知の確認
- [ ] 6/18 最終審査会出席

---

## 進捗集計 (2026-05-17 23:30 更新)

```
Day 0  (5/16 セットアップ):              7  /  7   完了
Day 1  (Azure リソース):                14  / 14   完了 (Az-8/9/13 を recheck で確認、Az-12 は Phase F へ斜線)
Day 2-5 (Backend Core):                 17  / 17   完了 (BE-8/9/14/16 を T-*/TB-* で実質完了済としてマーク)
Day 6-7 (Frontend):                      9  / 10   完了 (FE-4 Entra は Phase F へ斜線)
Day 8   (Web MVP)                        3  /  4   完了 (MVP-4 Planner は Phase F へ斜線)
Day 8.5.A (テスト整備):                 11  / 11   ✅ 完了 (66 tests pass)
Day 8.5.B (会議継続性 C-1〜6):           6  /  6   ✅ 完了
Day 8.5.C (文書 RAG):                    9  /  9   ✅ 完了 (DOC-5/6/8/9 もすでに済)
Day 8.5.D (審査基準):                    8  / 10   完了 (B-3 デモ動画 + A-3 Semantic Kernel が Phase F)
Day 8.5.E (コストダッシュボード):        7  /  7   ✅ 完了 (COST-7 ランディング集計済)
Day 8.5.F (Teams Bot):                  18  / 26   完了 (A 6/6 + B 6/6 + C 4/5 + D 9/9、Phase E trial 待ち)
Day 8.5.G (Facilitator 差別化):          2  /  4   完了 (POS-3/4 は Phase F)
Day 8.5.H (UI ブラッシュアップ):         5  /  5   ✅ 完了
Day 8.5.I (会議グループ + 書類):        16  / 17   ✅ 完了 (GRP-17 smoke は再デプロイ時)
Day 9-11 (PWA/声紋/Hybrid):              ❌ 不要化 (Teams Bot ピボットにより)
Day 12 (L3): → 8.5.F Phase C            -- 統合済
Day 13 (仕上げ/評価実験):                3  /  6   完了 (F-1 斜線 / F-2/3/6 は他で完了 / F-4/F-5 未実施)
Day 14-15 (デモ/Zenn):                   0  / 11   未着手
Day 16  (提出):                          0  /  5   未着手
─────────────────────────────────────
Total: ~134 / ~158 完了 (~85%)
```

**残タスク (5/19〜)**:
- TB-E1〜E5: Teams Essentials trial 待ち → smoke test (TB-E2/3/4) → trial 解約 (E5)
- TB-C4 (Barge-in) / TB-C5 (L2→L3 UI 昇格ボタン): smoke test 後の調整
- F-4/F-5 (Day 13): ソロ評価実験 (Helmsman ON/OFF 比較 + GAR/介入受容率記録)
- B-3 (Day 8.5.D): デモ動画にビフォアアフター数値を埋め込む (F-4/F-5 の結果を使う)
- Day 14-16: デモ撮影 + Zenn 記事 + 提出

**今すぐ着手可能な未着手 (外部ブロッカーなし)**:
- F-4/F-5: 録音済み会議音声があれば即評価可能
- POS-3 / Z-1〜Z-4: Zenn 記事執筆 (時間さえ取れれば書ける)

---

## 重要メモ

### 緊急時のフォールバック判断

- 5/24 で Web MVP が動かない → 声紋識別とハイブリッドを切り捨て、Webサイドバー単独で提出
- 5/27 でマルチデバイス同期が崩れる → 単一デバイス（ホスト画面のみ）で提出
- 5/30 でデモ撮影失敗 → 別途短縮版を 5/31 で撮影

### コスト監視

- 毎朝 9:00 に Azure Cost Analysis をチェック
- ¥22,500 月予算の 80% で再見直し
- スパイク発生時は即原因調査

### Discord 経由で詰まった時の escalation

- 技術質問: Discord Microsoft engineers
- フォーム・規約: zenn-support@classmethod.jp
