# Azure Functions 自動投稿システム

Streamlit アプリケーションで管理されている投稿データを参照して、定時に X (Twitter) へ自動投稿するAzure Functionsです。

## 機能概要

- **Timer Trigger**: 毎日 9:00、12:00、15:00、21:00（JST）に実行
- **Firestore連携**: Streamlit アプリと同じFirestoreデータベースを参照
- **自動投稿**: 指定時間に予約されている投稿を自動でX APIに送信
- **エラーハンドリング**: 各種エラーを適切にハンドリングし、Firestoreに記録

## プロジェクト構造

```
application/functions/
├── function_app.py           # メイン関数（Timer Trigger実装）
├── host.json                 # Functions設定ファイル
├── local.settings.json       # ローカル開発用設定
├── requirements.txt          # 依存関係
└── shared/                   # 共有モジュール
    ├── __init__.py
    ├── config.py             # 設定管理
    ├── firestore_client.py   # Firestore操作
    └── x_api_client.py       # X API通信
```

## 設定

### 環境変数

`local.settings.json`（ローカル開発）またはAzure Functions App Settings（本番）で以下を設定：

```json
{
  "FUNCTIONS_WORKER_RUNTIME": "python",
  "AzureWebJobsStorage": "UseDevelopmentStorage=true",
  "FIREBASE_PROJECT_ID": "your-firebase-project-id",
  "FIREBASE_SERVICE_ACCOUNT_BASE64": "your-base64-encoded-service-account-json",
  "ENCRYPTION_KEY": "your-fernet-encryption-key",
  "FIRESTORE_REGION": "asia-northeast1",
  "WEBSITE_TIME_ZONE": "Asia/Tokyo",
  "X_CLIENT_ID": "your-x-api-client-id",
  "X_CLIENT_SECRET": "your-x-api-client-secret"
}
```

**重要**: X API の Client ID と Client Secret はトークンのリフレッシュに必要です。これらの値はフロントエンドアプリケーションと同じものを使用してください。

### Timer スケジュール

CRON式: `0 0 9,12,15,21 * * *`
- 毎日 9:00、12:00、15:00、21:00 (JST) に実行
- 時間スロット: 0=9:00, 1=12:00, 2=15:00, 3=21:00

## データフロー

1. **Timer実行**: 指定時刻にFunction起動
2. **時間判定**: 現在時刻が投稿時間スロットかチェック
3. **データ取得**: Firestoreから該当する予約投稿を取得
4. **トークン取得**: ユーザーのアクセストークンとリフレッシュトークンを復号
5. **トークン検証**: アクセストークンの有効性を確認
6. **トークンリフレッシュ**: 無効な場合、リフレッシュトークンで新しいアクセストークンを取得
7. **投稿実行**: 有効なアクセストークンでX API v2 を使用してツイート
8. **結果更新**: 投稿状況とトークン（更新された場合）をFirestoreに記録

## ローカル開発

### 1. 前提条件

- Python 3.11+
- Azure Functions Core Tools v4
- Node.js (Azurite用)
- Azurite (Azure Storage エミュレータ)

### 2. Azurite のセットアップと起動

Azure Functions をローカルで実行するためには、Azure Storage エミュレータが必要です。

```bash
# Azurite をグローバルにインストール
npm install -g azurite

# Azurite を起動（別ターミナルで実行し続ける）
azurite --silent --location c:/azurite --debug c:/azurite/debug.log
```

**注意**: Azurite は Azure Functions の実行中は常に起動しておく必要があります。

### 3. 依存関係インストール

```bash
pip install -r requirements.txt
```

### 4. 設定ファイル編集

`local.settings.json` を実際の値で更新

### 5. ローカル実行

```bash
# Azurite が起動していることを確認してから実行
func start
```

### 4. テスト用HTTP Trigger（推奨）

ローカル開発時のみ有効になるテスト用HTTP Trigger関数を使用してテスト：

```bash
# 基本テスト（現在時刻で判定）
curl "http://localhost:7071/api/test_auto_poster"

# 特定の時間スロットをテスト
curl "http://localhost:7071/api/test_auto_poster?slot=0"  # 9時の投稿をテスト
curl "http://localhost:7071/api/test_auto_poster?slot=1"  # 12時の投稿をテスト

# 特定の日付をテスト
curl "http://localhost:7071/api/test_auto_poster?date=2024/01/15&slot=2"
```

**パラメータ:**
- `slot`: 時間スロット (0=9時, 1=12時, 2=15時, 3=21時)
- `date`: 対象日付（YYYY/MM/DD形式、省略時は今日）

**注意:** この HTTP Trigger 関数は環境変数 `ENABLE_TEST_FUNCTIONS=true` が設定されている場合のみ有効です。本番環境では無効化されます。

## 本番デプロイ

### 1. Azure Functions App 作成

```bash
# Bicepテンプレートでインフラ構築
cd ../../infrastructure
./deploy.sh
```

**注意**: 本番環境では Azurite は不要です。Azure Storage Account が自動的に作成され、使用されます。

### 2. 設定値の追加

Azure Key Vault から参照される設定値を確認

**重要:** 本番環境では `ENABLE_TEST_FUNCTIONS` 環境変数を設定しないか、`false` に設定してください。これによりテスト用HTTP Trigger関数が無効化されます。

### 3. デプロイ

```bash
func azure functionapp publish ${APP_NAME}-functions
```

### 4. セキュリティ確認

デプロイ後、Azure Portal で以下を確認：
- `ENABLE_TEST_FUNCTIONS` が未設定または `false` であること
- テスト用エンドポイント `/api/test_auto_poster` にアクセスできないこと

## トラブルシューティング

### Azurite 関連のエラー

#### "Failed to connect to Azure Storage"

- Azurite が起動していることを確認してください
- `azurite` コマンドが別ターミナルで実行中か確認
- ポート 10000, 10001, 10002 が他のプロセスで使用されていないか確認

#### "UseDevelopmentStorage=true" エラー

- `local.settings.json` の `AzureWebJobsStorage` が `"UseDevelopmentStorage=true"` に設定されているか確認
- Azurite が正しく起動しているか確認

#### Azurite のデータをクリアする場合

```bash
# Azurite を停止してからデータディレクトリを削除
rm -rf c:/azurite/*
# Azurite を再起動
azurite --silent --location c:/azurite --debug c:/azurite/debug.log
```

### 認証エラー

- Firebase サービスアカウント JSON が正しく設定されているか確認
- 暗号化キーが正しく設定されているか確認
- X API の Client ID と Client Secret が正しく設定されているか確認
- Firestore に保存されたアクセストークンの有効性を確認
- リフレッシュトークンが保存されているか確認（フロントエンドで `offline.access` スコープが必要）
- トークンリフレッシュに失敗する場合、フロントエンドアプリで再認証が必要

### タイムゾーンの問題

- `WEBSITE_TIME_ZONE=Asia/Tokyo` が設定されているか確認
- ログでJSTの時刻表示を確認

### Firestore接続エラー

- プロジェクトIDが正しく設定されているか確認
- サービスアカウントに適切な権限があるか確認

## ログ監視

Azure Portal の Application Insights でログを確認：

- 投稿成功/失敗の記録
- エラーメッセージ
- パフォーマンス情報

## セキュリティ

- アクセストークンは暗号化されてFirestoreに保存
- 環境変数は Azure Key Vault で管理
- X API レート制限を適切に処理