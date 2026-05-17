// Key Vault (シークレット集約用)

param location string
param keyVaultName string

resource keyVault 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7 // dev: 短め
    // enablePurgeProtection は一度 true にすると戻せないので dev では指定しない
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

output vaultUri string = keyVault.properties.vaultUri
output keyVaultName string = keyVault.name
