#!/bin/bash

# 権限確認特化スクリプト

# 出力ファイル名（タイムスタンプ付き）
OUTPUT_FILE="azure_status_check_permission_$(date +%Y%m%d_%H%M%S).md"
TEMP_FILE="/tmp/permission_check_$$.tmp"

# 関数：コンソールとMarkdownファイルの両方に出力
log_both() {
    echo "$1" | tee -a "$TEMP_FILE"
}

# 関数：コマンドの実行結果をMarkdown形式で保存
execute_and_log() {
    local title="$1"
    local command="$2"
    local format="${3:-table}"
    
    log_both ""
    log_both "#### $title"
    log_both ""
    log_both '```bash'
    log_both "$ $command"
    log_both '```'
    log_both ""
    
    if [ "$format" == "json" ]; then
        log_both '```json'
    else
        log_both '```'
    fi
    
    # コマンド実行して結果を取得
    eval "$command" 2>&1 | tee -a "$TEMP_FILE"
    local exit_code=$?
    
    log_both '```'
    
    if [ $exit_code -eq 0 ]; then
        log_both ""
        log_both "✅ **実行成功**"
    else
        log_both ""
        log_both "❌ **実行失敗** (Exit Code: $exit_code)"
    fi
    
    log_both ""
    log_both "---"
}

# Markdownファイル初期化
cat > "$TEMP_FILE" << EOF
# Azure権限確認レポート

**生成日時**: $(date '+%Y年%m月%d日 %H:%M:%S')  
**実行ユーザー**: $(whoami)  
**ホスト**: $(hostname)  

---

## 🎯 権限確認の目的

このスクリプトは以下を確認します：
- 現在のユーザーの Azure 権限
- テナントのデフォルト設定
- ロール割り当て権限の有無
- アプリ登録・管理権限の有無

---

EOF

log_both "🔍 Azure権限を詳細確認します..."
log_both ""
log_both "📄 実行結果は **$OUTPUT_FILE** に保存されます"
log_both ""

# =============================================================================
# 1. 基本ユーザー情報
# =============================================================================
log_both "## 1. 基本ユーザー情報"

execute_and_log "現在ログイン中のユーザー詳細" \
    "az ad signed-in-user show --query '{userPrincipalName:userPrincipalName, displayName:displayName, id:id, userType:userType}'" \
    "json"

execute_and_log "現在のテナント・サブスクリプション" \
    "az account show --query '{tenantId:tenantId, subscriptionId:id, subscriptionName:name, isDefault:isDefault}'" \
    "json"

# =============================================================================
# 2. Azure RBAC権限確認
# =============================================================================
log_both "## 2. Azure RBAC権限確認"

