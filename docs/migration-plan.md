# Next.js/Nest.js移植計画書

## 概要
現在のStreamlit + Azure Web Appsアーキテクチャから、Next.js（フロントエンド）+ Nest.js（バックエンド）の構成へ移植する計画書です。

## アーキテクチャ概要

### 全体構成
```
┌─────────────────────────────────┐
│  Azure Static Web Apps          │
│  (Next.js - 静的エクスポート)     │
└──────────────┬──────────────────┘
               │ API呼び出し
               ↓
┌─────────────────────────────────┐
│  Azure Web Apps for Container   │
│  (Nest.js - APIサーバー)         │
└──────────────┬──────────────────┘
               │
               ↓
┌─────────────────────────────────┐
│  Firebase Firestore             │
│  (データ永続化)                  │
└─────────────────────────────────┘
```

### 認証フロー
1. **未ログイン状態**: 予約投稿の作成・管理のみ可能
2. **ログイン状態**: 即時投稿 + 予約投稿の全機能が利用可能
3. **OAuth 2.0フロー**: バックエンド主導で実装

## フロントエンド（Next.js）仕様

### 技術スタック
- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS
- **State Management**: Zustand or Context API
- **HTTP Client**: Axios or Fetch API
- **Deployment**: Azure Static Web Apps

### ディレクトリ構成
```
application/frontend-next/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── login/
│   │   └── page.tsx
│   ├── dashboard/
│   │   └── page.tsx
│   ├── posts/
│   │   ├── page.tsx
│   │   └── [id]/
│   │       └── page.tsx
│   └── api/
│       └── [...] (プロキシ用)
├── components/
│   ├── auth/
│   │   ├── LoginButton.tsx
│   │   └── AuthStatus.tsx
│   ├── posts/
│   │   ├── PostForm.tsx
│   │   ├── PostList.tsx
│   │   └── ScheduledPosts.tsx
│   └── ui/
│       └── [...] (共通コンポーネント)
├── lib/
│   ├── api-client.ts
│   ├── auth.ts
│   └── utils.ts
├── public/
├── next.config.js
└── package.json
```

### 主要機能
1. **認証状態の管理**
   - JWTトークンをhttpOnly Cookieで管理
   - バックエンドからの認証状態をヘッダーで受信

2. **投稿機能**
   - 即時投稿（ログイン時のみ）
   - 予約投稿の作成・編集・削除
   - Markdownファイル読み込み

3. **UI/UX**
   - レスポンシブデザイン
   - ダークモード対応
   - リアルタイムバリデーション

### 静的エクスポート設定
```javascript
// next.config.js
module.exports = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true
  }
}
```

## バックエンド（Nest.js）仕様

### 技術スタック
- **Framework**: Nest.js
- **ORM**: Prisma or TypeORM
- **Authentication**: Passport.js
- **API Documentation**: Swagger
- **Deployment**: Azure Web Apps for Container (Docker)

### ディレクトリ構成
```
application/backend-nest/
├── src/
│   ├── auth/
│   │   ├── auth.controller.ts
│   │   ├── auth.service.ts
│   │   ├── auth.module.ts
│   │   ├── strategies/
│   │   │   └── oauth.strategy.ts
│   │   └── guards/
│   │       └── jwt-auth.guard.ts
│   ├── posts/
│   │   ├── posts.controller.ts
│   │   ├── posts.service.ts
│   │   ├── posts.module.ts
│   │   └── dto/
│   │       ├── create-post.dto.ts
│   │       └── update-post.dto.ts
│   ├── scheduled-posts/
│   │   ├── scheduled-posts.controller.ts
│   │   ├── scheduled-posts.service.ts
│   │   └── scheduled-posts.module.ts
│   ├── x-api/
│   │   ├── x-api.service.ts
│   │   └── x-api.module.ts
│   ├── firebase/
│   │   ├── firebase.service.ts
│   │   └── firebase.module.ts
│   ├── common/
│   │   ├── filters/
│   │   ├── interceptors/
│   │   └── pipes/
│   ├── app.module.ts
│   └── main.ts
├── test/
├── Dockerfile
├── docker-compose.yml
└── package.json
```

### APIエンドポイント設計

#### 認証関連
```
GET  /api/auth/login         # OAuth2.0認証URL生成・リダイレクト
GET  /api/auth/callback       # OAuth2.0コールバック処理
POST /api/auth/logout         # ログアウト
GET  /api/auth/me            # 現在のユーザー情報取得
```

#### 投稿関連
```
POST /api/posts              # 即時投稿（要認証）
GET  /api/posts/history      # 投稿履歴取得（要認証）
```

