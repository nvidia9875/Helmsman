# Helmsman 🎯

> Goal-driven AI meeting facilitator for Microsoft Teams
> Microsoft Agent Hackathon 2026 個人部門エントリ作品

会議のゴールを宣言するだけで、6+1のエージェントが論点を分解し、時間を管理し、議論の脱線を戻し、押し殺された反対意見を浮かび上がらせ、決定を構造化する。Microsoft Teams でも物理会議室でもハイブリッドでも、全員のデバイスに同期するサイドバーで会議の質を変える。

## 技術スタック

- **Microsoft Azure**: Container Apps / Functions / OpenAI / AI Speech / SignalR / Cosmos DB / AI Search / Communication Services
- **Microsoft AI**: Copilot Studio Multi-Agent / Azure AI Foundry Agent Service / gpt-4o / gpt-4o-realtime
- **Microsoft 365**: Teams Apps SDK / Graph API / Planner / Entra ID / Purview
- **Languages**: Python 3.12 (uv) / TypeScript (Node 20)

## ディレクトリ構成

```
.
├── src/helmsman/         # Python: エージェント・API
│   ├── agents/          # 6+1 Agent 実装
│   ├── api/             # FastAPI (Container Apps)
│   └── shared/          # 共有ユーティリティ
├── functions/            # Azure Functions
├── apps/
│   └── web/             # React Web App + PWA (TypeScript / Vite)
├── infra/                # Bicep (IaC)
└── .github/workflows/    # CI/CD
```

## セットアップ

### 前提
- macOS / Linux
- Homebrew
- Azure サブスクリプション
- Microsoft 365 Developer Tenant

### 環境構築

```bash
# Python 環境 (uv)
uv sync

# 仮想環境アクティベート
source .venv/bin/activate

# 開発サーバ起動 (例)
uv run uvicorn helmsman.api.main:app --reload
```

## ライセンス

MIT

## 開発期間

- 開始: 2026-05-16
- 提出締切: 2026-06-01
- 最終審査会: 2026-06-18
