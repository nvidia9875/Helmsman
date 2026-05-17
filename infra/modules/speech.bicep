// Azure AI Speech (Standard S0, pay-per-use)

param location string
param speechName string

resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: speechName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'SpeechServices'
  properties: {
    customSubDomainName: speechName
    publicNetworkAccess: 'Enabled'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

output endpoint string = speech.properties.endpoint
output region string = speech.location
output name string = speech.name
#disable-next-line outputs-should-not-contain-secrets
output key string = speech.listKeys().key1
