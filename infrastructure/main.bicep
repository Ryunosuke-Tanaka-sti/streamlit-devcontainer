@description('アプリケーション名')
param appName string

@description('リソースグループの場所')
param location string = resourceGroup().location

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

// GitHub Identity に Web App の操作権限を付与（Website Contributor）
resource webAppRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(webApp.id, githubIdentity.id, 'de139f84-1756-47ae-9be6-808fbbe84772')
  scope: webApp
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'de139f84-1756-47ae-9be6-808fbbe84772') // Website Contributor
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    federatedCredential
  ]
}

// GitHub Identity に リソースグループレベルでの読み取り権限を付与（Reader）
resource readerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, githubIdentity.id, 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'acdd72a7-3385-48ef-bd42-f606fba81ae7') // Reader
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    federatedCredential
  ]
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
    authType: 'Anonymous'
    environmentVariables: [
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
    ]
    volumeMounts: []
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
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

// Key Vault Access Policy for Web App and GitHub Identity
resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2024-11-01' = {
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
