# Azure インフラストラクチャ コスト試算

## 概要

X Scheduler Pro のAzureインフラストラクチャにおける月額コスト試算書です。Japan East リージョンでの2024年度価格を基準に算出しています。

## デプロイリソース概要

本プロジェクトでは以下のAzureリソースがデプロイされます：

- Web App (Streamlit フロントエンド)
- Azure Functions (自動投稿システム)
- Storage Account (Functions用)
- Key Vault (機密情報管理)
- Application Insights (監視・ログ)
- Managed Identity (認証)

## 📊 月額コスト試算表

| リソース | SKU/プラン | 仕様 | 想定使用量 | 月額コスト(¥) | 月額コスト($) |
|---------|-----------|------|-----------|-------------|-------------|
| **App Service Plan** | Basic B1 | 1.75GB RAM, 100GB Storage | 24時間稼働 | **7,115** | **47.00** |
| **Azure Functions** | Windows Consumption | 512MB メモリ上限 | 5万実行/月, 平均100MB×1秒 | **0** | **0** |
| **Storage Account** | Standard_LRS | 汎用v2 | 1GB保存, 1万トランザクション | **5** | **0.03** |
| **Key Vault** | Standard | HSM無し | 1万オペレーション | **3** | **0.03** |
| **Application Insights** | Pay-as-you-go | ログ・メトリクス収集 | 100MB データ取り込み | **0** | **0** |
| **Managed Identity** | System/User Assigned | OIDC認証 | 制限なし | **0** | **0** |
| **合計** | - | - | - | **7,123** | **47.06** |

## 🔍 詳細分析

### App Service Plan (B1) - 主要コスト要素
- **仕様**: 1コア, 1.75GB RAM, 100GB一時ストレージ
- **SLA**: 99.9% 可用性保証
- **特徴**: Linux コンテナ対応, カスタムドメイン, SSL証明書対応
- **コスト**: ¥7,115/月（VM稼働時間による固定費用）

### Azure Functions (Consumption) - 無料枠活用
- **無料枠**: 月100万実行 + 40万GB秒
- **想定実行**: Timer Trigger 4回/日 × 30日 = 120回/月
- **メモリ使用**: 100MB × 1秒 × 120回 = 12GB秒/月
- **結果**: 完全に無料枠内で運用可能

### Storage Account - 最小コスト
- **用途**: Azure Functions ランタイム用ストレージ
- **容量**: 1GB (Functions アーティファクト保存)
- **トランザクション**: 1万回/月 (Functions起動・実行時)
- **コスト**: ストレージ料金 + トランザクション料金

### Key Vault - セキュリティ必須コスト
- **用途**: X API認証情報、暗号化キー保存
- **オペレーション**: 1万回/月 (アプリ起動時の秘密情報取得)
- **セキュリティ**: HSMレベルでない標準的な暗号化

### Application Insights - 無料枠活用
- **無料枠**: 月5GB データ取り込み
- **想定使用**: 100MB/月 (アプリログ + Functionsテレメトリ)
- **結果**: 無料枠内で十分

## 💰 コスト最適化オプション

### 開発・検証環境向け (月額 ¥8)
```
App Service Plan: F1 Free → ¥0
その他サービス: 変更なし → ¥8
合計: ¥8/月
```
**制限**: 
- 60分/日の実行時間制限
- カスタムドメイン不可
- 可用性SLA なし

### 本番環境 - 現構成 (月額 ¥7,123)
```
現在の構成を維持
99.9% SLA保証
24時間安定稼働
```

### エンタープライズ環境向け (月額 ¥14,230)
```
App Service Plan: S1 Standard → ¥14,230
- 1.75GB RAM, 50GB Storage
- 99.95% SLA
- 自動スケール対応
- ステージング スロット
```

## 📈 使用量スケーリング影響

### Azure Functions スケールアウト時
| 月間実行回数 | GB秒使用量 | 追加コスト | 
|------------|-----------|-----------|
| 50万回 | 50万GB秒 | ¥192 |
| 100万回 | 100万GB秒 | ¥384 |
| 200万回 | 200万GB秒 | ¥768 |

### Storage Account 使用量増加時
| 保存容量 | 月額追加コスト |
|---------|-------------|
| 10GB | ¥50 |
| 100GB | ¥500 |
| 1TB | ¥5,000 |

## 🌍 他リージョン比較

| リージョン | App Service B1 | 差額 |
|-----------|---------------|------|
| Japan East | ¥7,115 | - |
| Japan West | ¥6,290 | -¥825 |
| East US | ¥5,850 | -¥1,265 |
| West Europe | ¥6,500 | -¥615 |

## 💡 コスト管理推奨事項

### 1. Azure Cost Management 設定
```bash
# 月額予算アラート設定
az consumption budget create \
  --budget-name "x-scheduler-budget" \
  --amount 10000 \
  --time-grain Monthly
```

### 2. リソース監視
- Application Insights によるパフォーマンス監視
- Azure Monitor によるコスト アラート
- 未使用リソースの定期確認

### 3. 自動シャットダウン（開発環境）
```bash
# 夜間・週末の App Service 停止スケジュール設定
az webapp config appsettings set \
  --name ${APP_NAME}-webapp \
  --settings WEBSITE_TIME_ZONE="Asia/Tokyo"
```

## 📋 想定外コスト要素

### 追加発生の可能性があるコスト
1. **データ転送料金**: アウトバウンドトラフィック（通常は月5GBまで無料）
2. **Firestore**: Google Cloud Platform側での課金（別途）
3. **カスタムドメイン SSL**: App Service Managed Certificate は無料
4. **Log Analytics**: Application Insights データ保持延長時

### コスト上昇トリガー
- ユーザー数急増によるApp Service スケールアップ
- Azure Functions 実行回数の大幅増加
- Storage Account への大量データ保存
- Key Vault への高頻度アクセス

## 🎯 まとめ

- **開発環境**: 月額 ¥8 で十分な機能
- **本番環境**: 月額 ¥7,123 でエンタープライズレベル
- **スケーラビリティ**: 需要に応じて柔軟にコスト調整可能
- **コストパフォーマンス**: 類似サービスと比較して非常に競争力のある価格

---

## 更新履歴

- **2024/08/11**: 初版作成（Japan East 価格ベース）
- 価格は2024年8月時点での公開情報を基に算出
- 実際の請求額は使用量や為替レート、Microsoftとの契約内容により変動する可能性があります

---

*本資料は Azure 公式価格情報および価格計算ツールを基に作成されています。*
*最新の価格情報については [Azure 料金計算ツール](https://azure.microsoft.com/pricing/calculator/) をご確認ください。*