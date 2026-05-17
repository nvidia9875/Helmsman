// Helmsman main Bicep template
// Deploy with:
//   az deployment group create --resource-group rg-helmsman-dev --template-file main.bicep --parameters main.parameters.json

@description('プロジェクト名（リソース命名の prefix）')
param projectName string = 'helmsman'

@description('環境名 (dev / staging / prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param env string = 'dev'

@description('リージョン')
param location string = resourceGroup().location

@description('既存の Azure OpenAI リソース名 (CLI で別途作成済み)')
param existingOpenAIName string = 'aoai-helmsman-dev'

@description('既存 Azure OpenAI の API キー (Container Apps に secret として注入)。Key Vault 経由が望ましいが MVP は parameter で。')
@secure()
param existingOpenAIKey string = ''

@description('Container Apps に注入するアプリ イメージ (初回は hello world)')
param appImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('ACS Call Automation の webhook 送信先 (Container App FQDN)。初回 deploy 後に判明する FQDN を 2 回目以降に渡す。空文字なら ACS bot 機能はオフ。')
param containerAppCallbackBaseUrl string = 'https://helmsman-dev-api.ashyocean-e634ae12.westus2.azurecontainerapps.io'

@description('リソース命名の suffix（ユニーク性確保用）')
param resourceSuffix string = uniqueString(resourceGroup().id)

// ===== 命名規則 =====
var namePrefix = '${projectName}-${env}'
// Storage account name: 3-24 chars, lower-case alphanumeric only
var storageAccountName = take(toLower(replace('sthm${env}${resourceSuffix}', '-', '')), 24)
var functionAppName = '${namePrefix}-func'
var hostingPlanName = '${namePrefix}-plan'
var cosmosAccountName = '${namePrefix}-cosmos'
var signalRName = '${namePrefix}-signalr'
var keyVaultName = take('${namePrefix}-kv-${resourceSuffix}', 24)
var logAnalyticsName = '${namePrefix}-log'
var appInsightsName = '${namePrefix}-ai'
var containerAppsEnvName = '${namePrefix}-cae'
var containerAppName = '${namePrefix}-api'
var speechName = '${namePrefix}-speech'
var searchName = take('${namePrefix}-search-${resourceSuffix}', 60)
var docIntelName = take('${namePrefix}-docintel', 24)
var staticWebAppName = '${namePrefix}-web'
var acsName = '${namePrefix}-acs'

// ===== Modules =====
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    location: location
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    location: location
    storageAccountName: storageAccountName
  }
}

module cosmosdb 'modules/cosmosdb.bicep' = {
  name: 'cosmosdb-deployment'
  params: {
    location: location
    accountName: cosmosAccountName
  }
}

module signalr 'modules/signalr.bicep' = {
  name: 'signalr-deployment'
  params: {
    location: location
    signalRName: signalRName
  }
}

module speech 'modules/speech.bicep' = {
  name: 'speech-deployment'
  params: {
    location: location
    speechName: speechName
  }
}

module search 'modules/aisearch.bicep' = {
  name: 'search-deployment'
  params: {
    location: location
    searchName: searchName
  }
}

module docintel 'modules/docintel.bicep' = {
  name: 'docintel-deployment'
  params: {
    location: location
    docIntelName: docIntelName
    sku: 'F0'
  }
}

module staticwebapp 'modules/staticwebapp.bicep' = {
  name: 'staticwebapp-deployment'
  params: {
    staticWebAppName: staticWebAppName
  }
}

module acs 'modules/acs.bicep' = {
  name: 'acs-deployment'
  params: {
    acsName: acsName
    dataLocation: 'Japan'
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    location: location
    keyVaultName: keyVaultName
  }
}

module containerApps 'modules/containerapps.bicep' = {
  name: 'containerapps-deployment'
  params: {
    location: location
    environmentName: containerAppsEnvName
    appName: containerAppName
    image: appImage
    logAnalyticsCustomerId: monitoring.outputs.logAnalyticsCustomerId
    logAnalyticsPrimaryKey: monitoring.outputs.logAnalyticsPrimaryKey
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    azureOpenAIEndpoint: 'https://${existingOpenAIName}.cognitiveservices.azure.com/'
    azureOpenAIApiKey: existingOpenAIKey
    cosmosEndpoint: cosmosdb.outputs.endpoint
    cosmosKey: cosmosdb.outputs.primaryKey
    azureStorageConnectionString: storage.outputs.connectionString
    azureSearchEndpoint: search.outputs.endpoint
    azureSearchKey: search.outputs.adminKey
    azureDocIntelEndpoint: docintel.outputs.endpoint
    azureDocIntelKey: docintel.outputs.key
    azureSpeechKey: speech.outputs.key
    azureSpeechRegion: speech.outputs.region
    acsConnectionString: acs.outputs.connectionString
    acsCallbackBaseUrl: containerAppCallbackBaseUrl
  }
}

// Functions は新規 sub の VM クォータ不足のため後日デプロイ
// Phase 1-2 は Container Apps の FastAPI で全機能実装可能
// module functions 'modules/functions.bicep' = {
//   name: 'functions-deployment'
//   params: {
//     location: location
//     functionAppName: functionAppName
//     hostingPlanName: hostingPlanName
//     storageAccountName: storage.outputs.storageAccountName
//     storageAccountKey: storage.outputs.storageAccountKey
//     appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
//   }
// }

// ===== Outputs =====
output cosmosEndpoint string = cosmosdb.outputs.endpoint
output cosmosAccountName string = cosmosdb.outputs.accountName
output signalRHostName string = signalr.outputs.hostName
output speechEndpoint string = speech.outputs.endpoint
output speechRegion string = speech.outputs.region
output containerAppFqdn string = containerApps.outputs.fqdn
// output functionAppHostName string = functions.outputs.functionAppHostName
output keyVaultUri string = keyVault.outputs.vaultUri
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output openAIEndpoint string = 'https://${existingOpenAIName}.cognitiveservices.azure.com/'
output searchEndpoint string = search.outputs.endpoint
output searchServiceName string = search.outputs.name
output docIntelEndpoint string = docintel.outputs.endpoint
output documentsContainerName string = storage.outputs.documentsContainerName
output staticWebAppHostName string = staticwebapp.outputs.defaultHostName
output staticWebAppName string = staticwebapp.outputs.name
output acsName string = acs.outputs.name
output acsEndpoint string = acs.outputs.endpoint
