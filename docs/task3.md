# Task 3: X 投稿機能実装

## 概要

Task 1 の認証機能と Task 2 の UI 基盤を活用し、実際の X API v2 投稿機能を実装する。レート制限管理、エラーハンドリング、投稿履歴管理を含む。

**開発期間**: 1 週間

---

## 実装内容

### X API v2 投稿機能

- **POST /2/tweets**: 実際のツイート投稿
- **レート制限管理**: 17/24 時間、500/月の制限監視
- **エラーハンドリング**: API エラーの適切な処理
- **投稿履歴**: Firestore 連携による履歴管理

### Firestore 連携

- **投稿データ保存**: 投稿内容・結果の記録
- **統計情報管理**: 投稿数・成功率の追跡
- **レート制限状況**: 使用量の永続化

### スケジューリング機能

- **即時投稿**: 即座の投稿実行
- **予約投稿**: 指定日時での投稿（基本実装）
- **リトライ機能**: 失敗時の再試行

---

## 技術要件

### 必要なライブラリ

```python
import requests
import json
from datetime import datetime, timezone
from firebase_admin import firestore
import logging
import time
```

### 環境変数

```bash
# X API
X_CLIENT_ID=your_client_id
X_REDIRECT_URI=your_redirect_uri

# Firebase
GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccount.json
FIREBASE_PROJECT_ID=your_project_id
```

### X API v2 エンドポイント

- **投稿 URL**: `https://api.twitter.com/2/tweets`
- **認証**: Bearer Token または OAuth 2.0
- **Content-Type**: `application/json`

---

## 詳細機能仕様

### X API 投稿クライアント

#### 基本投稿機能

```python
class XAPIClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.twitter.com/2"

    def post_tweet(self, text: str) -> dict:
        """ツイート投稿"""
        # 実装詳細は省略
        pass

    def check_rate_limit(self) -> dict:
        """レート制限状況確認"""
        # 実装詳細は省略
        pass
```

#### レスポンス処理

- **成功時**: 投稿 ID、作成日時の取得
- **失敗時**: エラーコード、メッセージの解析
- **レート制限**: 429 エラーの特別処理

### レート制限管理

#### 制限カウンター

- **日次カウンター**: 24 時間スライディングウィンドウ
- **月次カウンター**: 月初リセット
- **リセット時刻**: 適切なタイミング管理

#### 制限チェック機能

```python
class RateLimitManager:
    def can_post(self) -> tuple[bool, str]:
        """投稿可能かチェック"""
        # 制限確認ロジック
        pass

    def increment_usage(self):
        """使用量インクリメント"""
        # カウンター更新
        pass

    def get_reset_time(self) -> datetime:
        """次回リセット時刻"""
        # リセット時刻計算
        pass
```

### Firestore 連携

#### データ保存

```python
# 投稿データの保存
post_data = {
    "title": "投稿タイトル",
    "content": "投稿内容",
    "markdownFilePath": "local/path/file.md",
    "scheduledTime": datetime.now(),
    "status": "posted",  # scheduled, posted, failed, cancelled
    "xPostId": "1234567890",
    "postedAt": datetime.now(),
    "createdAt": datetime.now(),
    "updatedAt": datetime.now()
}
```

#### 統計情報管理

- **投稿数カウント**: 日次・月次集計
- **成功率計算**: 成功/失敗の比率
- **エラー分析**: エラー種別の統計

### エラーハンドリング

#### X API エラー

- **400 Bad Request**: リクエスト形式エラー
- **401 Unauthorized**: 認証エラー
- **403 Forbidden**: 権限不足
- **429 Too Many Requests**: レート制限
- **500 Internal Server Error**: サーバーエラー

#### ネットワークエラー

- **接続タイムアウト**: 適切な待機時間
- **DNS エラー**: ネットワーク問題
- **SSL 証明書エラー**: セキュリティ問題

#### リトライ機能

```python
def post_with_retry(api_client, content, max_retries=3):
    """リトライ付き投稿"""
    for attempt in range(max_retries):
        try:
            result = api_client.post_tweet(content)
            return result
        except RateLimitError:
            # レート制限の場合は待機
            wait_time = calculate_wait_time()
            time.sleep(wait_time)
        except TemporaryError:
            # 一時的エラーの場合は短時間待機
            time.sleep(2 ** attempt)  # 指数バックオフ
        except PermanentError:
            # 永続的エラーの場合は即座に諦める
            break
    return None
```

---

## UI 統合

### Task 2 からの引き継ぎ

- **モック投稿ボタン** → **実際の投稿機能**
- **ダミーレート制限** → **実際の制限管理**
- **モック履歴** → **Firestore 連携履歴**

### 投稿ボタンの実装

```python
if st.button("📤 投稿実行", type="primary"):
    # 事前チェック
    can_post, message = rate_limiter.can_post()
    if not can_post:
        st.error(f"投稿できません: {message}")
        return

    # 投稿実行
    with st.spinner("投稿中..."):
        result = post_with_retry(api_client, content)

    if result:
        st.success("投稿が完了しました！")
        # Firestore保存
        save_post_data(result)
        # 制限カウンター更新
        rate_limiter.increment_usage()
    else:
        st.error("投稿に失敗しました")
```

### リアルタイム制限表示

```python
# レート制限状況の表示
daily_used, daily_limit = rate_limiter.get_daily_usage()
monthly_used, monthly_limit = rate_limiter.get_monthly_usage()

col1, col2 = st.columns(2)
with col1:
    st.metric("日次制限", f"{daily_used}/{daily_limit}",
              delta=f"{daily_limit - daily_used} 残り")

with col2:
    st.metric("月次制限", f"{monthly_used}/{monthly_limit}",
              delta=f"{monthly_limit - monthly_used} 残り")

# プログレスバー
daily_progress = daily_used / daily_limit if daily_limit > 0 else 0
st.progress(daily_progress, text=f"日次使用量: {daily_used}/{daily_limit}")
```

