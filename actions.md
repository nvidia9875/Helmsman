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
- [ ] ~~**D-3 (5/30 土)**: PWA + 声紋 + マルチデバイス同期~~ ← **5/17 pivot で全部ドロップ済** (Teams bot + Web Dashboard 構成、マルチデバイス不要)
- [ ] **D-2 (5/31 日)**: ~~L3 Speak + Container Apps デプロイ~~ デプロイは既に完了、L3 は TB-C2 (8.5.M) で実装済 / デモ動画完成
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
- [ ] ~~**FE-9** Azure SignalR クライアント統合~~ ← **ADR-004 で却下**: 4 秒 polling で代用、interface 抽象化済 (100 人会議拡大時に WebPubSub に切替可能)。提出範囲外。
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
- [x] **B-3** デモ動画に "ビフォアアフター" 数値 — `docs/demo-numbers.md` に v1 (Helmsman OFF) vs v3-fixed cheap (ON) で「決定 0→10 件 / topic decided 0/5→5/5 / $0.03/会議」のヘッドライン 3 連 + 比較表 + 撮影台本テンプレを準備。撮影 (D-1〜D-4) で素材として投入

**【アプローチの有効性】**
- [x] **A-1** Multi-Agent 並列実行のシーケンス図を README に (Mermaid sequence、ACS join → STT → 8 agents → Arbiter → L3 TTS)
- [x] **A-2** Arbiter のアルゴリズム解説 (6 段階フィルタ + Density-aware silence + Authority gradient のフローチャート)
- [ ] ~~**A-3** Semantic Kernel + Azure AI Agent Service の正式採用~~ ← **Phase F (提出後)**。Zenn ADR-002 で「Copilot Studio Multi-Agent も Phase 6 で再導入予定」と明文化済

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

### 8.5.F Teams Bot ⚠️ ACS アプローチ廃止 (2026-05-20 判明) — 新方針は 8.5.M/N

> 🚨 **2026-05-20 重大事実判明**: 既存実装 (Phase A〜D) が依拠していた `TeamsMeetingLinkLocator` クラスは **ACS Call Automation の REST API spec / Python SDK / C# SDK / JS SDK のどこにも存在しない**ことを公式リポ + Microsoft Learn で確認。前 Claude セッションのハルシネーション。本番 Container App では `ImportError: cannot import name 'TeamsMeetingLinkLocator'` で派遣不能。
>
> 公式 Microsoft 公式制約:
> - **Application-hosted media bot** (生音声リアルタイム取得) = **Windows + C#/.NET 専用**
> - **Service-hosted media bot** (PlayPrompt / Record のみ) = 任意言語 (Python OK)
> - 詳細: https://learn.microsoft.com/en-us/microsoftteams/platform/bots/calls-and-meetings/calls-meetings-bots-overview
>
> 新方針 (2026-05-20 決定):
> 1. **8.5.M (本命)**: Service-hosted Graph bot を Python で実装 — 公式パス、Python のみ、5-10s 遅延の準リアルタイム
> 2. **8.5.N (フォールバック兼補完)**: Teams Tab + Web PWA — Web Speech API で生音声、Tab UI で Teams 内同居
>
> Phase A〜D の既存実装は流用可能な部分のみ残す (UI コンポーネント、Azure Speech 関連、TTS、tick pipeline、Cosmos 永続化など)。teams_bot.py の ACS 接続部分のみ書き換え。

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
- [ ] ~~**TB-C4** Barge-in 制御~~ ← **クローズ (2026-05-21)**: 8.5.M の単発 PlayPrompt 設計では概念的に不要。`recording_loop.py:87` の `bargeInAllowed: True` は Graph 録音 API の silent prompt 用パラメータで別概念
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

**Phase E: M365 テナント準備 + Bot 登録 (2026-05-19 進行中)**

⚠️ 経緯:
- 5/17 USER: Microsoft 365 Developer Program に申請 → Welcome メール届く (2026-05-19 確認)
- 5/19 USER: dashboard で「E5 not qualified」表示、E5 サンドボックスは付与されず断念
- 5/19 USER: M365 Business Standard trial チェックアウト画面まで進んだが、**最終「サブスクリプションを開始」を押さず購入未完了** (Graph `/subscribedSkus` 空 + 注文確認メール無しで確認)
- 結果: Dev Program のサインアップで作られたテナント `helmsmanjp.onmicrosoft.com` + admin アカウントだけが残り、M365 ライセンスはゼロ
- 副産物: Azure PAYG サブスクは helmsmanjp に自動作成された (現状リソース無しで¥0)

- [x] **TB-E1a** テナント + admin 作成完了 (Dev Program 経由)
  - テナント: `helmsmanjp.onmicrosoft.com` (ID: `bec25760-f44c-4ce5-9e1e-27b7f7080d10`、作成 2026-05-17 08:51 UTC)
  - Admin: `admin@helmsmanjp.onmicrosoft.com` (オブジェクトID `bf50a0d7-2b4d-4e09-9812-583018d49a0e`)
  - 組織表示名: 株式会社クイック (そのまま運用)
  - Entra プラン: Free のみ、M365 ライセンス無し
- [x] **TB-E1z** Teams ライセンス取得方針: 試行錯誤の末 Teams Essentials 試用版に決定
  - (失敗) 5/19 M365 Business Standard チェックアウト → 最終確定押さず未契約
  - (失敗) 5/19 M365 Business Basic (no Teams) 誤購入 → 即キャンセル、Suspended 確認、最終請求書 ~30日以内
  - (棄却) 個人 Outlook の Teams Free → ACS 公式に非対応 (`join-teams-meeting` ドキュメント明記)
  - (確定) 5/19 **Microsoft Teams Essentials 試用版** → admin@helmsmanjp に SKU `TEAMS_ESSENTIALS_AAD` 割当、TEAMS1/MCOIMP/EXCHANGE_S_DESKLESS など Success
  - 継続請求 OFF 実行済、7/19 自然失効で ¥0 終了予定
