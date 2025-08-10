# Task 3 詳細分割: Firestore統合・データ管理
## シンプル設計・即時投稿機能優先

## Firestore データ設計（シンプル版）

### users コレクション
```
ドキュメントID: ユーザーID（固定値: "main_user"）
{
  accessToken: string (暗号化済み)
}
```

### posts コレクション
```
ドキュメントID: 自動生成
{
  postDate: string (yyyy/mm/dd形式)
  timeSlot: number (0=9時, 1=12時, 2=13時, 3=20時)
  isPosted: boolean
  content: string
  createdAt: timestamp
  postedAt: timestamp | null
  xPostId: string | null (投稿成功時)
  errorMessage: string | null
}
```

### 複合クエリ設計

#### Firestoreインデックス設定（必須）
```
コレクション: posts
フィールド:
- postDate (昇順)
- timeSlot (昇順)  
- isPosted (昇順)
```

#### 検索パターン例
```javascript
// 1. 特定日の未投稿一覧
posts.where('postDate', '==', '2024/01/15')
     .where('isPosted', '==', false)

// 2. 特定時間帯の投稿済み一覧
posts.where('timeSlot', '==', 1)
     .where('isPosted', '==', true)

// 3. 特定日の特定時間帯
posts.where('postDate', '==', '2024/01/15')
     .where('timeSlot', '==', 2)
     .where('isPosted', '==', false)

// 4. 日付範囲での検索
posts.where('postDate', '>=', '2024/01/01')
     .where('postDate', '<=', '2024/01/31')
     .where('isPosted', '==', true)
```

## 全体構成（7つのサブタスク - シンプル版）

### Task 3-1: Firebase基盤セットアップ（0.5日）
### Task 3-2: 即時投稿機能実装（1.5日）⭐ 優先
### Task 3-3: 投稿履歴管理（1日）
### Task 3-4: 認証トークン管理（0.5日）
### Task 3-5: 予約投稿データ管理（1日）
### Task 3-6: UI統合・ダッシュボード（1.5日）
### Task 3-7: Azure Functions準備・統合テスト（1日）

---

## Task 3-1: Firebase基盤セットアップ

### 🎯 目標
シンプルなFirestore設定とインデックス作成

### 📋 実装内容
- Firebase プロジェクト作成
- Firestore データベース初期化
- **複合インデックス作成**（重要）
- 基本接続テスト

### 🔧 必要なインデックス設定
#### Firebase Console > Firestore > インデックス
1. **投稿検索用複合インデックス**
   - Collection ID: `posts`
   - Fields: `postDate` (Ascending), `timeSlot` (Ascending), `isPosted` (Ascending)

2. **日付範囲検索用インデックス** 
   - Collection ID: `posts`
   - Fields: `postDate` (Ascending), `isPosted` (Ascending)

### ✅ 完了条件
- Firestoreへの基本読み書きが成功
- 複合インデックスが作成済み
- 検索クエリのテストが完了

---

## Task 3-2: 即時投稿機能実装 ⭐

### 🎯 目標
Task 2のMarkdown選択機能と統合し、即座にXに投稿

### 📋 実装内容

#### 投稿データ作成
```python
# 即時投稿時のデータ構造
post_data = {
    'postDate': datetime.now().strftime('%Y/%m/%d'),
    'timeSlot': None,  # 即時投稿は時間帯指定なし
    'isPosted': False,  # 投稿前はfalse
    'content': selected_markdown_content,
    'createdAt': firestore.SERVER_TIMESTAMP,
    'postedAt': None,
    'xPostId': None,
    'errorMessage': None
}
```

#### X API投稿処理
1. アクセストークンを`users/main_user`から取得
2. X API v2でツイート投稿
3. 成功時：`isPosted=True`, `postedAt=現在時刻`, `xPostId=投稿ID`を更新
4. 失敗時：`errorMessage`を記録

#### UI統合
- Task 2の右ペインに「投稿する」ボタン追加
- 文字数カウンター（280文字制限）
- 投稿確認ダイアログ
- 投稿結果表示

### ✅ 完了条件
- Markdownからの即時投稿が成功
- 投稿データがFirestoreに正しく保存
- エラー時の適切な処理

---

## Task 3-3: 投稿履歴管理

### 🎯 目標
投稿履歴の表示と管理機能

### 📋 実装内容

#### 検索・表示機能
```python
# 今日の投稿一覧
today = datetime.now().strftime('%Y/%m/%d')
today_posts = posts_ref.where('postDate', '==', today).get()

# 投稿済み一覧（最新10件）
recent_posted = posts_ref.where('isPosted', '==', True)\
                         .order_by('postedAt', direction='DESCENDING')\
                         .limit(10).get()

# 特定時間帯の予約投稿
scheduled_posts = posts_ref.where('timeSlot', '==', 1)\
                          .where('isPosted', '==', False).get()
```

