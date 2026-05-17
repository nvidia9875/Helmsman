# Helmsman 本番デプロイ手順

審査期間 (6/2–6/18) の稼働維持に必要な作業手順をまとめる。

---

## 全体像

| Component | Where | URL |
|---|---|---|
| Backend (FastAPI) | Azure Container Apps `helmsman-dev-api` | https://helmsman-dev-api.ashyocean-e634ae12.westus2.azurecontainerapps.io |
| Frontend (Vite/React) | Azure Static Web Apps `helmsman-dev-web` (Free SKU) | https://kind-glacier-0122f6400.7.azurestaticapps.net |
| Container Registry | `helmsmandevacr.azurecr.io` (Basic, admin-enabled) | n/a |
| Infra-as-code | Bicep (`infra/main.bicep`) | n/a |
| CI/CD | GitHub Actions (`api-deploy.yml`, `web-deploy.yml`) | n/a |

リソースグループ `rg-helmsman-dev` / location `westus2` / subscription `Azure subscription 1` (0a8207b9-...)。

---

## 1. 初回セットアップ (済) — 何をしたかの記録

このセクションは「ハッカソン中に Claude Code が実行した一連の操作」を、再現できるように記録したもの。
通常の運用では再実行不要。

### 1.1 Bicep 適用

```bash
AOAI_KEY="$(az cognitiveservices account keys list \
  --name aoai-helmsman-dev \
  --resource-group rg-helmsman-dev \
  --query key1 -o tsv)"

az deployment group create \
  --resource-group rg-helmsman-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json \
  --parameters existingOpenAIKey="$AOAI_KEY"
```

新規作成された主なリソース:

- `helmsman-dev-docintel` — Azure AI Document Intelligence (F0 / 無料 500 ページ/月)
- `helmsman-dev-search-zzfj7ngjdvn3s` — Azure AI Search (**Free SKU**, 50 MB / 3 indexes)
- `helmsman-dev-web` — Static Web Apps (Free)
- Cosmos `documents` コンテナ
- Blob `documents` コンテナ

既存リソースに env vars / secret refs を追加:

- Container App `helmsman-dev-api` に `AZURE_OPENAI_*` / `COSMOS_*` /
  `AZURE_STORAGE_*` / `AZURE_SEARCH_*` / `AZURE_DOCINTEL_*` を Key Vault-style
  secret ref で注入

### 1.2 Service Principal + Federated Credential (GitHub OIDC)

```bash
SUB_ID="0a8207b9-0e71-4926-9f8a-58ba20ed3a1b"

az ad sp create-for-rbac \
  --name "github-helmsman-deploy" \
  --role contributor \
  --scopes "/subscriptions/$SUB_ID/resourceGroups/rg-helmsman-dev"

APP_ID="238c12d8-82d9-4a75-a022-39e13fab20ea"  # 上で得た clientId

az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:nvidia9875/Helmsman:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 1.3 SWA デプロイトークン取得

```bash
az staticwebapp secrets list \
  --name helmsman-dev-web \
  --resource-group rg-helmsman-dev \
  --query properties.apiKey -o tsv
