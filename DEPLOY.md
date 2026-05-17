# Helmsman 本番デプロイ手順

審査期間 (6/2–6/18) の稼働維持に必要な作業手順をまとめる。

---

## 全体像

- **Backend (FastAPI)**: Azure Container Apps (`rg-helmsman-dev/helmsman-dev-api`)
- **Frontend (Vite/React)**: Azure Static Web Apps (Free SKU)
- **Infra**: Bicep (`infra/main.bicep`) で全 Azure リソースを宣言
- **CI/CD**: GitHub Actions (`.github/workflows/api-deploy.yml`, `web-deploy.yml`)

## 1 回目: 手動セットアップ

### 1.1 Azure リソースを Bicep で更新

新しく追加した 3 モジュール (AI Search / Document Intelligence / Static Web Apps) と
コンテナ env vars を反映する。

```bash
cd infra

# Azure OpenAI の API キーを Container App に渡す (Bicep が secret 化して env に注入)
AOAI_KEY="$(az cognitiveservices account keys list \
  --name aoai-helmsman-dev \
  --resource-group rg-helmsman-dev \
  --query key1 -o tsv)"

az deployment group create \
  --resource-group rg-helmsman-dev \
  --template-file main.bicep \
  --parameters main.parameters.json \
  --parameters existingOpenAIKey="$AOAI_KEY"
```

出力に含まれる以下の値をメモする (GitHub secrets に登録するため):

| Bicep output | 用途 |
|---|---|
| `containerAppFqdn` | フロントエンドの `VITE_API_BASE` に設定する |
| `staticWebAppHostName` | 審査員に提示するフロント URL |

### 1.2 Service Principal を作って GitHub に登録

```bash
# Subscription ID を取得
SUB_ID="$(az account show --query id -o tsv)"

# Federated identity 付き SP を作成 (OIDC で動く)
az ad sp create-for-rbac \
  --name "github-helmsman-deploy" \
  --role contributor \
  --scopes "/subscriptions/$SUB_ID/resourceGroups/rg-helmsman-dev" \
  --json-auth
```

返ってきた JSON から `clientId` / `tenantId` / `subscriptionId` を控える。
さらに OIDC 用 federated credential を追加:

```bash
APP_ID="<上で得た clientId>"

az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:nvidia9875/Helmsman:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 1.3 Static Web Apps のデプロイトークンを取得

Bicep が SWA を作るので、その API キーを取り出して GitHub Secret に登録:

```bash
az staticwebapp secrets list \
  --name helmsman-dev-web \
  --resource-group rg-helmsman-dev \
  --query properties.apiKey -o tsv
```

### 1.4 GitHub Secrets を登録

リポジトリ Settings → Secrets and variables → Actions:

| Secret | 値 |
|---|---|
| `AZURE_CLIENT_ID` | 上の SP の clientId |
| `AZURE_TENANT_ID` | 上の SP の tenantId |
| `AZURE_SUBSCRIPTION_ID` | サブスクリプション ID |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | 1.3 で取得した SWA トークン |
| `PROD_API_BASE_URL` | `https://<containerAppFqdn>` (1.1 の output) |

## 2 回目以降: 自動デプロイ

`main` ブランチに push すると以下が走る:

- `src/**` 変更 → `api-deploy.yml` が Container App を再ビルド + 更新
- `apps/web/**` 変更 → `web-deploy.yml` がフロントを再ビルド + SWA に upload
- Bicep を変更したら `cd infra && az deployment group create ...` を手動実行

## 3. 動作確認

```bash
# API
curl https://<containerAppFqdn>/health

# Frontend
open "https://<staticWebAppHostName>"
```

## 4. 24/7 稼働 (審査期間)

- Container App は scale-to-zero (idle 0 replicas)。最初のリクエストでコールドスタート (~3-5 秒)。
- 審査員アクセス時のコールドスタート回避: workflow に keepalive (毎 30 分 `/health` を叩く) を追加するか、minReplicas を 1 に上げる
  - 後者は Bicep の `containerapps.bicep` で `minReplicas: 1` に変更し、再デプロイ
- Application Insights で 24 時間以内のエラー監視: ポータルから `helmsman-dev-ai` のメトリクス

## 5. ロールバック

```bash
# 直前のリビジョンに戻す
az containerapp revision list \
  --name helmsman-dev-api \
  --resource-group rg-helmsman-dev \
  --query '[].{name:name, active:properties.active, created:properties.createdTime}'

az containerapp revision activate \
  --name helmsman-dev-api \
  --resource-group rg-helmsman-dev \
  --revision <previous-revision-name>
```

## 6. コスト監視

- Azure Cost Analysis を毎朝確認 (Goal: ¥22,500 / 月)
- アプリ内ダッシュボード: 会議画面の「💰 LLM コスト」カードで会議単位の OpenAI 課金が確認できる
- `helmsman-monthly-budget` アラート (50% / 80% / 100%) は Day 0 で設定済
