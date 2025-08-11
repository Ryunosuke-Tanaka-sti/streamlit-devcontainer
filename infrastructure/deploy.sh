#!/bin/bash

# OIDC対応 2段階デプロイスクリプト（責務分離版 - CLI権限管理）

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
if [ -z "$RESOURCE_GROUP" ] || [ -z "$GITHUB_TOKEN" ] || [ -z "$APP_NAME" ] || [ -z "$GITHUB_REPO_OWNER" ] || [ -z "$GITHUB_REPO_NAME" ] || [ -z "$LOCATION" ] || [ -z "$X_CLIENT_ID" ] || [ -z "$X_CLIENT_SECRET" ] || [ -z "$X_REDIRECT_URI" ]; then
    echo "エラー: 必須の環境変数が設定されていません。"
    echo ".envファイルを確認してください。"
    echo "必要な変数: RESOURCE_GROUP, GITHUB_TOKEN, APP_NAME, GITHUB_REPO_OWNER, GITHUB_REPO_NAME, LOCATION, X_CLIENT_ID, X_CLIENT_SECRET, X_REDIRECT_URI"
    echo ""
    echo "現在の値:"
    echo "RESOURCE_GROUP: ${RESOURCE_GROUP:-未設定}"
    echo "APP_NAME: ${APP_NAME:-未設定}" 
    echo "GITHUB_REPO_OWNER: ${GITHUB_REPO_OWNER:-未設定}"
    echo "GITHUB_REPO_NAME: ${GITHUB_REPO_NAME:-未設定}"
    echo "LOCATION: ${LOCATION:-未設定}"
    echo "GITHUB_TOKEN: ${GITHUB_TOKEN:+設定済み}"
    echo "X_CLIENT_ID: ${X_CLIENT_ID:+設定済み}"
    echo "X_CLIENT_SECRET: ${X_CLIENT_SECRET:+設定済み}"
    echo "X_REDIRECT_URI: ${X_REDIRECT_URI:-未設定}"
    exit 1
fi

# Firebase/Firestore関連の変数チェック
echo ""
echo "Firebase/Firestore設定の確認..."
echo "FIREBASE_PROJECT_ID: ${FIREBASE_PROJECT_ID:-未設定}"
echo "FIREBASE_SERVICE_ACCOUNT_BASE64: ${FIREBASE_SERVICE_ACCOUNT_BASE64:+設定済み}"
echo "ENCRYPTION_KEY: ${ENCRYPTION_KEY:+設定済み}"
echo "FIRESTORE_REGION: ${FIRESTORE_REGION:-asia-northeast1}"

# Firebase必須設定のチェック
if [ -z "$FIREBASE_PROJECT_ID" ] || [ -z "$FIREBASE_SERVICE_ACCOUNT_BASE64" ] || [ -z "$ENCRYPTION_KEY" ]; then
    echo ""
    echo "⚠️  Firebase/Firestore設定が不完全です。"
    echo "以下の設定が必要です："
    echo "  - FIREBASE_PROJECT_ID: Firebase プロジェクトID"
    echo "  - FIREBASE_SERVICE_ACCOUNT_BASE64: Base64エンコードされたサービスアカウントキー"
    echo "  - ENCRYPTION_KEY: トークン暗号化用のFernetキー"
    echo ""
    echo "Firebase機能を使用しない場合はこのまま続行できますが、"
    echo "投稿履歴とFirestore連携機能は動作しません。"
    echo ""
    read -p "Firebase設定なしで続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Firebase設定を完了してから再実行してください。"
        exit 1
    fi
    FIREBASE_ENABLED=false
else
    FIREBASE_ENABLED=true
fi

KEY_VAULT_NAME="kv-${APP_NAME}"
DEPLOYMENT_NAME="deployment-$(date +%Y%m%d-%H%M%S)"

echo "🚀 OIDC対応 2段階Azureデプロイを開始します..."
echo "リソースグループ: $RESOURCE_GROUP"
echo "アプリ名: $APP_NAME"
echo "GitHub: $GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"
echo ""

# =============================================================================
# Stage 1: Bicepテンプレートでリソース作成（権限設定はCLIで実行）
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

echo "1-2. Bicepテンプレートをデプロイ中（インフラリソースのみ）..."

