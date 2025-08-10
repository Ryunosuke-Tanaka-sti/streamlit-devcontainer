# X Scheduler Pro

X API v2を使用したMarkdown投稿管理システム。OAuth 2.0認証、即時投稿、予約投稿、レート制限管理、投稿履歴管理を統合したStreamlitアプリケーション。

## 機能概要

### 🔐 X OAuth 2.0 認証
- **セキュア認証**: OAuth 2.0 + PKCE による安全な認証
- **自動トークン管理**: アクセストークンの自動更新
- **セッション管理**: タイムアウト機能付きセッション

### 📝 Markdown投稿管理
- **ファイル参照**: サイドバーでのMarkdownファイル参照・選択
- **2ペインUI**: プレビュー画面と投稿フォームの同時表示
- **リアルタイム編集**: 投稿内容の動的編集と文字数チェック

### 📤 即時・予約投稿
- **即時投稿**: X API v2による実際のツイート投稿
- **予約投稿**: 指定日時での自動投稿（スケジューラー連携）
- **投稿検証**: 文字数制限・レート制限の事前チェック

### 📊 レート制限管理
- **制限追跡**: 17投稿/24時間、500投稿/月の制限管理
- **リアルタイム表示**: 使用量・残り回数・リセット時刻の表示
- **自動カウント**: 投稿成功時の使用量自動更新

### 📋 投稿履歴・統計
- **履歴管理**: Firestore連携による投稿履歴保存
- **ステータス管理**: 投稿済み・失敗・予約中・キャンセルの追跡
- **統計分析**: 成功率・日次/月次統計の表示
- **再投稿機能**: 失敗した投稿の再試行

## 必要な環境・ライブラリ

### 必須要件
- **Python**: 3.11+
- **X API**: Developer アカウント（Basic プラン以上）
- **Firebase**: Firestore データベース（オプション）

### 主要ライブラリ
- `streamlit==1.46.1`: Webアプリケーションフレームワーク
- `requests==2.32.4`: HTTP通信（X API）
- `google-cloud-firestore>=2.11.0`: Firestore連携
- `firebase-admin>=6.2.0`: Firebase管理
- `APScheduler>=3.10.0`: 予約投稿スケジューラー
- `cryptography>=41.0.0`: OAuth 2.0セキュリティ

## セットアップ

### 1. 事前準備

#### X API 設定
1. [X Developer Portal](https://developer.twitter.com/) でアプリケーションを作成
2. OAuth 2.0 設定を有効化
3. Callback URL に `http://localhost:8501` を設定
4. Client ID と Client Secret を取得

#### Firebase 設定（オプション）
1. [Firebase Console](https://console.firebase.google.com/) でプロジェクトを作成
2. Firestore データベースを有効化
3. サービスアカウントキーを生成・ダウンロード

### 2. 環境設定

1. `sample.env` を `.env` にコピーして編集:
```bash
cp sample.env .env
```

2. 環境変数を設定:
```env
# X API
X_CLIENT_ID=your_client_id_here
X_CLIENT_SECRET=your_client_secret_here
X_REDIRECT_URI=http://localhost:8501

# Firebase（オプション）
GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccount.json
FIREBASE_PROJECT_ID=your_project_id
```

### 3. インストール・実行

#### Dev Container使用（推奨）
```bash
# VS Code で開き、「Dev Container で再度開く」を選択
```

#### ローカル環境
```bash
# 依存関係インストール
pip install -r requirements.txt

# アプリケーション実行
streamlit run src/main.py
```

## 使用方法

### 1. 認証
1. アプリ起動後、「Xでログイン」をクリック
2. X認証画面で認証を完了
3. アプリに自動的に戻る

### 2. 投稿作成
1. サイドバーでMarkdownファイルを選択
2. プレビュー確認後、投稿テキストを編集
3. 即時投稿または予約投稿を選択して実行

### 3. 投稿管理
- **統計情報タブ**: 投稿数・成功率の確認
- **投稿履歴**: 過去の投稿一覧・再試行
- **レート制限**: 使用量・残り回数の確認

## プロジェクト構成

```
.
├── src/
│   ├── main.py                    # メインアプリケーション
│   ├── api/                       # API関連
│   │   ├── x_api_client.py        # X API v2 クライアント
│   │   ├── rate_limit_manager.py  # レート制限管理
│   │   ├── post_processor.py      # 投稿処理
│   │   └── scheduler.py           # 予約投稿スケジューラー
│   ├── auth/                      # 認証関連
│   │   ├── oauth_client.py        # OAuth 2.0 クライアント
│   │   └── pkce_utils.py          # PKCE ユーティリティ
│   ├── db/                        # データベース関連
│   │   └── firestore_manager.py   # Firestore 管理
│   ├── components/                # UI コンポーネント
│   │   └── simple_file_viewer.py  # ファイル参照・投稿UI
│   └── utils/                     # ユーティリティ
├── markdown/                      # Markdownファイル
├── requirements.txt               # Python依存関係
├── sample.env                     # 環境変数サンプル
└── README.md                      # このファイル
```

## 主な機能詳細

### レート制限管理
- **日次制限**: 24時間ローリングウィンドウで17投稿
- **月次制限**: 月初リセットで500投稿
- **自動追跡**: 投稿成功時の使用量自動更新

### 予約投稿
- **精密スケジューリング**: 分単位での予約投稿
- **自動実行**: バックグラウンドでの自動投稿
- **エラー処理**: 失敗時の自動リトライ機能

### データ永続化
- **ローカル**: レート制限データのJSON保存
- **Firestore**: 投稿履歴・統計の cloud 保存

## 運用考慮事項

### セキュリティ
- OAuth 2.0 + PKCE による安全な認証
- アクセストークンの暗号化保存
- セッションタイムアウト機能

### 制限事項
- X API Basic プランの制限に準拠
- Firestore 無料枠での運用想定

### トラブルシューティング
- 認証エラー: リダイレクトURI設定確認
- レート制限: 使用量と制限値の確認
- Firestore エラー: サービスアカウント権限確認

## ライセンス

このプロジェクトは教育・デモ目的で作成されています。

