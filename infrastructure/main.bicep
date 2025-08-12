@description('アプリケーション名')
param appName string

@description('リソースグループの場所')
param location string = resourceGroup().location

@description('Functions App用の場所 (Linux対応リージョン)')
param functionsLocation string = 'eastus'

@description('App Service Planのサイズ')
@allowed(['B1', 'B2', 'B3', 'S1', 'S2', 'S3', 'P1V2', 'P2V2', 'P3V2'])
param appServicePlanSku string = 'B1'

@description('GitHubリポジトリのオーナー名')
param githubRepoOwner string

@description('GitHubリポジトリ名')
param githubRepoName string

@description('GitHub環境名（main, staging, production等）')
param githubEnvironment string = 'production'

@description('コンテナのポート番号')
param containerPort string = '8501'

// User Assigned Managed Identity for GitHub Actions
resource githubIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: '${appName}-github-identity'
  location: location
}

// Federated Identity Credential for GitHub Actions OIDC
resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2024-11-30' = {
  parent: githubIdentity
  name: 'github-federated-credential'
  properties: {
    audiences: [
      'api://AzureADTokenExchange'
    ]
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepoOwner}/${githubRepoName}:environment:${githubEnvironment}'
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: '${appName}-plan'
  location: location
  kind: 'linux'
  properties: {
    reserved: true
  }
  sku: {
    name: appServicePlanSku
  }
}

// Web App for Container (サイドカー対応)
resource webApp 'Microsoft.Web/sites@2024-11-01' = {
  name: '${appName}-webapp'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'sitecontainers'  // サイドカー対応に変更
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://ghcr.io'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: githubRepoOwner
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=github-token)'
        }
        {
          name: 'WEBSITES_PORT'
          value: containerPort
        }
        {
          name: 'DOCKER_ENABLE_CI'
          value: 'true'
        }
        {
          name: 'PORT'
          value: containerPort
        }
        {
          name: 'GITHUB_REPO_OWNER'
          value: githubRepoOwner
        }
        {
          name: 'GITHUB_REPO_NAME'
          value: githubRepoName
        }
        // Application Insights
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: applicationInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
        // X API設定
        {
          name: 'X_CLIENT_ID'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=x-client-id)'
        }
        {
          name: 'X_CLIENT_SECRET'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=x-client-secret)'
        }
        {
          name: 'X_REDIRECT_URI'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=x-redirect-uri)'
        }
        // Firebase/Firestore設定
        {
          name: 'FIREBASE_PROJECT_ID'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=firebase-project-id)'
        }
        {
          name: 'FIREBASE_SERVICE_ACCOUNT_BASE64'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=firebase-service-account-base64)'
        }
        {
          name: 'ENCRYPTION_KEY'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=encryption-key)'
        }
        {
          name: 'FIRESTORE_REGION'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=firestore-region)'
        }
      ]
      alwaysOn: true
    }
  }
}

// メインコンテナの設定（サイドカー）
resource mainContainer 'Microsoft.Web/sites/sitecontainers@2024-04-01' = {
  parent: webApp
  name: 'main-container'
  properties: {
    image: 'ghcr.io/${toLower(githubRepoOwner)}/${toLower(githubRepoName)}:latest'
    isMain: true
    targetPort: containerPort
    volumeMounts: []
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${appName}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []
    enableRbacAuthorization: false
  }
}

// X OAuth Secrets will be set via Azure CLI in deploy.sh
// This ensures sensitive data is not stored in Bicep templates or source control

// Storage Account for Azure Functions
resource storageAccount 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: toLower('${replace(appName, '-', '')}funcstor')
  location: functionsLocation
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    accessTier: 'Hot'
    encryption: {
      services: {
        file: {
          enabled: true
        }
        blob: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

// Function App Service Plan (Consumption Plan)
resource functionAppServicePlan 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: '${appName}-function-plan'
  location: functionsLocation
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true  // Linux
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2024-11-01' = {
  name: '${appName}-functions'
  location: functionsLocation
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionAppServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        // Azure Functions 必須設定
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower('${appName}-functions')
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        // Application Insights
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: applicationInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
        // Firebase/Firestore設定 (自動投稿に必要)
        {
          name: 'FIREBASE_PROJECT_ID'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=firebase-project-id)'
        }
        {
          name: 'FIREBASE_SERVICE_ACCOUNT_BASE64'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=firebase-service-account-base64)'
        }
        {
          name: 'ENCRYPTION_KEY'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=encryption-key)'
        }
      ]
      use32BitWorkerProcess: false
      ftpsState: 'Disabled'
      cors: {
        allowedOrigins: ['https://portal.azure.com']
      }
    }
    httpsOnly: true
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${appName}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
  }
}

// Key Vault Access Policy for Web App, Functions App and GitHub Identity
resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  parent: keyVault
  name: 'add'
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: webApp.identity.principalId
        permissions: {
          secrets: ['get']
        }
      }
      {
        tenantId: subscription().tenantId
        objectId: functionApp.identity.principalId
        permissions: {
          secrets: ['get']
        }
      }
      {
        tenantId: subscription().tenantId
        objectId: githubIdentity.properties.principalId
        permissions: {
          secrets: ['get', 'set', 'list']
        }
      }
    ]
  }
}


// 出力
output webAppName string = webApp.name
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output keyVaultName string = keyVault.name
output githubIdentityClientId string = githubIdentity.properties.clientId
output githubIdentityPrincipalId string = githubIdentity.properties.principalId
output federatedCredentialSubject string = federatedCredential.properties.subject
output resourceGroupName string = resourceGroup().name
output mainContainerName string = mainContainer.name
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output storageAccountName string = storageAccount.name
output applicationInsightsName string = applicationInsights.name