# 変数の値を確認
echo "デプロイパラメーター:"
echo "  appName: $APP_NAME"
echo "  location: $LOCATION"
echo "  githubRepoOwner: $GITHUB_REPO_OWNER"
echo "  githubRepoName: $GITHUB_REPO_NAME"
echo "  X OAuth設定: 設定済み"
echo ""

# Bicepテンプレートをデプロイ（インフラリソースのみ、権限設定は後でCLI実行）
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
    echo "✅ Stage 1: Bicepデプロイ成功（インフラリソース作成完了）"
else
    echo "❌ Stage 1: Bicepデプロイ失敗"
    exit 1
fi

echo ""

# =============================================================================
# Stage 2: CLI権限設定とKey Vault設定
# =============================================================================
echo "🔑 Stage 2: CLI権限設定とKey Vault設定..."

echo "2-1. デプロイ結果から情報を取得中..."
DEPLOYMENT_OUTPUT_FILE="/tmp/deployment_output_$.json"
az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$DEPLOYMENT_NAME" \
  --query properties.outputs \
  --output json > "$DEPLOYMENT_OUTPUT_FILE"

GITHUB_CLIENT_ID=$(jq -r '.githubIdentityClientId.value' < "$DEPLOYMENT_OUTPUT_FILE")
IDENTITY_PRINCIPAL_ID=$(jq -r '.githubIdentityPrincipalId.value' < "$DEPLOYMENT_OUTPUT_FILE")
WEB_APP_URL=$(jq -r '.webAppUrl.value' < "$DEPLOYMENT_OUTPUT_FILE")
FUNCTION_APP_NAME=$(jq -r '.functionAppName.value' < "$DEPLOYMENT_OUTPUT_FILE")
FUNCTION_APP_URL=$(jq -r '.functionAppUrl.value' < "$DEPLOYMENT_OUTPUT_FILE")
STORAGE_ACCOUNT_NAME=$(jq -r '.storageAccountName.value' < "$DEPLOYMENT_OUTPUT_FILE")
APPLICATION_INSIGHTS_NAME=$(jq -r '.applicationInsightsName.value' < "$DEPLOYMENT_OUTPUT_FILE")

echo "GitHub Identity Client ID: $GITHUB_CLIENT_ID"
echo "Identity Principal ID: $IDENTITY_PRINCIPAL_ID"
echo "Function App Name: $FUNCTION_APP_NAME"
echo "Storage Account Name: $STORAGE_ACCOUNT_NAME"
echo "Application Insights Name: $APPLICATION_INSIGHTS_NAME"
echo ""

echo "2-2. Managed Identity にContributorロールを割り当て中..."
az role assignment create \
  --assignee "$IDENTITY_PRINCIPAL_ID" \
  --role Contributor \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP"

if [ $? -eq 0 ]; then
    echo "✅ Contributorロール割り当て成功"
else
    echo "⚠️  Contributorロール割り当て失敗（既存の可能性）"
fi

echo ""

# 現在のユーザーのオブジェクトIDを取得
CURRENT_USER_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

echo "2-3. デプロイユーザーにKey Vaultのアクセス権限を付与中..."
echo "ユーザーオブジェクトID: $CURRENT_USER_OBJECT_ID"
az keyvault set-policy \
  --name "$KEY_VAULT_NAME" \
  --object-id "$CURRENT_USER_OBJECT_ID" \
  --secret-permissions get list set delete \
  --output none

if [ $? -eq 0 ]; then
    echo "✅ デプロイユーザーのKey Vaultアクセス権限を付与完了"
else
    echo "⚠️  Key Vaultアクセス権限の付与に失敗しました（既に権限がある可能性があります）"
fi

echo ""
echo "2-4. Key Vaultにシークレットを設定中..."

# GitHub Token
az keyvault secret set \
  --vault-name "$KEY_VAULT_NAME" \
  --name "github-token" \
  --value "$GITHUB_TOKEN" \
  --output none

if [ $? -eq 0 ]; then
    echo "✅ GitHub token をKey Vaultに設定完了"
else
    echo "❌ GitHub tokenの設定に失敗しました"
    exit 1
fi

# X OAuth Settings
echo "2-5. X OAuth設定をKey Vaultに設定中..."