- [x] **TB-E1b** Azure CLI を helmsmanjp テナントに切替 (`az login --tenant bec25760-...`)
  - 発見: helmsmanjp 配下に Azure PAYG サブスクが自動作成済 (`49999bd3-fee5-482a-950e-45f843421cee`, spendingLimit=Off)
- [x] **TB-E1c** Budget アラート `helmsman-monthly-3000` を ¥3,000/月で設定 (50%/80%/予測100%、`admin@helmsmanjp` + `s.shunsuke9875@outlook.jp` 宛)
- [x] **TB-E1d** Entra ID で Bot アプリ登録: `helmsman-bot`
  - App ID: `ef2737f1-37bf-4392-a108-70f53f585b6d`
  - SP Object ID: `6506bedd-3d40-4776-9337-f85368a96b5a`
  - Sign-in audience: AzureADMyOrg (single-tenant)
  - Client secret: 発行済 (有効期限 2027-05-19、`MICROSOFT_APP_PASSWORD` として .env に格納)
- [x] **TB-E1e** Graph API アプリ権限 5 つを admin consent 付きで付与
  - `Calls.JoinGroupCall.All`
  - `Calls.AccessMedia.All`
  - `OnlineMeetings.Read.All`
  - `OnlineMeetingArtifact.Read.All`
  - `User.Read.All`
- [x] **TB-E1f** Resource Group `rg-helmsman-teams` (japaneast) + Azure Bot Service (F0 無料 tier, global) 作成
  - Teams チャネル (`MsTeamsChannel`) 有効化済 (`enableCalling: false`、Phase C で要見直し)
- [ ] **TB-E2** Teams 会議を作って実 URL で派遣 smoke test (TB-E1z 解決後)
- [ ] **TB-E3** STT 認識精度の手動評価 (日本語 30 分会議で何 % 拾えるか)
- [ ] **TB-E4** L3 TTS の声質 / レイテンシ評価
- [ ] **TB-E5** 🔴 **USER: ハッカソン終了後 (~2026-06-18) の後片付け** ← **詳細は P0 サマリ参照 (line 759)、ここは重複**
  - (1) もし TB-E1z で有料 M365 を契約していれば: https://admin.microsoft.com → 課金 → 定期請求 OFF (公式手順)
  - (2) `az group delete --name rg-helmsman-teams --yes --no-wait --subscription 49999bd3-fee5-482a-950e-45f843421cee` (Azure リソース全削除)
  - (3) (optional) helmsmanjp Azure サブスク自体も解約 (Azure Portal → コスト管理)
  - リマインダー必要なら: TB-E1z で M365 契約した場合のみ、trial 終了 1 日前の 21:00 JST にアラーム

### 8.5.M 🆕 本命: Service-hosted Graph Calling Bot (Python) 🌟 (2026-05-20 着手)

ACS Call Automation の Teams meeting join 機能が公式に存在しないため、**Microsoft Graph Communications API ベース**に全面切り替え。Service-hosted media bot として動作 (Python のみ、Windows 不要)。`Record` API で短時間 chunk 録音 → Azure Speech で STT → 既存 8 agents pipeline → `PlayPrompt` で TTS 介入発話。

**アーキテクチャ**:
```
Teams Meeting (helmsmanjp)
  ↑↓ webhooks + REST
Microsoft Graph /communications/calls
  ↑↓ HTTP/HTTPS
Python Container App (helmsman-dev-api)
  ├── services/graph_calling.py (新規) — Graph API client
  ├── services/recording_loop.py (新規) — 5s chunk 制御
  ├── services/teams_bot.py (改修) — invite/leave エントリ
  ├── api/routers/bot.py (改修) — /graph-call/callback webhook
  ├── services/tts.py (流用) — TTS 生成
  └── services/call_tick.py (流用) — agent pipeline
```

**主要トレードオフ**:
- ✅ Python のまま、既存資産 (8 agents, Cosmos, Azure Speech) 全部流用
- ✅ Microsoft 公式パス、長期的に安定
- ✅ 追加コスト無し (Container App 流用)
- ⚠️ **5-10 秒遅延** (chunk 録音 → DL → STT) ← 真のリアルタイムではない
- ⚠️ Application Access Policy 設定に **PowerShell 必須** (1 回だけ)

**Phase M.A: Foundations (Day 1: 2026-05-20) ✅ 完了**
- [x] **TB-M.A1** Graph API アプリ権限 8 個を admin consent 付きで付与 (OnlineMeetings.ReadWrite.All / Calls.Initiate.All / Calls.InitiateGroupCall.All ほか)
- [x] **TB-M.A3-A5** PowerShell 7.6.1 + MicrosoftTeams module 7.8.0 + Application Access Policy (`Helmsman-Bot-Policy`) 作成 + admin@helmsmanjp に grant
- [x] **TB-M.A6** Teams app manifest を calling bot 化 (`bots[*].supportsCalling: true`, `configurableTabs.context` 拡張, `webApplicationInfo.id`, `devicePermissions: media`)
- [x] **TB-M.A7** Bot Service messaging endpoint = `/api/messages`, calling webhook = `/api/calling` 設定済 (Teams チャネル calling 有効化)

**Phase M.B: Graph API で Teams 会議 join (Day 2: 2026-05-20) ✅ 完了**
- [x] **TB-M.B1** `services/graph_calling.py` 新規実装 — Bot Framework JWT + Graph token の二重キャッシュ、`/users/{id}/onlineMeetings?$filter=JoinWebUrl` で coords 取得、`POST /communications/calls` で join、`hangup_via_graph()`
- [x] **TB-M.B2** Bot Framework + Graph token 取得関数 (`_fetch_bot_token` / `_fetch_graph_token`、いずれも client_credentials)
- [x] **TB-M.B3** `POST /api/calling` webhook handler 実装 — commsNotifications を defensive parse、state 変更 / participant 更新 / operation 完了の 3 種ハンドリング、call_id を URL から正規表現抽出
- [x] **TB-M.B4** `services/teams_bot.py` 薄いラッパに刷新 (ACS インポート削除、Graph 経路に delegate)
- [x] **TB-M.B5** 実機 smoke test: bot が helmsmanjp の Teams 会議に入室・state 遷移 JOINING→LISTENING・DISCONNECTED 全部確認

