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

// User Assigned Managed Identity for GitHub Actions
resource githubIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${appName}-github-identity'
  location: location
}

// Federated Identity Credential for GitHub Actions OIDC
resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
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

// ⚠️ ロール割り当てはCLIで別途実行
// resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
//   name: guid(resourceGroup().id, githubIdentity.id, 'Contributor')
//   dependsOn: [
//     federatedCredential
//   ]
//   properties: {
//     roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // Contributor
//     principalId: githubIdentity.properties.principalId
//     principalType: 'ServicePrincipal'
//   }
// }

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

// Web App for Container
resource webApp 'Microsoft.Web/sites@2024-11-01' = {
  name: '${appName}-webapp'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|ghcr.io/${toLower(githubRepoOwner)}/${toLower(githubRepoName)}:latest'
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
          value: '8501'
        }
      ]
      alwaysOn: true
    }
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

// Key Vault Access Policy for Web App and GitHub Identity
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
