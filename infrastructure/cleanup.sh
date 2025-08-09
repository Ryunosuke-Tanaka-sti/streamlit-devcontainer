#!/bin/bash

# 色付きの出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# .envファイルの読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}エラー: .envファイルが見つかりません。${NC}"
    echo ".env.exampleをコピーして.envを作成し、値を設定してください。"
    echo "cp .env.example .env"
    exit 1
fi

# 必須変数のチェック
if [ -z "$RESOURCE_GROUP" ]; then
    echo -e "${RED}エラー: RESOURCE_GROUPが設定されていません。${NC}"
    echo ".envファイルを確認してください。"
    exit 1
fi

echo -e "${YELLOW}Azure リソースグループのクリーンアップスクリプト${NC}"
echo "================================================="
echo ""

# リソースグループの存在確認
echo "リソースグループを確認中..."
if az group show --name $RESOURCE_GROUP &>/dev/null; then
    echo -e "${GREEN}リソースグループ '$RESOURCE_GROUP' が見つかりました。${NC}"
else
    echo -e "${RED}リソースグループ '$RESOURCE_GROUP' が見つかりません。${NC}"
    exit 1
fi

# リソースグループ内のリソース一覧を表示
echo ""
echo "以下のリソースが削除されます："
echo "--------------------------------"
az resource list --resource-group $RESOURCE_GROUP --output table

# 確認プロンプト
echo ""
echo -e "${RED}警告: この操作はリソースグループ '$RESOURCE_GROUP' とその中のすべてのリソースを完全に削除します！${NC}"
echo -e "${RED}この操作は取り消すことができません。${NC}"
echo ""
read -p "本当に削除しますか？ (yes/no): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo -e "${YELLOW}操作がキャンセルされました。${NC}"
    exit 0
fi

# 最終確認
echo ""
read -p "最終確認: リソースグループ名を入力してください: " input_rg

if [ "$input_rg" != "$RESOURCE_GROUP" ]; then
    echo -e "${RED}リソースグループ名が一致しません。操作を中止します。${NC}"
    exit 1
fi

# リソースグループの削除
echo ""
echo "リソースグループを削除中..."
echo "（この処理には数分かかる場合があります）"

if az group delete --name $RESOURCE_GROUP --yes --no-wait; then
    echo -e "${GREEN}リソースグループの削除が開始されました。${NC}"
    echo ""
    echo "削除の進行状況を確認するには、以下のコマンドを実行してください："
    echo "az group show --name $RESOURCE_GROUP"
    echo ""
    echo "削除が完了すると、上記のコマンドはエラーを返すようになります。"
else
    echo -e "${RED}リソースグループの削除に失敗しました。${NC}"
    exit 1
fi