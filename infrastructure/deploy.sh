#!/bin/bash

# OIDC対応 2段階デプロイスクリプト（統合版）

# .envファイルの読み込み
if [ -f .env ]; then
    echo ".envファイルを読み込み中..."
    set -a  # 自動的にexportする
    source .env
    set +a  # 自動exportを無効化
else
    echo "エラー: .envファイルが見つかりません。"
    echo ".env.exampleをコピーして.envを作成し、値を設定してください。"
    echo "cp .env.example .env"
    exit 1
fi

# 必須変数のチェック
if [ -z "$RESOURCE_GROUP" ] || [ -z "$GITHUB_TOKEN" ] || [ -z "$APP_NAME" ] || [ -z "$GITHUB_REPO_OWNER" ] || [ -z "$GITHUB_REPO_NAME" ] || [ -z "$LOCATION" ]; then
    echo "エラー: 必須の環境変数が設定されていません。"
    echo ".envファイルを確認してください。"
    echo "必要な変数: RESOURCE_GROUP, GITHUB_TOKEN, APP_NAME, GITHUB_REPO_OWNER, GITHUB_REPO_NAME, LOCATION"
    echo ""
    echo "現在の値:"
    echo "RESOURCE_GROUP: ${RESOURCE_GROUP:-未設定}"
    echo "APP_NAME: ${APP_NAME:-未設定}" 
    echo "GITHUB_REPO_OWNER: ${GITHUB_REPO_OWNER:-未設定}"
    echo "GITHUB_REPO_NAME: ${GITHUB_REPO_NAME:-未設定}"
    echo "LOCATION: ${LOCATION:-未設定}"
    echo "GITHUB_TOKEN: ${GITHUB_TOKEN:+設定済み}"
    exit 1
fi

KEY_VAULT_NAME="kv-${APP_NAME}"
DEPLOYMENT_NAME="deployment-$(date +%Y%m%d-%H%M%S)"

echo "🚀 OIDC対応 2段階Azureデプロイを開始します..."
echo "リソースグループ: $RESOURCE_GROUP"
echo "アプリ名: $APP_NAME"
echo "GitHub: $GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"
echo ""

# =============================================================================
# Stage 1: Bicepテンプレートでリソース作成（ロール割り当て除く）
# =============================================================================
echo "📦 Stage 1: Azure リソース作成中..."

echo "1-1. Bicepテンプレートの構文チェック..."
if ! az bicep build --file main.bicep --stdout > /dev/null 2>&1; then
    echo "❌ Bicepテンプレートの構文エラー"
    az bicep build --file main.bicep --stdout
    exit 1
fi

echo "✅ Bicepテンプレートの構文チェック成功"
echo ""

echo "1-2. Bicepテンプレートをデプロイ中..."

# 変数の値を確認
echo "デプロイパラメーター:"
echo "  appName: $APP_NAME"
echo "  location: $LOCATION"
echo "  githubRepoOwner: $GITHUB_REPO_OWNER"
echo "  githubRepoName: $GITHUB_REPO_NAME"
echo ""

# Bicepテンプレートをデプロイ（ロール割り当てなし版）
# main.parameters.json が存在する場合はそれを使用、なければ環境変数を使用
if [ -f "main.parameters.json" ]; then
    echo "main.parameters.json を使用してデプロイします"
    az deployment group create \
      --resource-group "$RESOURCE_GROUP" \
      --template-file "main.bicep" \
      --parameters "@main.parameters.json" \
      --name "$DEPLOYMENT_NAME"
else
    echo "環境変数を使用してデプロイします"
    az deployment group create \
      --resource-group "$RESOURCE_GROUP" \
      --template-file "main.bicep" \
      --parameters \
        appName="$APP_NAME" \
        location="$LOCATION" \
        githubRepoOwner="$GITHUB_REPO_OWNER" \
        githubRepoName="$GITHUB_REPO_NAME" \
      --name "$DEPLOYMENT_NAME"
fi

# デプロイが成功したか確認
if [ $? -eq 0 ]; then
    echo "✅ Stage 1: Bicepデプロイ成功"
else
    echo "❌ Stage 1: Bicepデプロイ失敗"
    exit 1
fi

echo ""

# =============================================================================
# Stage 2: CLI で権限割り当て
# =============================================================================
echo "🔐 Stage 2: 権限割り当て実行中..."

echo "2-1. デプロイ結果から情報を取得中..."
DEPLOYMENT_OUTPUT_FILE="/tmp/deployment_output_$$.json"
az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$DEPLOYMENT_NAME" \
  --query properties.outputs \
  --output json > "$DEPLOYMENT_OUTPUT_FILE"

GITHUB_CLIENT_ID=$(jq -r '.githubIdentityClientId.value' < "$DEPLOYMENT_OUTPUT_FILE")
IDENTITY_PRINCIPAL_ID=$(jq -r '.githubIdentityPrincipalId.value' < "$DEPLOYMENT_OUTPUT_FILE")
WEB_APP_URL=$(jq -r '.webAppUrl.value' < "$DEPLOYMENT_OUTPUT_FILE")

echo "GitHub Identity Client ID: $GITHUB_CLIENT_ID"
echo "Identity Principal ID: $IDENTITY_PRINCIPAL_ID"
echo ""

echo "2-2. Managed Identity にContributorロールを割り当て中..."
az role assignment create \
  --assignee "$IDENTITY_PRINCIPAL_ID" \
  --role Contributor \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP"

echo ""

# =============================================================================
# Stage 3: Key Vault設定とWeb App再起動
# =============================================================================
echo "🔑 Stage 3: Key Vaultとアプリケーション設定..."

# 現在のユーザーのオブジェクトIDを取得
CURRENT_USER_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