```

### 1.4 GitHub Secrets 登録 (5 件)

```bash
gh secret set AZURE_CLIENT_ID --body "238c12d8-82d9-4a75-a022-39e13fab20ea"
gh secret set AZURE_TENANT_ID --body "a83e1e15-f13a-47c8-8945-33c225ef0136"
gh secret set AZURE_SUBSCRIPTION_ID --body "0a8207b9-0e71-4926-9f8a-58ba20ed3a1b"
gh secret set PROD_API_BASE_URL --body "https://helmsman-dev-api.ashyocean-e634ae12.westus2.azurecontainerapps.io"
gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body "<SWA token>"
```

### 1.5 Subscription provider registration

`az containerapp up` 系が暗黙で要求する resource provider:

```bash
az provider register --namespace Microsoft.ContainerRegistry
# 1〜2 分待つ。az provider show -n Microsoft.ContainerRegistry --query registrationState
```

このサブスクは **ACR Tasks が disabled** だったため、build は GitHub runner 上で
`docker buildx` → push ACR で実行する設計に変更してある (`api-deploy.yml` 参照)。

---

## 2. 通常運用 (自動デプロイ)

`main` ブランチに push するだけで以下が並列に走る。

| Workflow | Trigger paths | やること |
|---|---|---|
| `api-deploy.yml` | `src/**`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `.dockerignore`, `README.md`, `.github/workflows/api-deploy.yml` | ACR をなければ作成 → runner で docker build → ACR に push → admin 認証で Container App に image swap |
| `web-deploy.yml` | `apps/web/**`, `.github/workflows/web-deploy.yml` | `npm ci && npm run build` (`VITE_API_BASE` を `PROD_API_BASE_URL` で注入) → SWA に upload |

両方とも secret が無い環境では skip するガードがある (`if: env.AZURE_CLIENT_ID != ''`)。

Bicep を変更したときだけ手動で再適用:

```bash
AOAI_KEY="$(az cognitiveservices account keys list \
  --name aoai-helmsman-dev --resource-group rg-helmsman-dev --query key1 -o tsv)"
az deployment group create \
  --resource-group rg-helmsman-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json \
  --parameters existingOpenAIKey="$AOAI_KEY"
```

---

## 3. 動作確認

```bash
API="https://helmsman-dev-api.ashyocean-e634ae12.westus2.azurecontainerapps.io"
SWA="https://kind-glacier-0122f6400.7.azurestaticapps.net"

curl "$API/health"          # {"status":"ok"}
curl "$API/health/config"   # 環境変数の注入状態
curl "$API/openapi.json" | jq '.paths | keys'
open "$SWA"                 # SWA フロントエンド
open "$API/docs"            # FastAPI Swagger UI
```

---

## 4. 審査期間 (6/2-6/18) の 24/7 稼働

- Container App は **scale-to-zero**。最初のリクエストでコールドスタート (~3-5 秒)。
- 審査員のアクセスでコールドスタートを許容しない場合:
  - **Option A** Bicep の `containerapps.bicep` で `minReplicas: 1` に変更 → 再 apply (コスト微増だが常時 1 replica)
  - **Option B** keepalive を GitHub Actions で 30 分おきに `/health` を叩く workflow を追加 (無料)
- 監視: ポータル `helmsman-dev-ai` (Application Insights) のメトリクス。エラー率 / レスポンス時間 / リクエスト数。

---

## 5. ロールバック

```bash
# 現在のリビジョン一覧
az containerapp revision list \
  --name helmsman-dev-api \
  --resource-group rg-helmsman-dev \
  --query '[].{name:name, active:properties.active, image:properties.template.containers[0].image, created:properties.createdTime}' \
  -o table

# 1 つ前を active 化 (multiple-revision モード必須なら先に変更)
az containerapp revision activate \
  --name helmsman-dev-api \
  --resource-group rg-helmsman-dev \
  --revision <previous-revision-name>

# image を特定タグに直接戻す手も簡単
az containerapp update \
  --name helmsman-dev-api \
  --resource-group rg-helmsman-dev \
  --image helmsmandevacr.azurecr.io/helmsman-api:<old-sha>
```

ACR に保存されているタグ:

```bash
az acr repository show-tags --name helmsmandevacr --repository helmsman-api -o tsv
```

---

## 6. コスト監視

- アプリ内ダッシュボード: 会議画面の「💰 LLM コスト」カード — 会議単位の Azure OpenAI 課金
- ポータル `Cost Management + Billing` を毎朝確認 (Goal: ¥22,500 / 月)
- `helmsman-monthly-budget` アラート (50% / 80% / 100%) は Day 0 で設定済

主要コスト見込み:

| Service | 課金タイプ | 目安 |
|---|---|---|
| Azure OpenAI (gpt-5.4 / mini) | 従量 (token) | 主因。会議 1 件 ~$0.10 程度想定 |
| Cosmos DB (Serverless) | 従量 (RU) | 数 USD / 月 |
| Container Apps | scale-to-zero + Consumption | アイドル時 $0 |
| Container Registry (Basic) | 固定 | ~$5/月 |
| AI Search (Free SKU) | $0 | 50 MB / 3 indexes 制約あり |
| Document Intelligence (F0) | $0 | 500 ページ/月まで |
| Static Web Apps (Free) | $0 | 100 GB 帯域/月 |
| Application Insights / Log Analytics | 5 GB 無料分内 | 5 GB 超で課金 |

---

## 7. ハマりやすい点 (今回踏んだ罠 = future-proof な記録)

1. **`Microsoft.ContainerRegistry` プロバイダーが未登録** だと `az containerapp up` が失敗。`az provider register` してから 1-2 分待つ。
2. **`az containerapp up --source` が `NoneType.linux` で落ちる** Azure CLI バグあり。本リポジトリは `acr build / runner-side docker build` パスを使うので影響なし (`api-deploy.yml` 参照)。
3. **ACR Tasks がサブスクリプションで禁止されている** ことがある (`TasksOperationsNotAllowed`)。`az acr build` を諦めて GitHub runner 上で docker build に切り替える。本リポジトリは既にそのパス。
4. **Managed Identity の AcrPull RBAC は伝搬に最大数分**。Container App が起動直後だと image pull できない。本リポジトリは admin 認証 (`az containerapp registry set --username/--password`) で確実に。
5. **`uv sync` の editable インストールは builder の `/build/src` を指す**。multi-stage で `/app/src` にコピーすると `import helmsman` が失敗。Dockerfile で `ENV PYTHONPATH=/app/src` を設定済。
6. **`pyproject.toml` で `readme = "README.md"` を宣言していると hatchling が builder で README を要求**。`Dockerfile` で `COPY ... README.md` + `.dockerignore` に `!README.md`。
7. **`/app/.venv/bin/uvicorn` の shim が cross-stage で壊れる**。Dockerfile の `CMD` を `["python", "-m", "uvicorn", ...]` に。

これら全て対処済 (`Dockerfile`, `.dockerignore`, `.github/workflows/api-deploy.yml`)。次回 push は build キャッシュも効いて 2-3 分で完了。
