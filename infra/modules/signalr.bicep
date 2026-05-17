// Azure SignalR Service (Free tier for dev)

param location string
param signalRName string

resource signalR 'Microsoft.SignalRService/signalR@2024-03-01' = {
  name: signalRName
  location: location
  sku: {
    name: 'Free_F1'
    tier: 'Free'
    capacity: 1
  }
  kind: 'SignalR'
  properties: {
    features: [
      {
        flag: 'ServiceMode'
        value: 'Serverless'
      }
      {
        flag: 'EnableConnectivityLogs'
        value: 'True'
      }
    ]
    cors: {
      allowedOrigins: [
        '*' // dev only - 本番では絞る
      ]
    }
    // networkACLs は Free_F1 では未サポート
  }
}

output hostName string = signalR.properties.hostName
output id string = signalR.id