az keyvault secret set \
  --vault-name "$KEY_VAULT_NAME" \
  --name "x-client-id" \
  --value "$X_CLIENT_ID" \
  --output none

if [ $? -eq 0 ]; then
    echo "✅ X Client ID をKey Vaultに設定完了"
else
    echo "❌ X Client IDの設定に失敗しました"
    exit 1
fi

az keyvault secret set \
  --vault-name "$KEY_VAULT_NAME" \
  --name "x-client-secret" \
  --value "$X_CLIENT_SECRET" \
  --output none

if [ $? -eq 0 ]; then
    echo "✅ X Client Secret をKey Vaultに設定完了"
else
    echo "❌ X Client Secretの設定に失敗しました"
    exit 1
fi

az keyvault secret set \
  --vault-name "$KEY_VAULT_NAME" \
  --name "x-redirect-uri" \
  --value "$X_REDIRECT_URI" \
  --output none

if [ $? -eq 0 ]; then
    echo "✅ X Redirect URI をKey Vaultに設定完了"
else
    echo "❌ X Redirect URIの設定に失敗しました"
    exit 1
fi

# Firebase/Firestore設定をKey Vaultに保存
if [ "$FIREBASE_ENABLED" = true ]; then
    echo "2-6. Firebase/Firestore設定をKey Vaultに設定中..."

    # Firebase Project ID
    az keyvault secret set \
      --vault-name "$KEY_VAULT_NAME" \
      --name "firebase-project-id" \
      --value "$FIREBASE_PROJECT_ID" \
      --output none

    if [ $? -eq 0 ]; then
        echo "✅ Firebase Project ID をKey Vaultに設定完了"
    else
        echo "❌ Firebase Project IDの設定に失敗しました"
        exit 1
    fi

    # Firebase Service Account (Base64)
    az keyvault secret set \
      --vault-name "$KEY_VAULT_NAME" \
      --name "firebase-service-account-base64" \
      --value "$FIREBASE_SERVICE_ACCOUNT_BASE64" \
      --output none

    if [ $? -eq 0 ]; then
        echo "✅ Firebase Service Account (Base64) をKey Vaultに設定完了"
    else
        echo "❌ Firebase Service Account (Base64)の設定に失敗しました"
        exit 1
    fi

    # Encryption Key
    az keyvault secret set \
      --vault-name "$KEY_VAULT_NAME" \
      --name "encryption-key" \
      --value "$ENCRYPTION_KEY" \
      --output none

    if [ $? -eq 0 ]; then
        echo "✅ Encryption Key をKey Vaultに設定完了"
    else
        echo "❌ Encryption Keyの設定に失敗しました"
        exit 1
    fi

    # Firestore Region (デフォルト値を使用)
    FIRESTORE_REGION_VALUE="${FIRESTORE_REGION:-asia-northeast1}"
    az keyvault secret set \
      --vault-name "$KEY_VAULT_NAME" \
      --name "firestore-region" \
      --value "$FIRESTORE_REGION_VALUE" \
      --output none

    if [ $? -eq 0 ]; then
        echo "✅ Firestore Region をKey Vaultに設定完了"
    else
        echo "❌ Firestore Regionの設定に失敗しました"
        exit 1
    fi

    echo "🔥 Firebase/Firestore設定完了"
else
    echo "2-6. Firebase/Firestore設定をスキップ（設定が不完全なため）"
fi

echo ""

echo "2-7. Web AppとFunction Appを再起動してシークレットを反映中..."
az webapp restart \
  --name "${APP_NAME}-webapp" \
  --resource-group "$RESOURCE_GROUP" \
  --output none

echo "✅ Web App再起動完了"

az functionapp restart \
  --name "${APP_NAME}-functions" \
  --resource-group "$RESOURCE_GROUP" \
  --output none

echo "✅ Function App再起動完了"
echo ""

