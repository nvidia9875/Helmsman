// Container Apps Environment + 初回 App
// scale-to-zero で idle 課金ゼロ

param location string
param environmentName string
param appName string
param image string
param logAnalyticsCustomerId string
@secure()
param logAnalyticsPrimaryKey string
param appInsightsConnectionString string

// ----- アプリ ランタイム env 注入 (本番デプロイ用、空文字列なら省略) -----
@description('Azure OpenAI endpoint URL')
param azureOpenAIEndpoint string = ''
@secure()
@description('Azure OpenAI API key')
param azureOpenAIApiKey string = ''
@description('Cosmos DB endpoint URL')
param cosmosEndpoint string = ''
@secure()
@description('Cosmos DB primary key')
param cosmosKey string = ''
@secure()
@description('Azure Storage account connection string')
param azureStorageConnectionString string = ''
@description('Azure AI Search endpoint URL')
param azureSearchEndpoint string = ''
@secure()
@description('Azure AI Search admin key')
param azureSearchKey string = ''
@description('Azure AI Document Intelligence endpoint URL')
param azureDocIntelEndpoint string = ''
@secure()
@description('Azure AI Document Intelligence key')
param azureDocIntelKey string = ''

resource environment 'Microsoft.App/managedEnvironments@2024-10-02-preview' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsPrimaryKey
      }
    }
    daprAIConnectionString: appInsightsConnectionString
    zoneRedundant: false // dev
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// Secrets — 空文字列なら宣言だけ残して未使用にする
var appSecrets = [
  { name: 'azure-openai-api-key', value: azureOpenAIApiKey }
  { name: 'cosmos-key', value: cosmosKey }
  { name: 'azure-storage-connection-string', value: azureStorageConnectionString }
  { name: 'azure-search-key', value: azureSearchKey }
  { name: 'azure-docintel-key', value: azureDocIntelKey }
]

// envvars — 値が空でない設定のみ Container に渡す
var envBase = [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsightsConnectionString
  }
]
var envOpenAI = empty(azureOpenAIEndpoint) ? [] : [
  { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenAIEndpoint }
  { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-api-key' }
]
var envCosmos = empty(cosmosEndpoint) ? [] : [
  { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
  { name: 'COSMOS_KEY', secretRef: 'cosmos-key' }
]
var envStorage = empty(azureStorageConnectionString) ? [] : [
  { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'azure-storage-connection-string' }
]
var envSearch = empty(azureSearchEndpoint) ? [] : [
  { name: 'AZURE_SEARCH_ENDPOINT', value: azureSearchEndpoint }
  { name: 'AZURE_SEARCH_KEY', secretRef: 'azure-search-key' }
]
var envDocIntel = empty(azureDocIntelEndpoint) ? [] : [
  { name: 'AZURE_DOCINTEL_ENDPOINT', value: azureDocIntelEndpoint }
  { name: 'AZURE_DOCINTEL_KEY', secretRef: 'azure-docintel-key' }
]
var appEnv = concat(envBase, envOpenAI, envCosmos, envStorage, envSearch, envDocIntel)

resource containerApp 'Microsoft.App/containerApps@2024-10-02-preview' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        allowInsecure: false
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: [
            '*' // dev only
          ]
          allowedMethods: [
            'GET'
            'POST'
            'PUT'
            'DELETE'
            'OPTIONS'
          ]
          allowedHeaders: [
            '*'
          ]
        }
      }
      secrets: [for s in appSecrets: {
        name: s.name
        value: s.value
      }]
    }
    template: {
      containers: [
        {
          name: 'helmsman-api'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: appEnv
        }
      ]
      scale: {
        minReplicas: 0 // scale-to-zero
        maxReplicas: 3
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output appName string = containerApp.name
output environmentId string = environment.id
output principalId string = containerApp.identity.principalId
