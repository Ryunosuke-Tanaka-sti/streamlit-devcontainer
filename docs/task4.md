# Task 4: Azure Functions 自動投稿システム実装

## 概要

Azure Functionsを使用して、Firestoreに保存された投稿計画とアクセストークンを参照し、スケジュールに基づいてX APIへ自動投稿するサーバーレス関数を実装します。

## 背景と目的

### 現状の課題
- Streamlitアプリケーションは常時起動が必要
- 予約投稿の実行にユーザーセッションが必要
- サーバーリソースの非効率な利用

### 解決策
- Azure Functionsによるサーバーレス実行
- Timer Triggerによる定期実行
- Firestoreベースの投稿管理

## システム構成

### アーキテクチャ

```
[Azure Functions (Timer Trigger)]
    ↓ (定期実行: 毎時0分、30分)
[Firestore Query]
    ↓ (該当時間の投稿を取得)
[Access Token取得]
    ↓ (暗号化トークンの復号)
[X API v2 投稿]
    ↓
[Firestore Update]
    ↓ (ステータス更新)
[ログ記録]
```

### 技術スタック

- **ランタイム**: Python 3.11
- **トリガー**: Timer Trigger (CRON式)
- **データベース**: Google Firestore
- **API通信**: X API v2
- **暗号化**: cryptography (Fernet)
- **インフラ**: Azure Functions Premium Plan

## 機能要件

### 1. Timer Trigger設定

```python
# Timer設定 (function.json) - 投稿時刻のみで実行
{
  "schedule": "0 0 9,12,15,21 * * *",  # 9:00, 12:00, 15:00, 21:00に実行
  "name": "myTimer",
  "type": "timerTrigger",
  "direction": "in"
}
```

### 2. 投稿処理フロー

1. **投稿検索**
   - 現在時刻の投稿を検索
   - time_slotベースの検索

2. **トークン取得**
   - Firestoreからユーザートークンを取得
   - 暗号化トークンの復号

3. **投稿実行**
   - X API v2への投稿
   - レート制限の確認

4. **結果更新**
   - 投稿ステータス更新
   - エラー情報の記録

### 3. Time Slot管理

```python
# config.pyで定義済みのTIME_SLOTSを使用
TIME_SLOTS = [
    {"slot": 0, "time": "09:00", "label": "朝9時"},
    {"slot": 1, "time": "12:00", "label": "昼12時"},
    {"slot": 2, "time": "15:00", "label": "午後3時"},
    {"slot": 3, "time": "21:00", "label": "夜9時"},
]

# 投稿判定ロジック
def get_current_time_slot(now_time: datetime) -> Optional[int]:
    """現在時刻が投稿対象スロットかどうかを判定"""
    current_time_str = now_time.strftime("%H:%M")
    for slot_info in TIME_SLOTS:
        if slot_info["time"] == current_time_str:
            return slot_info["slot"]
    return None  # 投稿時刻ではない
```

### 4. エラーハンドリング

- **トークン無効**: エラーログ記録、管理者通知
- **レート制限**: 次回実行へ延期
- **API障害**: リトライ機構（最大3回）
- **データ不整合**: トランザクション処理

## 実装詳細

### ディレクトリ構造

```
application/
├── functions/
│   ├── auto_poster/
│   │   ├── __init__.py
│   │   ├── function.json      # Timer Trigger設定
│   │   └── main.py           # メイン処理
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── firestore_client.py  # Firestore接続
│   │   ├── x_api_client.py      # X API通信
│   │   └── config.py            # 設定管理
│   ├── host.json               # Functions全体設定
│   ├── local.settings.json     # ローカル開発設定
│   └── requirements.txt        # 依存パッケージ
```

### 主要コンポーネント

#### 1. メイン関数 (main.py)