#### 統計情報
- 今日の投稿数
- 今週の投稿数
- 投稿成功率
- 時間帯別投稿数

#### 管理機能
- 投稿履歴の削除
- 失敗投稿の再試行
- 予約投稿の編集

### ✅ 完了条件
- 複合クエリでの検索が正常動作
- 統計情報が正確に表示
- 履歴管理操作が完了

---

## Task 3-4: 認証トークン管理

### 🎯 目標
アクセストークンのシンプルな管理

### 📋 実装内容

#### トークン保存（シンプル版）
```python
# users/main_user ドキュメントに保存
user_data = {
    'accessToken': encrypted_token  # Fernet暗号化
}
db.collection('users').document('main_user').set(user_data)
```

#### トークン取得
```python
# 暗号化されたトークンを取得・復号化
user_doc = db.collection('users').document('main_user').get()
if user_doc.exists:
    encrypted_token = user_doc.data()['accessToken']
    return cipher.decrypt(encrypted_token.encode()).decode()
```

### 🔐 セキュリティ
- Fernet暗号化による保存
- 環境変数での暗号化キー管理
- セッション内での一時的な平文保持

### ✅ 完了条件
- トークンの暗号化保存が動作
- 復号化してX API呼び出しが成功
- セキュリティ要件を満たす

---

## Task 3-5: 予約投稿データ管理

### 🎯 目標
時間指定投稿の予約機能

### 📋 実装内容

#### 予約投稿作成
```python
# 予約投稿データ
scheduled_post = {
    'postDate': target_date,  # '2024/01/16'
    'timeSlot': time_slot,    # 0,1,2,3
    'isPosted': False,
    'content': content,
    'createdAt': firestore.SERVER_TIMESTAMP,
    'postedAt': None,
    'xPostId': None,
    'errorMessage': None
}
```

#### 時間帯定義
- timeSlot 0: 9時
- timeSlot 1: 12時  
- timeSlot 2: 13時
- timeSlot 3: 20時

#### 重複チェック
```python
# 同じ日・同じ時間帯の予約があるかチェック
existing = posts_ref.where('postDate', '==', target_date)\
                   .where('timeSlot', '==', time_slot)\
                   .where('isPosted', '==', False).get()
```

### ✅ 完了条件
- 予約投稿の作成・編集・削除
- 重複予約の防止
- Azure Functions連携準備

---

## Task 3-6: UI統合・ダッシュボード

### 🎯 目標
統合ダッシュボードの実装

### 📋 実装内容

#### メインダッシュボード
- **今日の状況**: 投稿済み/予約中の件数
- **今日の予定**: 今日予定されている投稿一覧
- **最近の投稿**: 直近の投稿履歴

#### タブ構成
1. **投稿作成**: Task 2のMarkdown選択 + 即時/予約投稿
2. **投稿履歴**: 検索・フィルター機能付きの履歴表示
3. **予約管理**: 予約投稿の一覧・編集
4. **統計**: 投稿分析・トレンド表示

### ✅ 完了条件
- 全機能が統合されたUI
- レスポンシブデザイン
- 直感的な操作性

---

## Task 3-7: Azure Functions準備・統合テスト

### 🎯 目標
Azure Functions連携とシステムテスト

### 📋 実装内容

#### Functions向けクエリ準備
```python
# Azure Functionsが実行する検索クエリ
def get_scheduled_posts_for_time(date_str, time_slot):
    return posts_ref.where('postDate', '==', date_str)\
                   .where('timeSlot', '==', time_slot)\
                   .where('isPosted', '==', False).get()
```

#### 統合テスト
- 即時投稿フローの完全テスト
- 予約投稿作成・管理のテスト
- 複合クエリの性能テスト
- エラーシナリオの検証

#### Task 4連携仕様
- Firestore接続方法
- 投稿データ取得方法
- 投稿完了時の更新方法
- エラー処理方針

### ✅ 完了条件
- 全機能のテストが完了
- Azure Functions連携仕様が確定
- パフォーマンスが要件を満たす

---

## 📊 クエリ性能最適化

### インデックス戦略
```
1. 複合インデックス (postDate, timeSlot, isPosted)
   → 日付・時間帯・投稿状態での検索を高速化

2. 単一フィールドインデックス (postedAt) 
   → 投稿日時での並び替えを高速化
```

### 検索パターン最適化
- **頻繁な検索**: 今日の投稿、特定時間帯の予約
- **バッチ処理**: Azure Functionsでの時間帯別取得
- **統計処理**: 日付範囲での集計クエリ

この設計で、シンプルかつ効率的なFirestore活用が可能になります。複合クエリも問題なく動作し、Azure Functionsとの連携もスムーズになります。