echo "3-1. 現在のユーザーにKey Vaultのアクセス権限を付与中..."
az keyvault set-policy \
  --name "$KEY_VAULT_NAME" \
  --object-id "$CURRENT_USER_OBJECT_ID" \
  --secret-permissions get list set delete \
  --output none

if [ $? -eq 0 ]; then
    echo "✅ Key Vaultアクセス権限を付与完了"
else
    echo "⚠️  Key Vaultアクセス権限の付与に失敗しました（既に権限がある可能性があります）"
fi

echo ""
echo "3-2. Key Vaultにシークレットを設定中..."
az keyvault secret set \
  --vault-name "$KEY_VAULT_NAME" \
  --name "github-token" \
  --value "$GITHUB_TOKEN" \
  --output none

echo "✅ GitHub token をKey Vaultに設定完了"
echo ""

echo "3-3. Web Appを再起動してシークレットを反映中..."
az webapp restart \
  --name "${APP_NAME}-webapp" \
  --resource-group "$RESOURCE_GROUP" \
  --output none

echo "✅ Web App再起動完了"
echo ""

# =============================================================================
# Stage 4: GitHub Secrets設定
# =============================================================================
echo "🐙 Stage 4: GitHub Secrets設定..."

# GitHub リポジトリ情報（.envから取得、フォールバックでGitから取得）
REPO_OWNER=${GITHUB_REPO_OWNER}
REPO_NAME=${GITHUB_REPO_NAME}

# .envに値がない場合はGitリモートから取得を試行
if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
    echo "⚠️  .envにGitHub情報がありません。Gitリモート情報から取得を試行..."
    GIT_REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
    if [ -n "$GIT_REMOTE_URL" ]; then
        REPO_OWNER=$(echo "$GIT_REMOTE_URL" | sed -n 's/.*github\.com[:|\/]\([^/]*\)\/.*/\1/p')
        REPO_NAME=$(echo "$GIT_REMOTE_URL" | sed -n 's/.*github\.com[:|\/][^/]*\/\([^.]*\)\.git/\1/p' | sed 's/\.git$//')
    fi
fi

if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
    echo "❌ GitHub リポジトリ情報を取得できませんでした。"
    echo ".envファイルにGITHUB_REPO_OWNERとGITHUB_REPO_NAMEを設定してください。"
    echo ""
    echo "🔧 GitHub Actions に設定が必要な値："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "【環境シークレット (Settings > Environments > production)】"
    echo "AZURE_CLIENT_ID: $GITHUB_CLIENT_ID"
    echo "AZURE_TENANT_ID: $(az account show --query tenantId -o tsv)"
    echo "AZURE_SUBSCRIPTION_ID: $(az account show --query id -o tsv)"
    echo ""
    echo "【環境変数 (Settings > Environments > production)】"
    echo "APP_NAME: $APP_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "GitHub リポジトリ: $REPO_OWNER/$REPO_NAME"
    
    # Azure情報を取得
    AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)
    AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    
    # GitHub CLI の存在確認
    if ! command -v gh &> /dev/null; then
        echo "⚠️  GitHub CLI (gh) がインストールされていません。"
        echo ""
        echo "🔧 GitHub Actions に設定が必要な値："
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "【環境シークレット (Settings > Environments > production)】"
        echo "AZURE_CLIENT_ID: $GITHUB_CLIENT_ID"
        echo "AZURE_TENANT_ID: $AZURE_TENANT_ID"
        echo "AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID"
        echo ""
        echo "【環境変数 (Settings > Environments > production)】"
        echo "APP_NAME: $APP_NAME"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    else
        echo "4-1. GitHub CLIで production environment にシークレットを設定中..."
        
        # GitHub CLI でシークレットを設定
        echo "$GITHUB_CLIENT_ID" | gh secret set AZURE_CLIENT_ID --repo "$REPO_OWNER/$REPO_NAME" --env production
        echo "$AZURE_TENANT_ID" | gh secret set AZURE_TENANT_ID --repo "$REPO_OWNER/$REPO_NAME" --env production  
        echo "$AZURE_SUBSCRIPTION_ID" | gh secret set AZURE_SUBSCRIPTION_ID --repo "$REPO_OWNER/$REPO_NAME" --env production
        
        # 環境変数も設定
        gh variable set APP_NAME --repo "$REPO_OWNER/$REPO_NAME" --env production --body "$APP_NAME"
        
        if [ $? -eq 0 ]; then
            echo "✅ GitHub Secrets と環境変数を production 環境に設定完了"
        else
            echo "❌ GitHub Secrets設定でエラーが発生しました"
            echo ""
            echo "🔧 手動で設定してください："
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "【環境シークレット】"
            echo "AZURE_CLIENT_ID: $GITHUB_CLIENT_ID"
            echo "AZURE_TENANT_ID: $AZURE_TENANT_ID"
            echo "AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID"
            echo ""
            echo "【環境変数】"
            echo "APP_NAME: $APP_NAME"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        fi
    fi
fi

# 一時ファイルをクリーンアップ
rm -f "$DEPLOYMENT_OUTPUT_FILE"

echo ""
echo "🎉 2段階デプロイ完了！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 デプロイ結果サマリー:"
echo "  🌐 Web App URL: $WEB_APP_URL"
echo "  🆔 Client ID: $GITHUB_CLIENT_ID"
echo "  🏷️  Principal ID: $IDENTITY_PRINCIPAL_ID"
echo "  🔑 Key Vault: $KEY_VAULT_NAME"
echo ""
echo "📋 次のステップ:"
echo "  1. GitHub Actionsワークフローを作成"
echo "  2. Dockerfileとアプリケーションコードの準備"
echo "  3. 初回デプロイテスト"
echo ""
echo "📖 詳細な設定手順: README.md を参照"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"