**Phase M.B-fix: webhook / 認証 / アーキ周辺の修正 ✅ 完了**
- [x] **B-fix.1** App を SingleTenant → MultiTenant に変更 (Bot Framework JWT 発行のため必須、AADSTS700016 解消)
- [x] **B-fix.2** `/communications/calls` 用 token は Graph token (`audience=graph.microsoft.com`)、Bot Framework JWT は不要 — roles 0 件でルーティング不可と判明し修正
- [x] **B-fix.3** in-memory call registry (`_call_registry`) 追加 → operationContext が webhook で echo されなくても call_id で meeting を引き戻せる fallback
- [x] **B-fix.4** participants webhook → 人ゼロ判定で自動 hangup (`graph.auto_hangup`、Teams 会議終了に追従)
- [x] **B-fix.5** disconnect 時に CallSession を `registry.drop()` で削除 (古い call_id の lookup 防止)

**Phase M.C: 録音 → STT ループ (Day 3: 2026-05-20) ✅ 完了**
- [x] **TB-M.C1** `services/recording_loop.py` 新規 — `recordResponse` を 10 秒 chunk で連続 trigger、in-memory task registry + pause/resume API
- [x] **TB-M.C2** `services/recording_stt.py` 新規 — recording URL を Bearer 認証で download → Azure Speech SDK で batch 文字化 (executor 経由) → CallSession.utterances に append → `maybe_trigger_tick`
- [x] **TB-M.C3** chunk 結果が tick pipeline (8 agents + Arbiter) に流れることを実機確認 (DissentSurface 発火)
- [x] **TB-M.C4** silent prompt 100ms + INTER_CHUNK_SLEEP=0 で chunk 境界の音声欠落最小化
- [x] **TB-M.C5** Microsoft error 8523 (Only single prompt is supported) 対処: `/static/silent.wav` (16kHz/16bit/mono/100ms) を在中 endpoint で配信し prompts 配列に必須要素を渡す

**Phase M.D: TTS 介入発話 (Day 3: 2026-05-21) ✅ 完了**
- [x] **TB-M.D1** `services/graph_play_prompt.py` 新規 — `synthesize_pcm` の PCM を WAV ヘッダ付きにし in-memory cache + uuid キーで `/static/tts/{key}.wav` 配信
- [x] **TB-M.D2** Microsoft の早期 completed 報告対策で末尾 1.5s silence padding
- [x] **TB-M.D3** Graph `POST /communications/calls/{id}/playPrompt` を Graph token で発行 (Bot Framework JWT は 401 になるため不可)
- [x] **TB-M.D4** Arbiter L3 選択 → session に media_ws 有無で ACS/Graph 経路を自動切替 (`call_tick.py`)
- [x] **TB-M.D5** Microsoft の "1 call 1 op only" 制約対処: TTS 中は recording loop を `pause_recording_for_tts` で停止、`playPromptOperation completed` webhook で resume + auto_resume fallback (pcm_duration + 5s)
- [x] **TB-M.D6** 実機検証: 日本語 TTS フル再生 (「こんにちは、ヘルムスマンです。最後まで聞こえれば成功です。」最後まで)

**Phase M.E: フロント統合 + smoke test ✅ 完了 (M.B / M.D 実機検証時に同時消化)**

**Phase M.F: 後始末 ✅ 完了 (2026-05-21)**
- [x] **TB-M.F1** 旧 ACS 関連コード削除 — bot.py から WebSocket + ACS callback handler (216-441 行、計 226 行) 撤去、teams_bot.py を Graph wrapper に薄化
- [x] **TB-M.F2** pyproject.toml から `azure-communication-callautomation` + `azure-communication-identity` 削除 (bundle 軽量化、ACS SDK が依存連れてきていた抜本依存も解消)
- [ ] **TB-M.F3** 🔴 **USER** ACS リソース (rg-helmsman-dev 内 `helmsman-dev-acs`) 削除可能 (節約 ~¥3,000/月) — `az resource delete --ids ...` で実行 ← **P0 サマリ (line 757) と重複**

---

### 8.5.O 🆕 設定機能 + UI 改善 (2026-05-21 実装、ユーザー要望 5 項目)

ユーザーから受けた追加要望: タイムキーパー / 方向確認 toggle / bot アイコン / UI 大幅改善 / facilitator name バグ。

**O.A: バックエンド設定機能 ✅ 完了**
- [x] **TB-O.A1** Meeting model 拡張: `facilitator_name` / `steering_enabled` / `timekeeper_alerts (list[TimekeeperAlert])`
- [x] **TB-O.A2** `PATCH /meetings/{id}/settings` エンドポイント追加 (3 つ全部一括編集)
- [x] **TB-O.A3** `StartMeetingRequest.facilitator_name` フィールド追加 (派遣時に保存)
- [x] **TB-O.A4** `call_tick.py` `_maybe_fire_timekeeper()` — 経過分が target 超過した未発火 alert を音声発火 + fired フラグ書き戻し
- [x] **TB-O.A5** Steering candidate を `meeting.steering_enabled=False` なら Arbiter 候補から除外

**O.B: フロント設定 UI ✅ 完了**
- [x] **TB-O.B1** `MeetingSettings.tsx` 新規 — 折りたたみ式 (デフォルト closed)、状態 summary バッジ ("名前: ... · Alert × 2")
- [x] **TB-O.B2** AI ファシリテーター名 input / 議論方向 Switch / タイムキーパー alerts CRUD (分後 + メッセージ + enabled + 発火済 dot)
- [x] **TB-O.B3** `CreateMeeting.tsx` で facilitator_name を実際に backend に送信 (元来の bug 修正)
- [x] **TB-O.B4** MeetingRoom ヘッダーに facilitator_name 表示 (`MISSION CONTROL · session · {name}`)
- [x] **TB-O.B5** Recent sessions: ENDED を `neutral` (gray) 表示に変更 (赤はエラーのみ)

