// Azure AI Search (Free SKU) — 文書ベクトル検索のための索引基盤
// Free SKU: 50 MB / 3 indexes / 1 service per subscription, $0/月。
// ハッカソンのデモには十分。本番スケール時は basic (~$75/月) に上げる。

param location string
param searchName string

@allowed([
  'free'
  'basic'
  'standard'
])
param sku string = 'free'

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: location
  sku: {
    name: sku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    // semanticSearch は basic 以上で free tier 利用可能、free SKU では指定不可
    semanticSearch: sku == 'free' ? null : 'free'
  }
}

output endpoint string = 'https://${search.name}.search.windows.net'
output name string = search.name
#disable-next-line outputs-should-not-contain-secrets
output adminKey string = search.listAdminKeys().primaryKey