```python
import logging
import azure.functions as func
from datetime import datetime
from shared.firestore_client import FirestoreClient
from shared.x_api_client import XAPIClient
from shared.config import Config

def main(myTimer: func.TimerRequest) -> None:
    """自動投稿処理のメインエントリーポイント"""
    
    logging.info('Auto poster function triggered')
    
    # 現在時刻で投稿対象かどうかを判定
    now = datetime.now()
    current_slot = get_current_time_slot(now)
    
    # 投稿時刻ではない場合は何もしない
    if current_slot is None:
        logging.info(f'Current time {now.strftime("%H:%M")} is not a posting slot')
        return
    
    logging.info(f'Processing posts for slot {current_slot} at {now.strftime("%H:%M")}')
    
    # Firestore接続
    fs_client = FirestoreClient()
    
    # 該当する投稿を取得
    posts = fs_client.get_scheduled_posts(
        date_str=now.strftime("%Y/%m/%d"),
        time_slot=current_slot
    )
    
    for post in posts:
        try:
            # ユーザートークン取得
            token = fs_client.get_user_token(post['userId'])
            
            # X API投稿
            x_client = XAPIClient(token)
            result = x_client.post_tweet(post['content'])
            
            # ステータス更新（実装済みメソッドに合わせて修正）
            fs_client.update_post_status(
                post_id=post['id'],
                is_posted=True,
                x_post_id=result['data']['id']
            )
            
            logging.info(f"Successfully posted: {post['id']}")
            
        except Exception as e:
            logging.error(f"Failed to post {post['id']}: {str(e)}")
            fs_client.update_post_status(
                post_id=post['id'],
                is_posted=False,
                error_message=str(e)
            )
```

#### 2. Firestore Client

```python
class FirestoreClient:
    """Firestore操作クライアント"""
    
    def get_scheduled_posts(self, date_str: str, time_slot: int):
        """指定時間スロットの投稿を取得（実装済みメソッドに合わせて修正）"""
        docs = (
            self._db.collection("posts")
            .where(filter=FieldFilter("postDate", "==", date_str))
            .where(filter=FieldFilter("timeSlot", "==", time_slot))
            .where(filter=FieldFilter("isPosted", "==", False))
            .stream()
        )
        
        posts = []
        for doc in docs:
            post_data = doc.to_dict()
            post_data["id"] = doc.id
            posts.append(post_data)
        return posts
    
    def get_user_token(self, user_id: str) -> str:
        """ユーザーのアクセストークンを取得・復号"""
        user_ref = self.db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()
        encrypted_token = user_data['encryptedToken']
        return self.decrypt_token(encrypted_token)
```

## インフラストラクチャ

### Azure Bicep定義

```bicep
// Azure Functions App
resource functionApp 'Microsoft.Web/sites@2024-11-01' = {
  name: '${appName}-functions'
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionPlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: storageConnectionString
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FIREBASE_PROJECT_ID'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=firebase-project-id)'
        }
        {
          name: 'FIREBASE_SERVICE_ACCOUNT_BASE64'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=firebase-service-account)'
        }
        {
          name: 'ENCRYPTION_KEY'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=encryption-key)'
        }
        {
          name: 'WEBSITE_TIME_ZONE'
          value: 'Asia/Tokyo'
        }
      ]
    }
  }
}

// Function App Service Plan
resource functionPlan 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: '${appName}-function-plan'
  location: location
  sku: {
    name: 'Y1'  // Consumption Plan
    tier: 'Dynamic'
  }
  properties: {
    reserved: true  // Linux
  }
}

// Storage Account for Functions
resource storageAccount 'Microsoft.Storage/storageAccounts@2024-07-01' = {
  name: '${appName}funcstore'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}
```

## 開発環境セットアップ

### 1. Azure Functions Core Tools インストール

```bash
# Ubuntu/WSL
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4

# macOS
brew tap azure/functions
brew install azure-functions-core-tools@4

# Windows
winget install Microsoft.Azure.FunctionsCoreTools
```

### 2. ローカル開発設定

```json
// local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FIREBASE_PROJECT_ID": "your-project-id",
    "FIREBASE_SERVICE_ACCOUNT_BASE64": "base64-encoded-json",
    "ENCRYPTION_KEY": "your-encryption-key",
    "WEBSITE_TIME_ZONE": "Asia/Tokyo"
  }
}
```

### 3. 開発コマンド

```bash
# Functions プロジェクト初期化
cd application/functions
func init --python

# 新規関数作成
func new --name auto_poster --template "Timer trigger"

# ローカル実行
func start

# Azure へのデプロイ
func azure functionapp publish ${APP_NAME}-functions
```

## データモデル

### Firestore構造

```javascript
// posts コレクション (実装済みスキーマ)
{
  "postId": "auto_generated_id",
  "content": "投稿内容",
  "postDate": "2024/01/01",         // "YYYY/MM/DD"形式
  "timeSlot": 0,                   // 0-3のスロット番号 (nullは即時投稿)
  "isPosted": false,               // 投稿済みフラグ
  "xPostId": "x_platform_post_id", // Xの投稿ID
  "postedAt": "timestamp",         // 投稿日時
  "errorMessage": "エラーメッセージ", // エラー情報
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}

// users コレクション (新規 - トークン管理用)
{
  "userId": "user_id",
  "username": "x_username",
  "encryptedToken": "encrypted_access_token", // セッションからFirestoreへ移行予定
  "tokenExpiry": "timestamp",
  "dailyPostCount": 0,
  "monthlyPostCount": 0,
  "lastPostAt": "timestamp",
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}

// rate_limits コレクション (新規)
{
  "userId": "user_id",
  "date": "2024-01-01",
  "dailyCount": 0,
  "monthlyCount": 0,
  "lastResetDaily": "timestamp",
  "lastResetMonthly": "timestamp"
}
```