**O.C: HELMSMAN アイコン群 ✅ 完了**
- [x] **TB-O.C1** `HelmsmanIcon.tsx` primitive 新規 — 8-spoke 船舵 SVG、active 時 spin animation (`@keyframes helmsman-spin`)
- [x] **TB-O.C2** `BotStatusStrip` / `BotMissionCard` の 🧭 emoji を HelmsmanIcon に置換
- [x] **TB-O.C3** `apps/web/public/favicon.svg` を船舵デザインに刷新
- [x] **TB-O.C4** `apps/teams-app/icons/color.png` (192x192) + `outline.png` (32x32) を Python/Pillow で生成
- [x] **TB-O.C5** Bot Service / Entra ID app display name を "Helmsman" に統一
- [ ] **TB-O.C6** 🔴 **USER: Entra Portal で Bot app にロゴアップロード** (Graph API は権限不足で API 経由不可) — Teams 会議内の `<>` placeholder が船舵になる ← **P0 サマリ (line 756) と重複**
  - URL: https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Branding/appId/ef2737f1-37bf-4392-a108-70f53f585b6d
  - ローカルファイル: `/tmp/helmsman_entra_icon.png` (240x240)

**O.D: UI 全体改善 (futuristic AI 感) ✅ 完了 (2026-05-21)**
- [x] **TB-O.D1** `global.css` 拡張: 新色 (accent-cyan / accent-violet / accent-glow)、ambient gradient orb (24s drift)、grid pattern overlay、`.glass` / `.glow-active` / `.breathing` utility
- [x] **TB-O.D2** `CountUp.tsx` primitive 新規 — 数値変更時に ease-out cubic で 400ms 補間
- [x] **TB-O.D3** KpiRow 全部 (utterances / interventions / decisions / cost) を CountUp 化
- [x] **TB-O.D4** BotStatusStrip に `.glass` + `.glow-active` 適用 (in_call 時にパルス glow)
- [x] **TB-O.D5** docsPanel に `.glass` 適用
- [x] **TB-O.D6** Onboarding hero — `OnboardingSteps.tsx` を 3 ステップ縦並びヒーローに刷新 (大番号 + 矢印 + breathing で「派遣フォームへ」誘導)。「情報密度が高すぎる」「初めての人が何を設定したらいいか分からない」フィードバックへの対応
- [x] **TB-O.D7** Sidebar polish — Topics に gradient progress bar (decided/total) + 議論中 topic に ON AIR バッジ + cyan accent border + deep_dive で StatusDot pulse 追加
- [x] **TB-O.D8** BotStatusStrip beacon の glow リング強化 — in_call 時に 3s ease-in-out で cyan の inset/outset 双方向 pulse glow (16px → 32px)
- [x] **TB-O.D9** ページ遷移 stagger アニメ — `.stagger > *:nth-child(N)` で 50ms ずつ delay 付き fadeRise (cubic-bezier 0.16,1,0.3,1)。`prefers-reduced-motion` 対応も同居
- [x] **TB-O.D10** 全パネルへの glass 適用統一 — InterventionFeed / LiveTranscript / MeetingPulse に `backdrop-filter: blur(12px) saturate(140%)` + inset highlight を一括適用

---

### 8.5.N 🆕 フォールバック兼補完: Teams Tab + Web PWA 🌟 (2026-05-26 着手予定)

8.5.M で 5-10 秒遅延が許容できない場合、または並行アピール材料として実装。Helmsman を Teams 会議内の Tab として埋め込み、ブラウザ側で **Web Speech API** で音声キャプチャ (真のリアルタイム)。

**主要トレードオフ**:
- ✅ 完全リアルタイム (Web Speech API は <1 秒)
- ✅ Microsoft 公式 Teams Tab SDK パス
- ✅ サーバー側でメディア処理しないのでスケール容易
- ⚠️ 参加者全員が Teams Tab を開く必要 (ホスト 1 人で十分という設計も可能)
- ⚠️ Web Speech API は Chrome/Edge のみ完全対応

**Phase N.A: Web Speech 復活 ✅ 完了 (2026-05-21)**
- [x] **TB-N.A1** 既存 `useBrowserSTT.ts` (`apps/web/src/hooks/`) を再評価 — 既に Web Speech API ラッパとして稼働中
- [x] **TB-N.A2** `apps/web/src/components/SoloMicCard.tsx` 新規 — Web Speech + テキスト入力 + tick 実行を 1 枚に統合
- [x] **TB-N.A3** MeetingRoom UI に SoloMicCard を `needsDispatch` 中常設で追加 (bot 派遣不要の solo demo モード)。旧 dev-fallback Accordion (`UtteranceConsole`) は削除
- [x] **TB-N.A4** Web Speech 結果を既存 `POST /meetings/{id}/tick` に流す経路接続 — append → useUtteranceLog → tickMutation で agents 走り、介入結果は violet カードで in-card 表示

**Phase N.B: Teams Tab manifest ✅ 完了 (2026-05-21)**
- [x] **TB-N.B1** `apps/teams-app/manifest.json` に `configurableTabs` 設定済 (`/teams-config` を configurationUrl に、context は channelTab/meetingChatTab/meetingDetailsTab/meetingSidePanel/meetingStage の 5 つ全て対応)
- [x] **TB-N.B2** `validDomains` に SWA URL (`kind-glacier-0122f6400.7.azurestaticapps.net`) 追加済
- [x] **TB-N.B3** Teams JavaScript SDK (`@microsoft/teams-js@2.53.0`) を Helmsman Web に組み込み — `lib/teams.ts` で `getTeamsContext()` + `looksLikeTeamsHost()`、`/teams-config` ルート (TeamsConfig.tsx) で `pages.config.registerOnSaveHandler` 配線済
- [-] **TB-N.B4** Tab 検出時の UI 切替 (chrome 簡略化) — `looksLikeTeamsHost()` 用意済だが、AppShell 切替は提出後 polish (現状: Teams 内では `?teamsTab=1` 付きで開かれる)