---

## 投稿履歴管理

### 履歴表示画面

```python
def show_post_history():
    st.subheader("📋 投稿履歴")

    # フィルター
    status_filter = st.selectbox("ステータス",
                                ["全て", "投稿済み", "失敗", "予約中"])

    # Firestoreから履歴取得
    posts = get_post_history(status_filter)

    for post in posts:
        with st.expander(f"{post['title']} - {post['status']}"):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**内容**: {post['content'][:100]}...")
                st.write(f"**投稿日時**: {post['postedAt']}")
                if post['xPostId']:
                    st.write(f"**X投稿ID**: {post['xPostId']}")

            with col2:
                if post['status'] == 'failed':
                    if st.button("🔄 再試行", key=f"retry_{post['id']}"):
                        retry_post(post)
```

### 統計情報表示

```python
def show_statistics():
    st.subheader("📊 投稿統計")

    # 今日の統計
    today_stats = get_today_statistics()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("今日の投稿", today_stats['count'],
                  delta=today_stats['change'])
    with col2:
        st.metric("成功率", f"{today_stats['success_rate']:.1%}")
    with col3:
        st.metric("エラー数", today_stats['errors'])

    # 週次グラフ
    weekly_data = get_weekly_statistics()
    st.line_chart(weekly_data)
```

---

## 設定管理

### 投稿設定

```python
# 設定ファイル (config.json)
{
    "posting": {
        "max_retries": 3,
        "retry_delay": 5,
        "timeout": 30
    },
    "rate_limit": {
        "daily_limit": 17,
        "monthly_limit": 500,
        "buffer_posts": 2  # 余裕を持った制限
    },
    "firestore": {
        "collection_name": "posts",
        "batch_size": 100
    }
}
```

### ログ設定

```python
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('x_scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 投稿ログ
def log_post_attempt(content, result):
    if result:
        logger.info(f"投稿成功: ID={result['id']}, Content={content[:50]}...")
    else:
        logger.error(f"投稿失敗: Content={content[:50]}...")
```

---

## テスト項目

### 投稿機能テスト

- [ ] 正常な投稿の成功
- [ ] 投稿 ID の正常取得
- [ ] レスポンスデータの正常解析
- [ ] 投稿内容の正確性

### レート制限テスト

- [ ] 制限カウンターの正常動作
- [ ] 制限到達時の適切な処理
- [ ] リセット時刻の正確性
- [ ] 制限状況の正常表示

### エラーハンドリングテスト

- [ ] 各種 API エラーの適切な処理
- [ ] ネットワークエラーの処理
- [ ] リトライ機能の動作
- [ ] エラーメッセージの表示

### Firestore 連携テスト

- [ ] 投稿データの正常保存
- [ ] 履歴表示の正常動作
- [ ] 統計情報の正確性
- [ ] データ同期の確認

### UI 統合テスト

- [ ] Task 2 UI との正常連携
- [ ] リアルタイム更新の動作
- [ ] 状態管理の正確性
- [ ] ユーザビリティの確認

---

## 成果物

### 実装ファイル

- `x_api_client.py`: X API v2 クライアント
- `rate_limit_manager.py`: レート制限管理
- `firestore_manager.py`: Firestore 連携
- `post_processor.py`: 投稿処理ロジック
- `error_handler.py`: エラーハンドリング

### 設定ファイル

- `config.json`: アプリケーション設定
- `logging.conf`: ログ設定
- `firestore_rules.json`: Firestore セキュリティルール

### ドキュメント

- API 連携仕様書
- エラーコード一覧
- トラブルシューティングガイド
- 運用マニュアル

---

## 運用考慮事項

### 監視・アラート

- **投稿失敗率**: 閾値超過時のアラート
- **API レスポンス時間**: パフォーマンス監視
- **レート制限到達**: 事前通知機能
- **Firestore使用量**: 無料枠監視
- **セッション状況**: アクティブユーザー監視

### バックアップ・復旧

- **投稿データ**: Firestore の自動バックアップ
- **Markdownファイル**: 定期的なローカルバックアップ
- **設定ファイル**: バージョン管理による履歴保存
- **ログファイル**: ローテーション・長期保存

### セキュリティ

- **アクセストークン**: Streamlit Secretsでの安全な管理
- **API キー**: 環境変数・Secretsでの管理
- **ログ出力**: 機密情報の完全除外
- **セッション管理**: タイムアウト・自動ログアウト

### エラー復旧機能

- **オフライン対応**: ネットワーク断絶時のキューイング
- **自動復旧**: 接続回復時の自動同期
- **データ整合性**: 復旧時の重複投稿防止

---

## プロジェクト完成

この Task 3 の完了により、以下の完全な機能を持つ X 予約投稿管理アプリケーションが完成します：

### 完成機能

- ✅ X OAuth 2.0 認証
- ✅ Markdown ファイル管理
- ✅ 2 ペイン投稿作成 UI
- ✅ 実際の X 投稿機能
- ✅ レート制限管理
- ✅ 投稿履歴・統計
- ✅ エラーハンドリング

### 技術スタック

- **フロントエンド**: Streamlit
- **認証**: X OAuth 2.0
- **データベース**: Google Firestore
- **ファイル管理**: ローカル Markdown
- **API**: X API v2

この実装により、X API 無料プランの制約下で実用的な投稿管理システムが実現されます。
