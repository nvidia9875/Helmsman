// Azure Communication Services — Teams Interop で Helmsman bot を会議に参加させる基盤
// Call Automation SDK + Media Streaming (WebSocket) で音声 in/out を扱う。
// data residency は Japan (会議参加者が日本想定)。

param acsName string

@description('Where call audio/transcripts are stored. Japan を選ぶと Speech も Japan リージョンと合う')
@allowed([
  'United States'
  'Europe'
  'Asia Pacific'
  'Australia'
  'Brazil'
  'Canada'
  'France'
  'Germany'
  'India'
  'Japan'
  'Korea'
  'Norway'
  'Switzerland'
  'United Arab Emirates'
  'United Kingdom'
])
param dataLocation string = 'Japan'

// ACS リソース自体は global (location 必須だが意味は無い)
resource acs 'Microsoft.Communication/CommunicationServices@2023-04-01' = {
  name: acsName
  location: 'global'
  properties: {
    dataLocation: dataLocation
  }
}

output id string = acs.id
output name string = acs.name
output immutableResourceId string = acs.properties.immutableResourceId
#disable-next-line outputs-should-not-contain-secrets
output connectionString string = acs.listKeys().primaryConnectionString
#disable-next-line outputs-should-not-contain-secrets
output primaryKey string = acs.listKeys().primaryKey
output endpoint string = 'https://${acs.name}.communication.azure.com/'
