# GitHub Actions デプロイ設定

## 前提条件

デプロイワークフローを実行する前に、GitHubリポジトリで以下の設定を行ってください：

### 1. 環境シークレット（環境ごと）

Settings > Environments > [production/staging] に移動し、以下を追加：

- `AZURE_CLIENT_ID`: Azure Managed IdentityのClient ID
- `AZURE_TENANT_ID`: AzureのTenant ID
- `AZURE_SUBSCRIPTION_ID`: AzureのSubscription ID

これらの値は `infrastructure/deploy.sh` スクリプトの実行時に出力されます。

### 2. 環境変数

同じ環境設定で以下を追加：

- `APP_NAME`: アプリケーション名（インフラストラクチャデプロイで使用した値と一致させる必要があります）

### 3. リポジトリ設定

GHCR (GitHub Container Registry) を使用するため、リポジトリでGitHub Packagesが有効になっていることを確認してください。

## ワークフローの実行

1. GitHubリポジトリのActionsタブに移動
2. "Deploy to Azure" ワークフローを選択
3. "Run workflow" をクリック
4. 環境（productionまたはstaging）を選択
5. "Run workflow" ボタンをクリック

## ワークフローの詳細

デプロイプロセスは2つのジョブで構成されています：

1. **build-and-push**: DockerイメージをビルドしてGHCRにプッシュ
2. **deploy**: OIDCを使用してAzureに認証し、イメージをAzure Web Appにデプロイ

このワークフローはOIDC認証を使用するため、Azureの認証情報をシークレットとして保存する必要がありません。