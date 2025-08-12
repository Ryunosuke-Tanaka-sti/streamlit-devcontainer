# Streamlit本番環境Docker構築ガイド｜セキュリティ設定分離完全対応 | SIOS Tech. Lab

**URL:** [https://tech-lab.sios.jp/archives/48313](https://tech-lab.sios.jp/archives/48313)

**メタディスクリプション:** Streamlit本番環境用Docker構築を実践解説。DevContainer開発からセキュアな本番デプロイまで、config.prod.toml設定分離と非rootユーザー実行を完全網羅。軽量slimイメージとパフォーマンス最適化、トラブルシューティングまで詳細ガイド

## 目次

1. [挨拶](#挨拶)
2. [事前準備](#事前準備)
3. [今回の目標](#今回の目標)
4. [開発環境と本番環境の設定戦略](#開発環境と本番環境の設定戦略)
   - [開発環境の特徴](#開発環境の特徴)
   - [本番環境での課題](#本番環境での課題)
   - [設定分離のメリット](#設定分離のメリット)
5. [本番環境用Dockerfileの詳細解説](#本番環境用dockerfileの詳細解説)
   - [ベースイメージの選択理由](#ベースイメージの選択理由)
   - [セキュリティ対策のポイント](#セキュリティ対策のポイント)
   - [パフォーマンス最適化の工夫](#パフォーマンス最適化の工夫)
   - [設定ファイルの適切な管理](#設定ファイルの適切な管理)
   - [Stremlit HealthCheckについて](#stremlit-healthcheckについて)
6. [本番環境用Streamlit設定（config.prod.toml）](#本番環境用streamlit設定configprodtoml)
7. [動作確認](#動作確認)
   - [Dockerイメージのビルド](#dockerイメージのビルド)
   - [コンテナの起動と確認](#コンテナの起動と確認)
   - [クリーンアップ](#クリーンアップ)
8. [よくあるエラーと対処法](#よくあるエラーと対処法)
   - [ポートが既に使用されている場合](#ポートが既に使用されている場合)
   - [設定ファイルが見つからない場合](#設定ファイルが見つからない場合)
   - [権限エラーが発生する場合](#権限エラーが発生する場合)
9. [まとめ](#まとめ)

## **挨拶**

ども！お久しぶりです。Claudeを活用した開発手法の模索に真剣に取り組んでいる龍ちゃんです。

合間でStreamlitアプリの開発もちょこちょこやっているんですが、前回は「[DevContainerでStreamlit開発を始める方法：Docker+VSCode](https://tech-lab.sios.jp/archives/48239)」でStreamlitの開発コンテナ環境を構築しました。

開発環境は整ったものの、「いざ本番環境にデプロイしようとしたら、設定が開発環境のままで困った…」という経験、皆さんもありませんか？実際に私も最初の頃、開発用の設定のままAzureにデプロイして、エラー情報が丸見えになってしまったことがあります。

今回はそんな課題を解決するため、**本番環境用Dockerfileの構築手法**を共有していきたいと思います！

**今回の内容**: 「Streamlit 本番環境用Dockerfileの作成」

- セキュリティを考慮したコンテナ設計
- 開発環境と本番環境の適切な設定分離
- プロダクション向けStreamlit最適化

## **事前準備**

事前準備として、[前回のVSCode環境で、コンテナを用いてStreamlit環境を構築した記事](https://tech-lab.sios.jp/archives/48239)の内容をベースに進めていきます。

まだ環境が整っていない方は、その記事を参考に環境を構築するか、[サンプルリポジトリ](https://github.com/Ryunosuke-Tanaka-sti/streamlit-devcontainer)を参照してください。

**前提条件**：

- Docker Desktop がインストール済み
- 基本的なStreamlitアプリが作成済み
- VSCodeでの開発経験（推奨）

今回の内容はStreamlitのDockerビルドに関するものですが、環境が完全に一致していなくても動作します。使える部分だけを取り入れていただければ問題ありません。

## **今回の目標**

今回の目標は、**本番環境用のDockerfileを作成し、実際にローカルでビルド・動作確認すること**です。

また、Streamlit用のプロダクション環境向け設定ファイル（config.prod.toml）の作成も目指しています。

**具体的な手順**：

1. 本番環境用Dockerfileの作成
2. Streamlit設定ファイル（config.prod.toml）の最適化
3. Dockerコマンドを用いた動作確認

**最終的な成果物**：

- セキュリティを考慮した本番環境用Dockerfile
- プロダクション最適化されたStreamlit設定
- 即座にデプロイ可能なDockerイメージ

今回作成するディレクトリ構造は以下のようになります：

```
.
├── .devcontainer
│   ├── Dockerfile
│   ├── compose.yml
│   └── devcontainer.json
├── .gitignore
├── .streamlit
│   └── config.prod.toml             # 本番環境用Streamlit設定ファイル
├── Dockerfile                       # 本番環境用Dockerfile
├── README.md
├── requirements.txt
├── setup.cfg
└── src
    ├── chat.py
    ├── demo.py
    └── main.py
```

## **開発環境と本番環境の設定戦略**

ここで重要なのが、**開発環境と本番環境の設定を明確に分離する**ことです。実際のプロジェクトでどちらを選ぶべきか、迷うところですよね。

### **開発環境の特徴**

開発環境では、特別な設定を行っていませんでした。これはStreamlitのデフォルト設定に開発者向けの便利機能がすでに組み込まれているからです：

- **エラーメッセージの詳細表示**: デバッグに便利
- **ファイル変更時の自動リロード**: ホットリロード機能
- **開発者ツールの表示**: パフォーマンス情報など
- **詳細なデバッグ情報**: トラブルシューティングに有用

### **本番環境での課題**

一方、本番環境ではこれらの機能は不要どころか、**ユーザー体験を損なう要因**になります：

- エラーの詳細情報がエンドユーザーに表示される（セキュリティリスク）
- 不要な開発者ツールが表示されて混乱を招く
- そもそもソースコードが変更されることがないのでリロード機能は不要
- リソース使用量が最適化されていない

### **設定分離のメリット**

そこで、本番環境専用の設定ファイル（config.prod.toml）を作成することで：

- **セキュリティ向上**: 不要な情報の非表示化
- **パフォーマンス最適化**: 開発機能の無効化
- **ユーザー体験向上**: クリーンなインターフェース
- **運用効率化**: 環境に応じた適切な設定

また、VSCode開発時に必要な情報（.vscodeディレクトリなど）や開発時にのみ必要な情報を本番環境のビルドに含めないことで、**より軽量なDockerイメージ**を実現できます。

開発環境では、DevContainerで開発するために専用イメージを使用していましたが、これには多くの設定が含まれた重いイメージになっています。本番環境ではこれらを削ぎ落として、極力小さなベースイメージを使用したいという意図があります。

環境分離のメリットとしては、**イメージの軽量化**や**不要情報の削除によるセキュリティリスクの回避**が挙げられます。

## **本番環境用Dockerfileの詳細解説**

それでは、本番環境用Dockerfileについて詳しく見ていきます。

ベースイメージの選択に関しては、こちらの「[Dockerイメージの選び方ガイド](https://tech-lab.sios.jp/archives/48204)」が参考になります。

Dockerfileのベースとしては、[公式リファレンスの「Deploy Streamlit using Docker」](https://docs.streamlit.io/deploy/tutorials/docker)を参照しています。

```dockerfile
# 本番環境用 - Python 3.11 slim イメージ
FROM python:3.11-slim

# 非rootユーザーでの実行（セキュリティ対策）
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 作業ディレクトリの設定
WORKDIR /app

# システムの更新と必要最小限のパッケージをインストール
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pythonの設定（パフォーマンス最適化）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 依存関係ファイルをコピー
COPY requirements.txt .

# Pythonパッケージのインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY ./src .

# Streamlit設定ファイルを作成
RUN mkdir -p .streamlit
COPY .streamlit/config.prod.toml .streamlit/config.toml

# ファイルの所有権を変更（セキュリティ対策）
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# ポート公開
EXPOSE 8501

# Streamlitアプリの起動
CMD ["streamlit", "run", "main.py"]
```

### **ベースイメージの選択理由**

こちらが本番環境のDockerfileになります。ベースイメージとしては、**Python 3.11のslimイメージ**を使用し、開発環境と同じバージョンに揃えています。

slimイメージを選択した理由：

- 必要最小限のパッケージのみ含有（セキュリティリスク軽減）
- イメージサイズが小さい（デプロイ時間短縮）
- 本番環境に不要な開発ツールが含まれていない

### **セキュリティ対策のポイント**

セキュリティのために**非rootユーザーでの実行**を行うためにユーザーを作成し、システムの更新と必要最小限のパッケージのインストールも実施しています。

### **パフォーマンス最適化の工夫**

Pythonアプリケーションを動かすための手順としては、まず依存ファイルをコピーして必要なパッケージをインストールし、その後、srcディレクトリ内のアプリケーションコードとStreamlitの設定ファイルをコピーしています。

### **設定ファイルの適切な管理**

特に重要な点は**Streamlitの設定ファイル（config.toml）の作成部分**です。.streamlitディレクトリを作成し、ホスト側にある.streamlitディレクトリ内の**config.prod.toml**ファイルを、コンテナ内では単に**config.toml**としてコピーしています。

これにより、設定項目が本番環境用のconfigとして正しく認識され、プロダクション用の設定を適切に管理できます。また、config.prod.tomlというファイル名にすることで、開発環境では読み込まれないという利点もあります。

公開ポートとしては8501を指定し、最終的にStreamlitを起動するコマンドを実行しています。

### Stremlit HealthCheckについて

[公式のこちらのページ](https://docs.streamlit.io/deploy/tutorials/docker)でDockerのコンテナが起動しているかをHealth Checkを行っています。これはStreamlitを確実に動作させるために必要なので追加しておきます。

ヘルスチェックにより、コンテナオーケストレーション（Kubernetes、Docker Swarm等）が自動的に異常なコンテナを検知・再起動できるようになります

## **本番環境用Streamlit設定（config.prod.toml）**

このファイルは**本番環境用のStreamlit設定ファイル**です。詳細な内容については、[Streamlit公式のドキュメント](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)を参照してください。

ファイル内には一通り必要な設定項目にコメントを付けていますので、それぞれの設定が必要かどうか判断していただければと思います。

実装としては以下のようになります：

```toml
# Streamlit 本番環境用設定ファイル
# 各設定項目の詳細説明付き

[server]
# ブラウザを自動で開かない（サーバー環境での実行に適している）
# デフォルト: false
headless = true

# Streamlitアプリが待ち受けるポート番号
# デフォルト: 8501
port = 8501

# サーバーがリッスンするIPアドレス
# "0.0.0.0" で全てのネットワークインターフェースからの接続を許可
# デフォルト: (未設定)
address = "0.0.0.0"

# 静的ファイル配信機能を無効化（セキュリティ向上）
# staticディレクトリからのファイル配信を禁止
# デフォルト: false
enableStaticServing = false

# ファイル変更時の自動再実行を無効化（本番環境では不要）
# 開発環境でのみ有効にすべき機能
# デフォルト: false
runOnSave = false

[browser]
# Streamlitへの使用統計送信を無効化（プライバシー保護）
# 本番環境では通常無効化する
# デフォルト: true
gatherUsageStats = false

# ブラウザが接続すべきサーバーアドレス
# コンテナ環境では "0.0.0.0" を指定
# デフォルト: "localhost"
serverAddress = "0.0.0.0"

# ブラウザが接続すべきポート番号
# server.portと同じ値を設定
# デフォルト: server.portの値
serverPort = 8501

[global]
# 開発モードを無効化（本番環境用の設定）
# 開発者向け機能や詳細なエラー表示を制限
# デフォルト: false
developmentMode = false

# 直接実行時の警告表示を無効化
# "python script.py" での実行時の警告を非表示
# デフォルト: true
showWarningOnDirectExecution = false

[client]
# エラー詳細の表示レベル設定
# "full": 完全なエラー情報を表示（本番環境でも詳細確認のため有効）
# 他の選択肢: "stacktrace", "type", "none"
# デフォルト: "full"
showErrorDetails = "full"

# ツールバーの表示モード設定
# "viewer": 開発者オプションを非表示（本番環境に適している）
# 他の選択肢: "auto", "developer", "minimal"
# デフォルト: "auto"
toolbarMode = "viewer"

# マルチページアプリでのサイドバーナビゲーション表示
# pages/ディレクトリベースのナビゲーションを有効化
# デフォルト: true
showSidebarNavigation = true

[ui]
# Streamlitのトップバーを非表示
# より洗練されたUIを実現（ブランディング向上）
# カスタム設定項目
hideTopBar = true

[theme]
# ダークテーマを適用
# "light" または "dark" から選択可能
# ユーザー体験向上のためのテーマ設定
base = "dark"
```

セキュリティの機能（CORSやXSRF）などの保護機能を無効化にすることもできますが、ここはデプロイ先の構成によって検討するべき内容です。十分に注意して設定項目を決定してください。[Streamlit公式フォーラムでも言及されています](https://discuss.streamlit.io/t/when-to-use-enablecors-and-enablexsrfprotection-parameters/32075)。

## **動作確認**

それでは、実際に作成したDockerfileとconfig.prod.tomlを使って動作確認を行ってみます。

### **Dockerイメージのビルド**

まずはDockerイメージをビルドしてみましょう：

```bash
# Dockerイメージのビルド
docker build -t python-app:test .
```

### **コンテナの起動と確認**

次に、ビルドしたイメージを使ってコンテナを起動します：

```bash
# コンテナの実行
# DevContainerで8501を使用している可能性を考慮して8502に接続
docker run -d -p 8502:8501 --name python-app-test python-app:test

# ログ確認
docker logs python-app-test

# ブラウザでアクセス
# http://localhost:8502
```

### **クリーンアップ**

動作確認が完了したら、コンテナを停止・削除します：

```bash
# コンテナの停止と削除
docker stop python-app-test
docker rm python-app-test

# 不要なイメージの削除（必要に応じて）
docker rmi python-app:test
```

## **よくあるエラーと対処法**

### **ポートが既に使用されている場合**

```bash
# エラー: port is already allocated
# 対処法: 別のポートを使用
docker run -d -p 8503:8501 --name python-app-test python-app:test
```

### **設定ファイルが見つからない場合**

```bash
# .streamlit/config.prod.toml の存在確認
ls -la .streamlit/

# ファイルパスの確認
COPY .streamlit/config.prod.toml .streamlit/config.toml
```

### **権限エラーが発生する場合**

```bash
# ファイル所有権の確認
docker exec -it python-app-test ls -la /app
```

## **まとめ**

今回は**Streamlit本番環境用Dockerfileの構築**について詳しく見てきました。

開発環境と本番環境の設定を適切に分離することで、セキュリティとパフォーマンスの両方を向上させることができました。特に**config.prod.toml**による設定最適化と、**非rootユーザー**でのコンテナ実行は、実際のプロジェクトでも重要なポイントになります。

今回作成したDockerfileは、Azure Container InstancesやAWS Fargate等のクラウドサービスにそのままデプロイできる構成になっています。

次回は、**GitHub Actions + Bicep**を使った**完全自動化デプロイパイプライン**の構築に挑戦します！今回のDockerfileがそのまま活用できるので、ぜひお楽しみに！

それでは、次回の記事でまたお会いしましょう！