**Phase N.C: Sideload + E2E test (Day 8: 5/27、USER 手動)**
- [x] **TB-N.C0** `apps/teams-app/SIDELOAD.md` 新規 — 6 ステップで明文化 (zip 化 → Admin Center 許可 → サイドロード → 動作確認チェックリスト → トラブルシューティング → 撤去)
<!-- TB-N.C1-C5: 詳細手順は apps/teams-app/SIDELOAD.md、P0 サマリは line 758。以下は手順詳細。 -->
- [ ] **TB-N.C1** 🔴 **USER** Teams 管理センターで sideloading 有効化 (admin.teams.microsoft.com → アプリポリシー)
- [ ] **TB-N.C2** 🔴 **USER** Helmsman manifest を Teams app パッケージ化 (`zip -j helmsman-app.zip manifest.json icons/color.png icons/outline.png`)
- [ ] **TB-N.C3** 🔴 **USER** admin.teams.microsoft.com でカスタムアプリアップロード
- [ ] **TB-N.C4** 🔴 **USER** 実 Teams 会議に Tab として追加 → save handler が走るか確認 → 通常通り派遣 → tick fires
- [ ] ~~**TB-N.C5** デモ用に「Tab 経由 + bot 経由」両方を併存させた最終 UI 確認~~ ← **Nice-to-have、提出に必須ではない**。C1-C4 が通れば Tab 単独でも bot 単独でも動く

---

### 8.5.G ポジショニング (Microsoft Teams Facilitator との差別化) 🌟 新規 (2026-05-17 着手)

Microsoft Teams ネイティブ Facilitator (Copilot エージェント) との関係を明確化。

- [x] **POS-1** README に「Microsoft Teams Facilitator との違い」セクション追加 (11 行比較表 + 利用ケース整理 + 補完関係明記)
- [x] **POS-2** Landing にバッジ (Copilot ライセンス不要 / 外部参加者として join / AI 音声介入 / OSS) + Facilitator 公式ドキュへの直リンク + README §Facilitator との違い へのアンカー
- [ ] **POS-3** Zenn 記事 / デモ動画に「Facilitator は補完関係」スライド追加 ← Zenn 記事 §8 で対応済、**残: 動画スライド化のみ** (P2 サマリ line 788 参照)
- [ ] ~~**POS-4** A-3 Semantic Kernel 採用~~ → **Phase F (提出後)**。A-3 と重複・統合済

### 8.5.L RAG 文書グラウンディング検証 🌟 新規 (2026-05-17 完了)

DOC-* 機能群を実音声で検証。GoalDecomposer / Coverage / DecisionCapture が
文書を引用 + 矛盾警告を出す経路を E2E で動作確認。

- [x] **RAG-1** `--doc-text PATH` フラグを eval CLI に追加 (`scripts/eval_offline.py`)
- [x] **RAG-2** `run_eval(doc_excerpts=...)` パラメータを runner で全 agent に伝搬
- [x] **RAG-3** 合成戦略 Memo を `scripts/fixtures/youtube_strategy_memo.txt` に配置 (YouTube 会議と内容オーバーラップ、1 KB)
- [x] **RAG-4** v4 (cheap+doc) を実音声 transcript replay で実行: $0.045 / 17 介入 / 12 decisions / 6 topics に **document_reference 自動付与** / **DOC-6 矛盾警告初発火**
- [x] **RAG-5** 結果を `docs/eval-results.md` 5-way 比較に反映 + README にデモ用 RAG 検証セクション追加

### 8.5.K 話者分離 (UNMIXED) 🌟 新規 (2026-05-17 完了)

Teams 認証済参加者の identity をそのまま活かす設計。声紋識別を入れずに speaker_id を解決。
Day 10 (VI-*) で「不要化」と書いてあった理屈の **実装** がやっと揃った。

- [x] **SR-1** `teams_bot.py`: `MediaStreamingAudioChannelType.MIXED` → **UNMIXED** に切替
- [x] **SR-2** `TranscriptEvent.speaker_id` + `StreamingTranscriber(participant_id=...)` 追加
- [x] **SR-3** `CallSession`: `transcribers: dict[participant_id, StreamingTranscriber]` + `consumer_tasks` + `participants_by_raw_id` (displayName キャッシュ)
- [x] **SR-4** `bot.py` WebSocket: `AudioData` frame から participantRawID 抽出 → `get_or_create_transcriber` で per-participant STT + consumer task 起動。SDK バージョン揺れに備え複数キー(participantRawID/Id, participant.rawId など)を fallback
- [x] **SR-5** ACS webhook の `ParticipantsUpdated` で `participantRawID → displayName` を session に学習。utterance の speaker_id は最終的に display name で記録 (未解決時のみ raw ID)

### 8.5.J オフライン評価ハーネス 🌟 新規 (2026-05-17 完了)

Teams trial 待ち期間に既存音声/transcript で精度を詰めるためのオフライン評価。
Cosmos / Teams / ACS を介さず in-memory に既存 8 agents + Arbiter を流す。

- [x] **EVAL-1** `src/helmsman/eval/audio.py` — WAV → Speech SDK → Utterance ストリーム + JSONL モード (STT スキップでプロンプト調整用)
- [x] **EVAL-2** `src/helmsman/eval/runner.py` — in-memory Meeting + 音声時間軸での tick オーケストレータ + GoalDecomposer 自動実行
- [x] **EVAL-3** `src/helmsman/eval/report.py` — utterances/interventions/candidates/ticks JSONL + final_meeting.json + metrics.json + report.md 自動生成
- [x] **EVAL-4** CLI `scripts/eval_offline.py` — `--audio` or `--transcript` + goal/mode/intensity/tick interval 引数
- [x] **EVAL-5** 集計指標: 介入数 (level/agent別)、Arbiter acceptance rate、topic 状態分布、決定捕捉、LLM コスト/トークン、tick latency
- [x] **EVAL-6** サンプル fixture (`scripts/fixtures/sample_meeting.jsonl`) で即試せる
- [x] **EVAL-7** unit test 3 件 (`tests/test_eval.py`、agents 全モックで run_eval → write_report 検証) — pytest 69/69 pass

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
- [x] **GRP-17** 本番 smoke (2026-05-18): UI から /groups 叩いて 500 確認 → Cosmos に `groups` / `group_documents` コンテナを az CLI で直接作成 → エンドポイント 200 復帰。Bicep 再デプロイ未実施が原因、後続対策として GitHub Actions or auto-create startup hook を検討

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
- [ ] ~~**L3-6** Microsoft Purview 連携（機微発言ラベリング）~~ → **Phase F (提出後)**。Zenn §9 で RAI のうち Privacy 章で言及済

