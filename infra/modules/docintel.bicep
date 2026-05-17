// Azure AI Document Intelligence (FormRecognizer brand) — PDF/Word/PPT のテキスト抽出
// S0 は標準。F0 は無料枠 (500 ページ/月) でハッカソンに十分。

param location string
param docIntelName string

@allowed([
  'F0'
  'S0'
])
param sku string = 'F0'

resource docintel 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: docIntelName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: docIntelName
    publicNetworkAccess: 'Enabled'
  }
}

output endpoint string = docintel.properties.endpoint
output name string = docintel.name
#disable-next-line outputs-should-not-contain-secrets
output key string = docintel.listKeys().key1
