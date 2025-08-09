# Task 1: Streamlit X OAuth 2.0 認証

## 概要

X API v2 の OAuth 2.0 認証を Streamlit アプリケーションに実装し、ユーザーが X アカウントでログインできる機能を構築する。

**開発期間**: 1-2 週間

---

## 実装内容

### OAuth 2.0 Authorization Code Flow with PKCE

- **認証フロー**: Authorization Code Flow with PKCE（セキュリティ強化）
- **スコープ**: `tweet.write`, `users.read`
- **コールバック処理**: Streamlit での認証コード受け取り
- **トークン管理**: アクセストークン・リフレッシュトークンの管理

### X Developer Portal 設定

- **アプリ登録**: X Developer Portal でのアプリケーション作成
- **認証設定**: OAuth 2.0 設定、コールバック URL 設定
- **スコープ設定**: 必要な権限の設定

### Streamlit 認証フロー

- **認証ボタン**: ログインボタンの実装
- **セッション管理**: `st.session_state`を使用した状態管理
- **リダイレクト処理**: X 認証画面への誘導
- **コールバック処理**: 認証コード受け取り・処理

### トークン管理

- **取得**: authorization code から access token への交換
- **保存**: セキュアなトークン保存（暗号化推奨）
- **更新**: refresh token を使用した自動更新
- **検証**: トークン有効期限のチェック

---

## 技術要件

### 必要なライブラリ

```python
import streamlit as st
import requests
import secrets
import hashlib
import base64
import json
from urllib.parse import urlencode
```

### 環境変数

```bash
X_CLIENT_ID=your_client_id
X_CLIENT_SECRET=your_client_secret  # 必要に応じて
X_REDIRECT_URI=http://localhost:8501/callback  # 開発時
X_REDIRECT_URI_PROD=https://your-app.com/callback  # 本番時
```

### 開発環境でのHTTPS対応

- **Windows側ngrok活用**: 既存のngrokインストールを使用してHTTPS化
- **設定例**:
  ```bash
  # Windows側で実行
  ngrok http 8501
  
  # 表示されるHTTPS URLを X Developer Portal のCallback URLに設定
  # 例: https://abc123.ngrok.io/callback
  ```
- **動的URL対応**: ngrokの動的URLに対応した認証フローの実装

### PKCE 実装要件

- **code_verifier**: 128 文字のランダム文字列生成
- **code_challenge**: SHA256 ハッシュ + Base64URL エンコード
- **code_challenge_method**: S256

### 認証エンドポイント

- **Authorization URL**: `https://twitter.com/i/oauth2/authorize`
- **Token URL**: `https://api.twitter.com/2/oauth2/token`
- **User Info URL**: `https://api.twitter.com/2/users/me`

---

## 実装ステップ

### Step 1: PKCE 生成機能

1. `code_verifier`の生成（43-128 文字）
2. `code_challenge`の生成（SHA256 + Base64URL）
3. `state`パラメータの生成（CSRF 対策）

### Step 2: 認証 URL 生成

1. 必要なパラメータの組み立て
2. クエリパラメータの構築
3. 認証 URL の生成・表示

### Step 3: コールバック処理

1. 認証コードの受け取り
2. `state`パラメータの検証
3. エラーハンドリング

### Step 4: トークン取得

1. authorization code の交換
2. access token・refresh token の取得
3. トークン情報の保存

### Step 5: ユーザー情報取得

1. `/2/users/me`エンドポイントの呼び出し
2. ユーザー情報の表示
3. 認証状態の管理

---

## 画面設計

### 未認証状態

```
X Scheduler Pro
===============

🔐 Xアカウントでログインしてください

[📱 Xでログイン]

* 投稿権限が必要です
* 安全なOAuth 2.0認証を使用
```

### 認証中状態

```
X Scheduler Pro
===============

🔄 認証処理中...

Xの認証画面で承認してください
```

### 認証済み状態

```
X Scheduler Pro
===============

✅ ログイン中: @username

🔹 アクセストークン: 有効
🔹 有効期限: 2024-12-31 23:59:59
🔹 権限: 投稿, ユーザー情報読み取り

[🚪 ログアウト]
```

---

## エラーハンドリング

### 認証エラー

- **access_denied**: ユーザーが認証を拒否
- **invalid_request**: リクエストパラメータの不備
- **server_error**: X 側のサーバーエラー

### トークンエラー

- **invalid_grant**: 無効な認証コード
- **expired_token**: トークンの期限切れ
- **invalid_token**: 無効なトークン

### ネットワークエラー

- **connection_error**: 接続エラー
- **timeout**: タイムアウト
- **rate_limit**: レート制限

---

## セキュリティ考慮事項

### PKCE 実装

- `code_verifier`の安全な生成
- `code_challenge`の正確な計算
- 一意性の確保

### State 検証

- CSRF 攻撃の防止
- state パラメータの検証
- セッション管理

### トークン保護

- Streamlit Secrets機能の活用（`.streamlit/secrets.toml`）
- メモリ内での適切な管理
- ログ出力時の機密情報除外
- セッション終了時のクリア
- セッションタイムアウト（30分）の実装

### HTTPS・CORS対応

- 開発環境：Windows側ngrokによるHTTPS化
- 本番環境：適切なドメイン設定
- CORS設定による許可ドメインの制限
- OAuth callback URLの環境別管理

---

## テスト項目

### 基本機能テスト

- [ ] 認証ボタンの正常動作
- [ ] X 認証画面への正常リダイレクト
- [ ] 認証コードの正常受け取り
- [ ] トークン取得の成功
- [ ] ユーザー情報の正常取得・表示

### エラーテスト

- [ ] 認証拒否時の適切なエラー表示
- [ ] 無効なコールバックの処理
- [ ] トークン期限切れの処理
- [ ] ネットワークエラーの処理

### セキュリティテスト

- [ ] PKCE 検証の正常動作
- [ ] State 検証の正常動作
- [ ] トークンの適切な保護
- [ ] セッション管理の安全性

---

## 成果物

### 実装ファイル

- `auth.py`: OAuth 認証クラス
- `main.py`: Streamlit メインアプリ
- `config.py`: 設定管理
- `utils.py`: ユーティリティ関数

### ドキュメント

- セットアップ手順書
- X Developer Portal 設定手順
- 環境変数設定ガイド
- トラブルシューティングガイド

### テスト結果

- 機能テスト結果レポート
- セキュリティテスト結果
- パフォーマンステスト結果

---

## 次のタスクへの引き継ぎ

### 提供機能

- 認証済みユーザーの判定機能
- 有効なアクセストークンの提供
- ユーザー情報の取得機能

### セッション状態

- `st.session_state.authenticated`: 認証状態
- `st.session_state.access_token`: アクセストークン
- `st.session_state.user_info`: ユーザー情報

この基盤により、Task 2 では安全に認証状態を前提とした機能開発が可能になります。
