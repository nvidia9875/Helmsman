// Azure Static Web Apps (Free SKU) — フロントエンド配信
// GitHub Actions の SWA トークンを使って `apps/web/dist` を upload する。
// Free SKU は 100 GB バンド幅 / 月、独自ドメイン 2 個まで。

param location string = 'eastasia' // SWA は限定リージョン
param staticWebAppName string

resource swa 'Microsoft.Web/staticSites@2024-04-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    allowConfigFileUpdates: true
    enterpriseGradeCdnStatus: 'Disabled'
  }
}

output name string = swa.name
output defaultHostName string = swa.properties.defaultHostname
#disable-next-line outputs-should-not-contain-secrets
output deploymentToken string = swa.listSecrets().properties.apiKey