#### 予約投稿関連
```
GET    /api/scheduled-posts           # 予約投稿一覧取得
POST   /api/scheduled-posts           # 予約投稿作成
GET    /api/scheduled-posts/:id       # 予約投稿詳細取得
PUT    /api/scheduled-posts/:id       # 予約投稿更新
DELETE /api/scheduled-posts/:id       # 予約投稿削除
GET    /api/scheduled-posts/analytics # 分析データ取得（未定）
```

### セキュリティ実装
1. **JWT認証**
   - Access Token: 15分
   - Refresh Token: 7日間
   - httpOnly Cookie使用

2. **CORS設定**
   - Static Web Appsのドメインのみ許可
   - 認証ヘッダーの適切な設定

3. **Rate Limiting**
   - IPベースのレート制限
   - APIキーベースの制限（必要に応じて）

### Docker設定
```dockerfile
# Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/main"]
```

## データベース設計

### Firestoreコレクション

#### users
```typescript
{
  uid: string;
  email: string;
  xUsername: string;
  xUserId: string;
  encryptedTokens: {
    accessToken: string;
    refreshToken: string;
  };
  createdAt: Timestamp;
  updatedAt: Timestamp;
}
```

#### posts
```typescript
{
  id: string;
  userId?: string;  // ログインユーザーの場合のみ
  content: string;
  postDate: string;  // YYYY/MM/DD
  timeSlot: number;  // 0-3
  isPosted: boolean;
  postedAt?: Timestamp;
  xPostId?: string;
  errorMessage?: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}
```

#### rate_limits
```typescript
{
  userId: string;
  dailyCount: number;
  monthlyCount: number;
  lastResetDaily: Timestamp;
  lastResetMonthly: Timestamp;
}
```

## 移行計画

### Phase 1: 環境構築（1週間）
- [ ] Next.jsプロジェクト初期化
- [ ] Nest.jsプロジェクト初期化
- [ ] Docker環境構築
- [ ] 開発環境のセットアップ

### Phase 2: バックエンド実装（2週間）
- [ ] 認証システム実装
- [ ] X API統合
- [ ] Firebase統合
- [ ] APIエンドポイント実装
- [ ] テスト作成

### Phase 3: フロントエンド実装（2週間）
- [ ] 基本UIコンポーネント作成
- [ ] 認証フロー実装
- [ ] 投稿機能実装
- [ ] 予約投稿管理機能実装
- [ ] レスポンシブ対応

### Phase 4: 統合・テスト（1週間）
- [ ] フロントエンド・バックエンド統合
- [ ] E2Eテスト実装
- [ ] パフォーマンス最適化
- [ ] セキュリティ監査

### Phase 5: デプロイ（3日）
- [ ] Azure環境構築
- [ ] CI/CDパイプライン設定
- [ ] 本番環境デプロイ
- [ ] 監視・ログ設定

## 環境変数

### フロントエンド（.env.local）
```bash
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_APP_URL=https://app.example.com
```

### バックエンド（.env）
```bash
# X API
X_CLIENT_ID=
X_CLIENT_SECRET=
X_REDIRECT_URI=

# Firebase
FIREBASE_PROJECT_ID=
FIREBASE_SERVICE_ACCOUNT_BASE64=

# JWT
JWT_SECRET=
JWT_REFRESH_SECRET=

# Encryption
ENCRYPTION_KEY=

# Azure
AZURE_STORAGE_CONNECTION_STRING=

# App
APP_URL=https://app.example.com
API_URL=https://api.example.com
PORT=3000
```

## CI/CD設定

### GitHub Actions
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push Docker image
        # Docker build & push to ACR
      - name: Deploy to Azure Web Apps
        # Deploy container

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Next.js
        run: |
          cd application/frontend-next
          npm ci
          npm run build
      - name: Deploy to Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
```

## 監視・運用

### Application Insights
- APIレスポンスタイム監視
- エラー率監視
- カスタムメトリクス

### ログ管理
- 構造化ログ（JSON形式）
- ログレベル管理
- ログローテーション

### アラート設定
- API障害時の通知
- Rate Limit超過の通知
- デプロイ失敗時の通知

## セキュリティチェックリスト

- [ ] HTTPS通信の強制
- [ ] SQLインジェクション対策
- [ ] XSS対策
- [ ] CSRF対策
- [ ] 適切なCORS設定
- [ ] 機密情報の暗号化
- [ ] 定期的な依存関係の更新
- [ ] ペネトレーションテスト

## リスクと対策

### リスク1: OAuth認証の複雑性
**対策**: Passport.jsの活用と十分なテスト

### リスク2: Rate Limit管理
**対策**: Redis等のキャッシュ層導入検討

### リスク3: スケーラビリティ
**対策**: 水平スケーリング可能な設計

## 参考資料

- [Next.js Documentation](https://nextjs.org/docs)
- [Nest.js Documentation](https://nestjs.com/)
- [Azure Static Web Apps](https://docs.microsoft.com/azure/static-web-apps/)
- [X API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)