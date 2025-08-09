#!/bin/bash

# 強制削除用スクリプト（確認なし）

# .envファイルの読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "エラー: .envファイルが見つかりません。"
    echo ".env.exampleをコピーして.envを作成し、値を設定してください。"
    echo "cp .env.example .env"
    exit 1
fi

# 必須変数のチェック
if [ -z "$RESOURCE_GROUP" ]; then
    echo "エラー: RESOURCE_GROUPが設定されていません。"
    echo ".envファイルを確認してください。"
    exit 1
fi

echo "リソースグループ '$RESOURCE_GROUP' を強制削除します..."

# リソースグループの削除（確認なし）
az group delete --name $RESOURCE_GROUP --yes --no-wait

echo "削除コマンドを実行しました。"
echo ""
echo "削除の完了を待つ場合は以下のコマンドを実行してください："
echo "az group delete --name $RESOURCE_GROUP --yes"