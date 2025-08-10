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
COPY . .

RUN pwd

# Streamlit設定ファイルを作成（既にCOPY . .でコピー済み）
RUN cp .streamlit/config.prod.toml .streamlit/config.toml

# Python パスにsrcディレクトリを追加（開発・本番両環境対応）
ENV PYTHONPATH="/app:${PYTHONPATH}"

# ファイルの所有権を変更（セキュリティ対策）
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# ポート公開
EXPOSE 8501

# Streamlitアプリの起動
CMD ["streamlit", "run", "main.py"]