# =============================================================================
# Stage 3: GitHub Secrets設定
# =============================================================================
echo "🐙 Stage 3: GitHub Secrets設定..."

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
    echo "RESOURCE_GROUP: $RESOURCE_GROUP"
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
        echo "RESOURCE_GROUP: $RESOURCE_GROUP"
        echo "KEY_VAULT_NAME: $KEY_VAULT_NAME"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    else
        echo "3-1. GitHub CLIで production environment にシークレット・変数を設定中..."
        
        # GitHub CLI でシークレットを設定
        echo "$GITHUB_CLIENT_ID" | gh secret set AZURE_CLIENT_ID --repo "$REPO_OWNER/$REPO_NAME" --env production
        echo "$AZURE_TENANT_ID" | gh secret set AZURE_TENANT_ID --repo "$REPO_OWNER/$REPO_NAME" --env production  
        echo "$AZURE_SUBSCRIPTION_ID" | gh secret set AZURE_SUBSCRIPTION_ID --repo "$REPO_OWNER/$REPO_NAME" --env production
        
        # 環境変数も設定
        gh variable set APP_NAME --repo "$REPO_OWNER/$REPO_NAME" --env production --body "$APP_NAME"
        gh variable set RESOURCE_GROUP --repo "$REPO_OWNER/$REPO_NAME" --env production --body "$RESOURCE_GROUP"
        gh variable set KEY_VAULT_NAME --repo "$REPO_OWNER/$REPO_NAME" --env production --body "$KEY_VAULT_NAME"
        
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
            echo "RESOURCE_GROUP: $RESOURCE_GROUP"
            echo "KEY_VAULT_NAME: $KEY_VAULT_NAME"
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
echo "  ⚡ Function App URL: $FUNCTION_APP_URL"
echo "  💾 Storage Account: $STORAGE_ACCOUNT_NAME"
echo "  📊 Application Insights: $APPLICATION_INSIGHTS_NAME"
echo "  🆔 Client ID: $GITHUB_CLIENT_ID"
echo "  🏷️  Principal ID: $IDENTITY_PRINCIPAL_ID"
echo "  🔑 Key Vault: $KEY_VAULT_NAME"

if [ "$FIREBASE_ENABLED" = true ]; then
    echo "  🔥 Firebase: 有効 (Project: $FIREBASE_PROJECT_ID)"
else
    echo "  🔥 Firebase: 無効 (設定不完全)"
fi

echo ""
echo "🔐 権限設定状況:"
echo "  ✅ GitHub Identity → Resource Group (Contributor) [deploy.sh CLI管理]"
echo "  ✅ Web App → Key Vault (Secret Reader) [Bicep管理]"
echo "  ✅ Function App → Key Vault (Secret Reader) [Bicep管理]"
echo "  ✅ GitHub Identity → Key Vault (Secret Manager) [Bicep管理]"
echo "  ✅ デプロイユーザー → Key Vault (Temp Access) [deploy.sh管理]"
echo "  ✅ サイドカー → GHCR (Private対応) [Key Vault PAT経由]"

if [ "$FIREBASE_ENABLED" = true ]; then
    echo "  🔥 Firebase/Firestore: 設定済み [Key Vault管理]"
fi

echo ""
echo "🚀 機能状況:"
echo "  ✅ X API OAuth認証"
echo "  ✅ Markdown投稿作成"

if [ "$FIREBASE_ENABLED" = true ]; then
    echo "  ✅ 投稿履歴管理 (Firestore)"
    echo "  ✅ 予約投稿機能"
    echo "  ✅ 自動投稿機能 (Azure Functions Timer Trigger)"
    echo "  ✅ アクセストークン暗号化保存"
else
    echo "  ❌ 投稿履歴管理 (Firebase設定なし)"
    echo "  ❌ 予約投稿機能 (Firebase設定なし)"
    echo "  ❌ 自動投稿機能 (Firebase設定なし)"
fi

echo ""
echo "📋 次のステップ:"
echo "  1. Web App: GitHub Actionsワークフロー 'Deploy to Azure' を手動実行"
echo "  2. Functions: GitHub Actionsワークフロー 'Deploy Azure Functions' を手動実行"
echo "  3. Timer Trigger動作確認: Azure Portal > Functions App > Timer関数"
echo "  4. Application Insights でログ監視開始"
echo "  5. 初回投稿テスト（Web App経由でFirestoreに予約投稿）"

if [ "$FIREBASE_ENABLED" = false ]; then
    echo ""
    echo "🔥 Firebase機能を有効にするには:"
    echo "  1. .envファイルにFirebase設定を追加"
    echo "  2. deploy.shを再実行"
fi

echo ""
echo "📖 詳細な設定手順: README.md を参照"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"