---

## Day 13 — 5/29 (金) 仕上げ + 評価実験

- [ ] ~~**F-1** Power BI ダッシュボード（オプション）~~ ← 8.5.E のコスト dashboard で代替済 (Landing + MeetingRoom 内蔵)
- [x] **F-2** Application Insights のログ整備 ✅ 8.5.D F-2 で azure-monitor-opentelemetry 配線 + JSONRenderer 完了
- [x] **F-3** エラーハンドリング全面強化 ✅ 8.5.D F-1 で完了 (Decomposer/Redecompose 失敗時 fallback + 全 unhandled→500 JSON)
- [x] **F-4** ソロ評価実験: 録音済み会議音声 × 5 セット (monitor / goal high / cheap / cheap+doc) で動作差を記録 ✅
  - [x] ハーネス `scripts/eval_offline.py` 実装済
  - [x] **第 1 サイクル完了 (2026-05-17)**: 実音声 25.7 min (YouTube マーケ定例) で v1 (monitor) / v2 (goal) 比較
    - v1 monitor mode: 173 utt / 26 ticks / 13→7 candidates (53.8%) / Dissent×7 / **$0.08**
    - v2 goal-driven: 173 utt / 26 ticks / **33→11** candidates (33.3%) / **Steering×5 + Decision×5 + Dissent×1** / topics 5 (decided 1, deep_dive 2, discussing 2) / **$0.18**
    - 質的発見: DecisionCapture が 3H 戦略、青地黄字テンプレ、再生数 KPI など実会議の結論 5 件を正しく構造化
  - [x] **第 2 サイクル完了 (2026-05-17)**: v3 (cheap = Decision+Dissent mini、transcript replay) で v2 と同じ素材を比較
    - v3 (buggy): 173 utt / 26 ticks / **34→3** candidates / 当初「mini は品質劣化」と結論
  - [x] **Arbiter rate_limit バグ発見 + 修正 (2026-05-17)**: `commit 3a1f592` で audio-time clock 注入。v3-buggy は時間圧縮で 31 candidates が rate_limit に弾かれていた人為的結果
  - [x] **第 3 サイクル完了 (2026-05-17)**: rate_limit 修正後に v2-fixed (high) と v3-fixed (cheap) を再評価
    - v2-fixed: 173 utt / 26→10 deliveries / **5 decisions / 4 topics decided / $0.17**
    - v3-fixed cheap: 173 utt / 33→**15** deliveries / **10 decisions / 5 topics decided / $0.03 (1/6)**
    - **結論逆転**: cheap モードが default を上回る (decisions 2x / cost 1/6 = **decision あたり 11× 安**)。本番 cost-optimal 設定として推奨格上げ
  - [x] 比較レポート `docs/eval-results.md` 4-way 版に更新
- [x] **F-5** メトリクス記録 (GAR / 介入受容率 / 決定構造化精度) ← 完了
  - [x] acceptance_rate: v1 54% / v2-fixed 39% / v3-fixed cheap **45%** を計測
  - [x] delivered_by_level + by_agent: 自動集計
  - [x] 決定構造化精度: v3-fixed cheap の Decision **10 件全部が実発言に紐づく (precision 100%)** — grep 確認 (千人 / 3H / 青字 / 平日効果)
  - [x] Topic state timeline: 26 tick × 5 topics の遷移を ticks.jsonl から可視化、v3-fixed では tick 23 で全 5 topics decided
- [x] **F-6** 本番デプロイ確認 ✅ 8.5.D F-3 (Container App + SWA + DEPLOY.md)

---

## Day 14 — 5/30 (土) 🎯 デモ動画撮影 + Zenn 記事

- [ ] **D-1** 撮影台本の最終確定
- [ ] **D-2** ソロ撮影セットアップ（PC + iPad + iPhone でマルチ参加者擬似 / 事前録音音声を流す）
- [ ] **D-3** デモ動画 3 パターン撮影
- [ ] **D-4** 動画編集 + 字幕
- [x] **Z-1** Zenn 記事 章 1-7 ドラフト → `docs/zenn-article-draft.md` (16 h2 sections, 1130 行)
- [x] **Z-2** Mermaid 図 5 枚埋め込み → Tick sequence / Container topology / Arbiter flowchart / Topic FSM / Report sequence

---

## Day 15 — 5/31 (日) Zenn 完成 + 提出準備

- [x] **Z-3** Zenn 記事 章 8-13 + Appendix → 下書き完成 (37k chars / プロンプト 5 種 / ADR 5 件 / Q&A 5 件)
- [x] **Z-4** 推敲 + リンク確認 → 数値更新 (テスト 41→89 / arbiter 16→17)、未検証メトリクス削除、クロスリファレンス検証済 (残: YouTube URL `REPLACE_ME` 2 箇所、撮影後差し替え)
- [ ] **S-1** 審査員アクセス用 URL（公開デモモード）の準備
- [ ] **S-2** GitHub リポジトリ最終整理（README + LICENSE + CONTRIBUTING）
- [ ] **S-3** Container Apps 本番デプロイ確認 + ドメイン取得任意
- [ ] **S-4** 提出フォーム下書き

---

## Day 16 — 6/1 (月) 🚀 提出

