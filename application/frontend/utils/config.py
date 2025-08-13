"""設定管理モジュール"""

import os
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import streamlit as st


class Config:
    """アプリケーション設定管理クラス"""

    # X API 設定
    X_CLIENT_ID: Optional[str] = None
    X_CLIENT_SECRET: Optional[str] = None
    X_REDIRECT_URI: Optional[str] = None

    # OAuth エンドポイント
    X_AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
    X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
    X_USER_INFO_URL = "https://api.x.com/2/users/me"
    X_TWEET_URL = "https://api.x.com/2/tweets"

    # レート制限
    DAILY_POST_LIMIT = 17
    MONTHLY_POST_LIMIT = 500

    # セッション設定
    SESSION_TIMEOUT_MINUTES = 30

    # OAuth スコープ
    OAUTH_SCOPES = ["tweet.write", "users.read", "tweet.read", "offline.access"]

    # Firebase/Firestore 設定
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIRESTORE_REGION: str = "asia-northeast1"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    FIREBASE_SERVICE_ACCOUNT_BASE64: Optional[str] = None
    ENCRYPTION_KEY: Optional[str] = None
    FIRESTORE_EMULATOR_HOST: Optional[str] = None

    # 投稿時間スロット
    TIME_SLOTS = [
        {"slot": 0, "time": "09:00", "label": "朝9時"},
        {"slot": 1, "time": "12:00", "label": "昼12時"},
        {"slot": 2, "time": "15:00", "label": "午後3時"},
        {"slot": 3, "time": "21:00", "label": "夜9時"},
    ]

    @classmethod
    def load_from_env(cls):
        """環境変数から設定を読み込み"""
        cls.X_CLIENT_ID = os.getenv("X_CLIENT_ID")
        cls.X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
        cls.X_REDIRECT_URI = os.getenv(
            "X_REDIRECT_URI", "http://localhost:8501/callback"
        )

        # Firebase設定
        cls.FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
        cls.FIRESTORE_REGION = os.getenv("FIRESTORE_REGION", "asia-northeast1")
        cls.GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        cls.FIREBASE_SERVICE_ACCOUNT_BASE64 = os.getenv(
            "FIREBASE_SERVICE_ACCOUNT_BASE64"
        )
        cls.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
        cls.FIRESTORE_EMULATOR_HOST = os.getenv("FIRESTORE_EMULATOR_HOST")

    @classmethod
    def load_from_secrets(cls):
        """Streamlit Secretsから設定を読み込み"""
        try:
            cls.X_CLIENT_ID = st.secrets.get("X_CLIENT_ID")
            cls.X_CLIENT_SECRET = st.secrets.get("X_CLIENT_SECRET")
            cls.X_REDIRECT_URI = st.secrets.get(
                "X_REDIRECT_URI", "http://localhost:8501/callback"
            )

            # Firebase設定
            cls.FIREBASE_PROJECT_ID = st.secrets.get("FIREBASE_PROJECT_ID")
            cls.FIRESTORE_REGION = st.secrets.get("FIRESTORE_REGION", "asia-northeast1")
            cls.GOOGLE_APPLICATION_CREDENTIALS = st.secrets.get(
                "GOOGLE_APPLICATION_CREDENTIALS"
            )
            cls.FIREBASE_SERVICE_ACCOUNT_BASE64 = st.secrets.get(
                "FIREBASE_SERVICE_ACCOUNT_BASE64"
            )
            cls.ENCRYPTION_KEY = st.secrets.get("ENCRYPTION_KEY")
            cls.FIRESTORE_EMULATOR_HOST = st.secrets.get("FIRESTORE_EMULATOR_HOST")
        except Exception:
            pass

    @classmethod
    def initialize(cls):
        """設定を初期化（環境変数とSecretsの両方を試行）"""
        cls.load_from_env()
        cls.load_from_secrets()

        if not cls.X_CLIENT_ID:
            # 開発時は警告のみで続行（実際のOAuth使用時に必要）
            print(
                "警告: X_CLIENT_ID が設定されていません。.env ファイルまたは Streamlit Secrets を確認してください。"
            )

    @classmethod
    def get_redirect_uri(cls, use_ngrok: bool = False) -> str:
        """リダイレクトURIを取得（ngrok対応）"""
        if use_ngrok and "ngrok" in (cls.X_REDIRECT_URI or ""):
            return cls.X_REDIRECT_URI
        return cls.X_REDIRECT_URI or "http://localhost:8501/callback"

    @classmethod
    def is_development(cls) -> bool:
        """開発環境かどうかを判定"""
        return "localhost" in (cls.X_REDIRECT_URI or "") or "ngrok" in (
            cls.X_REDIRECT_URI or ""
        )

    @classmethod
    def get_time_slot_label(cls, slot: int) -> str:
        """時間スロットのラベルを取得"""
        for ts in cls.TIME_SLOTS:
            if ts["slot"] == slot:
                return ts["label"]
        return "不明"

    @classmethod
    def get_time_slot_time(cls, slot: int) -> str:
        """時間スロットの時刻を取得"""
        for ts in cls.TIME_SLOTS:
            if ts["slot"] == slot:
                return ts["time"]
        return "00:00"


# 初期化
Config.initialize()