## セキュリティ考慮事項

### 1. トークン管理
- アクセストークンは暗号化して保存
- Key Vaultでの暗号化キー管理
- トークン有効期限の自動チェック

### 2. アクセス制御
- Managed Identityによる認証
- Firestoreセキュリティルール設定
- Functions アクセスキーの保護

### 3. エラー処理
- 個人情報を含まないログ記録
- エラー通知の実装
- 自動復旧メカニズム

## パフォーマンス最適化

### 1. Functions設定
- Premium Planでのコールドスタート削減
- Always On設定（必要に応じて）
- 並列実行の最適化

### 2. Firestore最適化
- インデックスの適切な設定
- バッチ処理の活用
- キャッシュ戦略

### 3. レート制限対応
- 事前チェック機能
- バックオフ戦略
- 優先度付きキュー

## モニタリング

### 1. Application Insights
- 実行ログの記録
- エラー追跡
- パフォーマンスメトリクス

### 2. アラート設定
- 連続失敗時の通知
- レート制限接近時の警告
- システムエラー通知

### 3. ダッシュボード
- 投稿成功率
- 日次/月次統計
- エラー傾向分析

## テスト戦略

### 1. ユニットテスト
```python
# test_auto_poster.py
import unittest
from unittest.mock import Mock, patch
from auto_poster import main

class TestAutoPoster(unittest.TestCase):
    
    @patch('auto_poster.main.FirestoreClient')
    @patch('auto_poster.main.XAPIClient')
    def test_successful_post(self, mock_x_api, mock_firestore):
        # テスト実装
        pass
    
    def test_time_slot_calculation(self):
        # time_slot計算のテスト
        pass
```

### 2. 統合テスト
- Firestore エミュレータ使用
- モックX API
- エンドツーエンドテスト

### 3. 負荷テスト
- 大量投稿のシミュレーション
- 同時実行テスト
- エラー復旧テスト

## デプロイメント

### 1. CI/CD パイプライン

```yaml
# .github/workflows/deploy-functions.yml
name: Deploy Azure Functions

on:
  push:
    branches: [main]
    paths:
      - 'application/functions/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd application/functions
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          cd application/functions
          python -m pytest
      
      - name: Deploy to Azure
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ vars.APP_NAME }}-functions
          package: application/functions
```

### 2. 環境別設定
- Development: ローカル開発
- Staging: テスト環境
- Production: 本番環境

## 運用・保守

### 1. 定期メンテナンス
- ログローテーション
- 古いデータのアーカイブ
- パフォーマンスチューニング

### 2. 障害対応
- オンコール体制
- 復旧手順書
- ロールバック計画

### 3. スケーリング
- 自動スケール設定
- 負荷分散
- 地域冗長性

## 成功指標

### 技術指標
- **投稿成功率**: 99%以上
- **実行遅延**: 1分以内
- **エラー率**: 1%以下

### ビジネス指標
- **コスト効率**: 月額1000円以下
- **可用性**: 99.9%
- **スケーラビリティ**: 1000ユーザー対応

## リスクと対策

| リスク | 影響度 | 対策 |
|-------|--------|------|
| Functions障害 | 高 | 冗長性確保、手動実行バックアップ |
| Firestore接続エラー | 高 | リトライ機構、ローカルキャッシュ |
| レート制限超過 | 中 | 事前チェック、優先度管理 |
| トークン失効 | 中 | 自動更新、ユーザー通知 |
| タイムゾーン問題 | 低 | UTC統一、明示的な変換 |

## まとめ

Azure Functionsを活用した自動投稿システムにより、サーバーレスで効率的な予約投稿機能を実現します。Firestoreとの連携により、スケーラブルで信頼性の高いシステムを構築し、X APIのレート制限を考慮した最適な投稿管理を行います。

## 次のステップ

1. Azure Functions環境のセットアップ
2. Bicepテンプレートの作成とデプロイ
3. Functions コードの実装
4. Firestore構造の更新
5. 統合テストの実施
6. 本番環境へのデプロイ