- [ ] **SUB-1** 全成果物の最終動作確認（Web Dashboard + Teams bot 派遣 + Report 生成 + RAG 経路） ← ~~マルチデバイス + 声紋識別~~ は 5/17 pivot で対象外
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
Day 8.5.D (審査基準):                    9  / 10   完了 (B-3 素材化済 / A-3 Semantic Kernel が Phase F)
Day 8.5.E (コストダッシュボード):        7  /  7   ✅ 完了 (COST-7 ランディング集計済)
Day 8.5.F (Teams Bot):                  21  / 26   完了 (A 6/6 + B 6/6 + C 4/5 + D 9/9 + F1-2 / N.A4 / N.B3 完了、Phase E trial 待ち + N.C USER 待ち)
Day 8.5.G (Facilitator 差別化):          2  /  4   完了 (POS-3/4 は Phase F)
Day 8.5.H (UI ブラッシュアップ):         5  /  5   ✅ 完了
Day 8.5.I (会議グループ + 書類):        16  / 17   ✅ 完了 (GRP-17 smoke は再デプロイ時)
Day 8.5.J (オフライン eval ハーネス):    7  /  7   ✅ 完了 (実音声投入で F-4/F-5 計測可能に)
Day 8.5.K (話者分離 UNMIXED):            5  /  5   ✅ 完了 (Day 10 VI-* の代替案を実装)
Day 8.5.L (RAG 文書グラウンディング検証):  5  /  5   ✅ 完了 (DOC-* 全機能 E2E 動作確認 + DOC-6 矛盾警告初発火)
Day 9-11 (PWA/声紋/Hybrid):              ❌ 不要化 (Teams Bot ピボットにより)
Day 12 (L3): → 8.5.F Phase C            -- 統合済
Day 13 (仕上げ/評価実験):                5  /  6   ✅ 完了 (F-1 斜線 / F-2/3/4/5/6 全完了、5/17 と 5/21 の素材化で前倒し)
Day 14-15 (デモ/Zenn):                   0  / 11   未着手
Day 16  (提出):                          0  /  5   未着手
─────────────────────────────────────
Total: ~141 / ~158 完了 (~89%)
```

**残タスク (2026-05-21 14:30 JST 時点、提出 6/1)**:

🎉 **想定 5 日先取り**: 13 日プランの Day 8 相当 (M.A〜M.D + 8.5.O + M.F + 8.5.N.A/B + B-3 デモ素材) が Day 2 (5/20-5/21) で完了。残 10 日は USER 手動 (N.C sideload + Entra logo + ACS リソース削除) + Zenn + デモ撮影 + 提出。

**実績タイムライン (実装済)**:

| 日付 | 達成 |
|---|---|
| 2026-05-20 (火) | 8.5.M.A 完了 (Graph 権限・PowerShell・Application Access Policy・manifest) + 8.5.M.B 完了 (graph_calling + webhook + smoke test) |
| 2026-05-20 (火) 夜 | 8.5.M.B-fix 完了 (MultiTenant 化、call registry fallback、auto_hangup、CallSession drop) + 8.5.M.C 完了 (recording_loop + STT + 実機 6 utterance 文字化) |
| 2026-05-21 (水) 早朝 | 8.5.M.D 完了 (silent.wav prompt + WAV 末尾 padding + recording pause/resume + 日本語 TTS フル再生確認) |
| 2026-05-21 (水) 昼 | 8.5.O 完了 part 1 (タイムキーパー / 方向確認 toggle / facilitator name / 船舵アイコン / glass + glow + CountUp) |
| 2026-05-21 (水) 午後 | 8.5.M.F1-2 (ACS dead code 削除、269 行クリーン) + 8.5.O.D6-D10 完了 (Onboarding hero / 全パネル glass / Sidebar ON AIR + progress bar / beacon 強脈動 glow / page stagger) + 8.5.N.A 完了 (SoloMicCard) + 8.5.N.B 完了 (@microsoft/teams-js + /teams-config) + B-3 デモ素材完成 (`docs/demo-numbers.md`) + N.C SIDELOAD.md 整備 |

**残タイムライン (5/22〜6/1)**:

| Day | Date | 内容 |
|---|---|---|
| - | 5/22 (木) | **休息推奨** + USER タスク消化 (Entra logo / ACS リソース削除 / Teams sideload テスト) |
| - | 5/23 (金) | 🔴 USER: 8.5.N.C 実行 (`apps/teams-app/SIDELOAD.md` 通り) — Teams 会議に Tab 追加 → 動作確認 |
| - | 5/24 (土) | Zenn 章立て + 技術解説下書き (Z-1) — Graph Calling 編 |
| - | 5/25 (日) | Zenn (Z-2) — 8 agents + Arbiter 編 |
| - | 5/26 (月) | Zenn (Z-3) — TTS pause/resume + recording loop 編 |
| - | 5/27 (火) | Zenn (Z-4) — 評価実験 (cheap mode 優位性) + POS-3 (Facilitator との差別化) |
| - | 5/28 (水) | **デモ動画撮影 Day 1** — `docs/demo-numbers.md` の台本通り。8.5.M Bot + 8.5.O Settings + 8.5.N Tab 全部見せる |
| - | 5/29 (木) | デモ動画撮影 Day 2 + 編集 + 数値スライド合成 (ビフォアアフター 3 連) |
| - | 5/30 (金) | 動画完成 + Zenn 公開 + 最終 QA |
| - | 5/31 (土) | 提出フォーム入力 + final smoke test |
| - | 6/1 (月) | 🚀 提出 |

審査期間: 6/2-6/18、最終審査 6/18。Teams Essentials trial が 7/19 まで延長済なので余裕大幅あり。

---

### 🔴 残必要作業 (優先度順)

**P0 (必須、shun さん手動が必要)**:
- [ ] **TB-O.C6** Entra Portal で bot app ロゴアップロード — `/tmp/helmsman_entra_icon.png` を https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Branding/appId/ef2737f1-... に手動アップロード
- [ ] **TB-M.F3** rg-helmsman-dev の ACS リソース削除 (`az resource delete --ids ...`、節約 ~¥3,000/月)
- [ ] **TB-N.C1-C5** Teams sideload + 実会議 Tab 動作確認 — `apps/teams-app/SIDELOAD.md` 手順通り
- [ ] **TB-E5** ハッカソン終了後の片付け (~6/18 以降): `rg-helmsman-teams` 削除、Teams Essentials は trial 自然失効で OK
- [ ] **#16** Business Basic (no Teams) 誤購入の最終請求書チェック (~6/19 まで)

**P1 ✅ 完了 (2026-05-21 午前)**:
- [x] **TB-M.F1-F2** ACS 関連の死コード削除 + pyproject.toml から `azure-communication-callautomation` + `azure-communication-identity` 削除
- [x] **TB-O.D6-D10** UI 追加磨き込み: Onboarding hero 刷新 / BotStatusStrip beacon の cyan 強脈動 glow / Sidebar の ON AIR + gradient progress bar / 全パネル glass 統一 / page stagger アニメ
- [x] **TB-N.A** SoloMicCard 新規 + 旧 UtteranceConsole Accordion 削除 (Web Speech をファーストクラス化)
- [x] **TB-N.B** `@microsoft/teams-js@2.53.0` + `/teams-config` ルート + `pages.config.registerOnSaveHandler` 配線
- [x] **B-3** デモ動画用ビフォアアフター数値 — `docs/demo-numbers.md` 新規 (0→10 件 / 0/5→5/5 / $0.03/会議 + 撮影台本テンプレ)
- [x] **F-4/F-5** ソロ評価実験 — 既に 5/17 完了済 (5-way 比較、cheap モード優位性発見)

**P1 ✅ 完了 (2026-05-21 午後)** — Report 機能 + RAG smoke + Zenn 記事:
- [x] **REPORT-1** `MeetingReportGenerator` agent 新規 (gpt-5.4 HIGH) — テンプレ + メモ + Helmsman 構造化結果から markdown レポート生成。情報源優先度をプロンプトで明示 (memo > structured > raw)、矛盾時は `⚠️ 事実関係要確認` 明示。`src/helmsman/agents/report_generator.py`
- [x] **REPORT-2** `MeetingReport` モデル + Cosmos `meeting_reports` repo 永続化 (partition key `/meeting_id`、template_snapshot / memo_snapshot / usage も保存)。Cosmos container 実機作成済
- [x] **REPORT-3** API 3 endpoint 追加 (`POST /meetings/{id}/report` / `GET /reports` / `GET /reports/latest`)。本番 OpenAPI で 3 つとも反映確認済
- [x] **REPORT-4** `ReportPanel` UI 新規 (`apps/web/src/components/ReportPanel.tsx`): template/memo textarea + 生成ボタン + プレビュー + 履歴切替。`MeetingRoom` の Accordion に defaultOpen で配置
- [x] **REPORT-5** テスト追加 — pytest 89 件 pass (新規 +9: ReportGenerator 6 + reports repo 3)、vitest 9 件 pass (新規 +3 ReportPanel + OnboardingSteps 旧 4 step → 3 step 修正)
- [x] **REPORT-6** 本番 LLM smoke 検証 — 3 ケース (default / template only / template+memo) すべて成功。default 10.8s / 1247-in / 859-out / ~$0.014、template 6.3s / $0.009、template+memo 6.8s / $0.010 (gpt-5.4)。`scripts/smoke_report.py`
- [x] **RAG-S1** 本番 Azure AI Search の end-to-end smoke (`scripts/smoke_rag.py`): ensure_index 711ms / embed 1162ms (466 tok, 1536 dim) / upsert 724ms / vector search cold 648-1549ms warm ~700ms / cosine 0.61-0.72 (3 自然文 query すべて hit)
- [x] **RAG-S2** 🔴 本番 bug 発見 + 修正: Azure OpenAI に `text-embedding-3-small` deployment 自体が **未作成** だった (RAG コード/Search index/ingest 経路は全部書かれてたが silent skip 設計のため 0 件で気付けなかった)。smoke で 404 を踏んで初めて発覚 → `az cognitiveservices account deployment create` で投入。Layer A (eval `--doc-text`) と Layer B (本番 vector pipeline) の 2 段検証体制に整理
- [x] **Z-1/Z-2** Zenn 記事下書き完成 — `docs/zenn-article-draft.md` (37k chars / 16 h2 sections / Mermaid 5 図 / プロンプト工夫 5 種 / ADR 5 件 / Q&A 5 件)。§3.8 (Report agent プロンプト) / §5 (AI が代弁する構造、4 失敗パターン) / §6.1-6.9 (実装ハイライト 9 連) / §7.3 (RAG 2 段検証) / §11 (Report 機能独立章) 含む
- [x] **CI-FIX-1** `package-lock.json` 同期漏れ (b073cf1 で teams-js 追加時に lock 更新忘れ) — `npm install --package-lock-only` で再生成
- [x] **CI-FIX-2** `OnboardingSteps.test.tsx` を 4065336 後の現状 3 step に合わせ更新 (4 step 期待で常時 failure だった)
- [x] **CI-GREEN** `5903cbe` で API / Web / Tests 全 workflow green、本番デプロイ完了

**P2 ✅ 完了 (2026-05-21 午後)**:
- [x] **TB-N.B4** Tab 内 chrome 簡略化 — `AppShell.tsx` で `looksLikeTeamsHost()` + `getTeamsContext()` 検出 → Teams Tab iframe 内では sidebar + topbar を省略
- [x] ~~**TB-C4** Barge-in~~ — 8.5.M の単発 PlayPrompt 設計では概念的に不要。grep で残コード無し (`recording_loop.py:87` の `bargeInAllowed: True` は **Graph 録音 API の silent prompt 用パラメータ**で別概念、正しく True で OK)。クローズ。
- [x] **Z-3/Z-4** Zenn 記事推敲 — 数値最新化 (テスト 41→89 / arbiter 16→17)、未検証メトリクス削除 ("1.8×/12 件で計測" 等)、hypothesis 誤 claim 訂正、クロスリファレンス検証済 ← **残: YouTube URL 差し替え 2 箇所 (撮影後)**

**P2 残 (Time permitting)**:
- [ ] **POS-3** Zenn 記事 / デモ動画に「Facilitator との差別化」スライド ← **記事 §8 + Helmsman vs Facilitator 比較表は完了済、残: 動画スライド化のみ (D-3 撮影時に組み込み)**
- [ ] ~~**POS-4** Semantic Kernel 移行~~ → **Phase F (提出後)**

**今すぐ着手可能 (ブロッカー無し)**:
- D-1〜D-4 デモ動画台本ブラッシュアップ (Report scene を `docs/demo-numbers.md` に追記)
- Zenn 記事の最終推敲 + YouTube 動画 URL 差し替え (2 箇所 `REPLACE_ME`)
- README.md に Report 機能反映

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
