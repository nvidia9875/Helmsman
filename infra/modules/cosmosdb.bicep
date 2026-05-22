// Cosmos DB for NoSQL (Serverless, 4 containers)

param location string
param accountName string

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: accountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless' // pay-per-RU, idle で課金なし
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    enableAutomaticFailover: false
    publicNetworkAccess: 'Enabled'
    disableKeyBasedMetadataWriteAccess: false
    minimalTlsVersion: 'Tls12'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: cosmosAccount
  name: 'helmsman'
  properties: {
    resource: {
      id: 'helmsman'
    }
  }
}

// containers (partition key パスは Python snake_case フィールドに合わせる)
var containers = [
  {
    name: 'meetings'
    partitionKey: '/organizer_id'
  }
  {
    name: 'participants'
    partitionKey: '/meeting_id'
  }
  {
    name: 'voiceprints'
    partitionKey: '/id'
  }
  {
    name: 'interventions'
    partitionKey: '/meeting_id'
  }
  {
    name: 'documents'
    partitionKey: '/meeting_id'
  }
  {
    name: 'groups'
    partitionKey: '/organizer_id'
  }
  {
    name: 'group_documents'
    partitionKey: '/group_id'
  }
  {
    name: 'meeting_reports'
    partitionKey: '/meeting_id'
  }
  {
    // Phase 7: 会議横断記憶 — DecisionCapture が高 confidence を出した瞬間に
    // write-through で 1 件ずつ格納。MemoryRetriever が将来会議で引く。
    name: 'decisions'
    partitionKey: '/organizer_id'
  }
  {
    // Phase 6: マルチモーダル — ブラウザ webcam の集計シグナル (nod/confusion/engagement)
    // を 4 秒 batch で受け取り保存。生フレームは保持しない (ADR-105/107)。
    name: 'face_signals'
    partitionKey: '/meeting_id'
  }
]

resource cosmosContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = [for c in containers: {
  parent: database
  name: c.name
  properties: {
    resource: {
      id: c.name
      partitionKey: {
        paths: [
          c.partitionKey
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}]

output accountName string = cosmosAccount.name
output endpoint string = cosmosAccount.properties.documentEndpoint
output databaseName string = database.name
#disable-next-line outputs-should-not-contain-secrets
output primaryKey string = cosmosAccount.listKeys().primaryMasterKey