USER_ID=$(az ad signed-in-user show --query id -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

execute_and_log "サブスクリプション全体での権限" \
    "az role assignment list --assignee \"$USER_ID\" --scope \"/subscriptions/$SUBSCRIPTION_ID\" --query '[].{role:roleDefinitionName, scope:scope, principalType:principalType}' --output table"

execute_and_log "全スコープでの権限一覧" \
    "az role assignment list --assignee \"$USER_ID\" --all --query '[].{role:roleDefinitionName, scope:scope}' --output table"

# 重要な権限の個別チェック
log_both ""
log_both "### 🔑 重要権限の個別チェック"
log_both ""

OWNER_ROLE=$(az role assignment list --assignee "$USER_ID" --all --query "[?roleDefinitionName=='Owner'].roleDefinitionName" -o tsv 2>/dev/null)
UAA_ROLE=$(az role assignment list --assignee "$USER_ID" --all --query "[?roleDefinitionName=='User Access Administrator'].roleDefinitionName" -o tsv 2>/dev/null)
CONTRIBUTOR_ROLE=$(az role assignment list --assignee "$USER_ID" --all --query "[?roleDefinitionName=='Contributor'].roleDefinitionName" -o tsv 2>/dev/null)

if [ -n "$OWNER_ROLE" ]; then
    log_both "✅ **Owner権限**: あり - 完全な管理権限"
elif [ -n "$UAA_ROLE" ]; then
    log_both "✅ **User Access Administrator権限**: あり - ロール割り当て可能"
else
    log_both "❌ **ロール割り当て権限**: なし - Owner または User Access Administrator が必要"
fi

if [ -n "$CONTRIBUTOR_ROLE" ]; then
    log_both "✅ **Contributor権限**: あり - リソース作成・管理可能"
else
    log_both "⚠️  **Contributor権限**: なし - リソース作成に制限あり"
fi

# =============================================================================
# 3. Microsoft Entra ID (Azure AD) 権限確認
# =============================================================================
log_both ""
log_both "## 3. Microsoft Entra ID 権限確認"

execute_and_log "Entra ID でのディレクトリロール" \
    "az rest --method GET --url \"https://graph.microsoft.com/v1.0/me/memberOf\" --query 'value[?\@.\"@odata.type\"==\`#microsoft.graph.directoryRole\`].{displayName:displayName, description:description}' --output table"

execute_and_log "テナントのデフォルトユーザー権限設定" \
    "az rest --method GET --url \"https://graph.microsoft.com/v1.0/policies/authorizationPolicy\" --query 'defaultUserRolePermissions.{allowedToCreateApps:allowedToCreateApps, allowedToCreateSecurityGroups:allowedToCreateSecurityGroups, allowedToReadOtherUsers:allowedToReadOtherUsers}'" \
    "json"

# アプリ登録権限の詳細チェック
log_both ""
log_both "### 📱 アプリ登録関連権限"
log_both ""

execute_and_log "自分が作成したアプリ登録数" \
    "az ad app list --show-mine --query 'length(@)'"

execute_and_log "アプリ登録作成テスト（ドライラン）" \
    "az ad app create --display-name \"permission-test-app-$(date +%s)\" --dry-run 2>&1 || echo 'アプリ登録権限なし'"

# =============================================================================
# 4. サービスプリンシパル関連権限
# =============================================================================
log_both ""
log_both "## 4. サービスプリンシパル関連権限"

execute_and_log "自分が作成したサービスプリンシパル数" \
    "az ad sp list --show-mine --query 'length(@)'"

# サービスプリンシパル作成テスト（実際には作らない）
log_both ""
log_both "#### サービスプリンシパル作成可能性テスト"
log_both ""
log_both '```bash'
log_both "$ # テスト用サービスプリンシパル作成（即削除）"
log_both '```'
log_both ""
log_both '```'

TEST_SP_NAME="permission-test-sp-$(date +%s)"
SP_CREATE_OUTPUT=$(az ad sp create-for-rbac --name "$TEST_SP_NAME" --skip-assignment 2>&1)
SP_CREATE_SUCCESS=$?

if [ $SP_CREATE_SUCCESS -eq 0 ]; then
    log_both "サービスプリンシパル作成: 成功"
    # すぐに削除
    SP_ID=$(echo "$SP_CREATE_OUTPUT" | jq -r '.appId' 2>/dev/null)
    if [ -n "$SP_ID" ] && [ "$SP_ID" != "null" ]; then
        az ad app delete --id "$SP_ID" 2>/dev/null
        log_both "テスト用サービスプリンシパルを削除しました"
    fi
else
    log_both "サービスプリンシパル作成: 失敗"
    log_both "$SP_CREATE_OUTPUT"
fi

log_both '```'
log_both ""

if [ $SP_CREATE_SUCCESS -eq 0 ]; then
    log_both "✅ **サービスプリンシパル作成**: 可能"
else
    log_both "❌ **サービスプリンシパル作成**: 不可能"
fi

log_both ""
log_both "---"

# =============================================================================
# 5. 特定操作の権限確認
# =============================================================================
log_both ""
log_blob "## 5. 特定操作の権限確認"

# リソースグループ作成権限
log_both ""
log_both "### リソース管理権限"
log_both ""

TEST_RG_NAME="permission-test-rg-$(date +%s)"
execute_and_log "テスト用リソースグループ作成・削除" \
    "az group create --name \"$TEST_RG_NAME\" --location japaneast --output none && az group delete --name \"$TEST_RG_NAME\" --yes --no-wait && echo 'リソースグループ作成・削除権限: あり'" \
    "text"

# Key Vault操作権限
execute_and_log "Key Vault一覧取得" \
    "az keyvault list --query '[].{name:name, location:location}' --output table"

# =============================================================================
# 6. 診断結果とサマリー
# =============================================================================
log_both ""
log_both "## 6. 🩺 診断結果とサマリー"

log_both ""
log_both "### 権限サマリー"
log_both ""

# 権限レベルの判定
if [ -n "$OWNER_ROLE" ]; then
    PERMISSION_LEVEL="完全管理者"
    PERMISSION_SCORE=5
elif [ -n "$UAA_ROLE" ] && [ -n "$CONTRIBUTOR_ROLE" ]; then
    PERMISSION_LEVEL="高権限ユーザー"
    PERMISSION_SCORE=4
elif [ -n "$UAA_ROLE" ]; then
    PERMISSION_LEVEL="権限管理者"
    PERMISSION_SCORE=3
elif [ -n "$CONTRIBUTOR_ROLE" ]; then
    PERMISSION_LEVEL="リソース管理者"
    PERMISSION_SCORE=2
else
    PERMISSION_LEVEL="制限付きユーザー"
    PERMISSION_SCORE=1
fi

log_both "**権限レベル**: $PERMISSION_LEVEL (スコア: $PERMISSION_SCORE/5)"
log_both ""

# OIDC vs サービスプリンシパル の推奨
log_both "### 🚀 デプロイ方式の推奨"
log_both ""

if [ $PERMISSION_SCORE -ge 3 ]; then
    log_both "✅ **推奨**: OIDC方式"
    log_both ""
    log_both "理由:"
    log_both "- ロール割り当て権限あり"
    log_both "- より安全で現代的"
    log_both "- 長期運用に適している"
    log_both ""
    log_both "次のステップ:"
    log_both "1. Managed Identity + Federated Credential作成"
    log_both "2. 自動でロール割り当て"
    log_both "3. GitHub Actions設定"
elif [ $SP_CREATE_SUCCESS -eq 0 ]; then
    log_both "⚠️  **推奨**: サービスプリンシパル方式"
    log_both ""
    log_both "理由:"
    log_both "- ロール割り当て権限不足"
    log_both "- サービスプリンシパル作成は可能"
    log_both "- より簡単に開始できる"
    log_both ""
    log_both "次のステップ:"
    log_both "1. サービスプリンシパル作成"
    log_both "2. GitHub Secretsに認証情報設定"
    log_both "3. GitHub Actions設定"
else
    log_both "❌ **要対応**: 管理者に権限付与依頼"
    log_both ""
    log_both "現状:"
    log_both "- ロール割り当て権限なし"
    log_both "- サービスプリンシパル作成不可"
    log_both ""
    log_both "必要なアクション:"
    log_both "1. 管理者に User Access Administrator 権限付与を依頼"
    log_both "2. または Application Administrator 権限付与を依頼"
    log_both "3. 権限付与後に OIDC方式でセットアップ"
fi

log_both ""
log_both "### 🎯 管理者への依頼内容（必要な場合）"
log_both ""

if [ $PERMISSION_SCORE -lt 3 ]; then
    log_both '```'
    log_both "件名: Azure権限付与のお願い"
    log_both ""
    log_both "ユーザー: $(az ad signed-in-user show --query userPrincipalName -o tsv)"
    log_both "要求権限: User Access Administrator (ロール割り当て用)"
    log_both "対象スコープ: /subscriptions/$SUBSCRIPTION_ID または特定のリソースグループ"
    log_both ""
    log_both "用途: GitHub ActionsからのAzureリソース自動デプロイ"
    log_both "期間: プロジェクト期間中"
    log_both '```'
fi

log_both ""
log_both "---"
log_both ""
log_both "## 📄 技術的詳細"
log_both ""
log_both "- **Azure CLI バージョン**: $(az --version | head -1 | cut -d' ' -f2)"
log_both "- **実行時間**: $(date '+%Y年%m月%d日 %H:%M:%S')"
log_both "- **テナントID**: $(az account show --query tenantId -o tsv)"
log_both "- **サブスクリプションID**: $SUBSCRIPTION_ID"
log_both ""
log_both "このレポートは権限確認スクリプトにより自動生成されました。"

# 最終ファイル出力
mv "$TEMP_FILE" "$OUTPUT_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 権限確認完了"
echo ""
echo "📄 詳細レポート: $OUTPUT_FILE"
echo ""
echo "📊 結果サマリー:"
echo "   権限レベル: $PERMISSION_LEVEL ($PERMISSION_SCORE/5)"

if [ $PERMISSION_SCORE -ge 3 ]; then
    echo "   ✅ OIDC方式で完全自動デプロイ可能"
elif [ $SP_CREATE_SUCCESS -eq 0 ]; then
    echo "   ⚠️  サービスプリンシパル方式を推奨"
else
    echo "   ❌ 管理者に権限付与依頼が必要"
fi

echo ""
echo "🔗 レポート閲覧:"
echo "   cat $OUTPUT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"