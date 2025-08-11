"""Azure Functions設定管理モジュール"""

import os
from typing import Optional
from datetime import datetime


class Config:
    """Azure Functions用設定管理クラス（フロントエンドと共通設定）"""

    # レート制限（フロントエンドと共通）
    DAILY_POST_LIMIT = 17
    MONTHLY_POST_LIMIT = 500

    # Firebase/Firestore 設定（フロントエンドと共通）
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIRESTORE_REGION: str = "asia-northeast1"
    FIREBASE_SERVICE_ACCOUNT_BASE64: Optional[str] = None
    ENCRYPTION_KEY: Optional[str] = None

    # 投稿時間スロット（フロントエンドと共通）
    TIME_SLOTS = [
        {"slot": 0, "time": "09:00", "label": "朝9時"},
        {"slot": 1, "time": "12:00", "label": "昼12時"},
        {"slot": 2, "time": "15:00", "label": "午後3時"},
        {"slot": 3, "time": "21:00", "label": "夜9時"},
    ]

    @classmethod
    def load_from_env(cls):
        """環境変数から設定を読み込み（Firebase関連のみ）"""
        # Firebase設定（フロントエンドと同じ環境変数名を使用）
        cls.FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
        cls.FIRESTORE_REGION = os.getenv("FIRESTORE_REGION", "asia-northeast1")
        cls.FIREBASE_SERVICE_ACCOUNT_BASE64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
        cls.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

    @classmethod
    def initialize(cls):
        """設定を初期化"""
        cls.load_from_env()

    @classmethod
    def get_current_time_slot(cls, now_time: datetime) -> Optional[int]:
        """現在時刻が投稿対象スロットかどうかを判定"""
        current_time_str = now_time.strftime("%H:%M")
        for slot_info in cls.TIME_SLOTS:
            if slot_info["time"] == current_time_str:
                return slot_info["slot"]
        return None  # 投稿時刻ではない

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