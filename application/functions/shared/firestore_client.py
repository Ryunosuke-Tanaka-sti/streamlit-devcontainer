"""
Firebase/Firestore クライアント (Azure Functions版)

Firebase Admin SDKを使用したFirestore接続とデータ管理
"""

import base64
import json
import os
import logging
from typing import Dict, Any, Optional, List

import firebase_admin
from firebase_admin import credentials, firestore
from cryptography.fernet import Fernet
from google.cloud.firestore_v1 import FieldFilter

logger = logging.getLogger(__name__)


class FirestoreClient:
    """Firebase/Firestore クライアント (Azure Functions版)"""

    _instance = None
    _db = None
    _cipher = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Firebase接続を初期化"""
        try:
            if not firebase_admin._apps:
                # サービスアカウントキーの取得
                cred = self._get_credentials()

                # Firebaseアプリケーションの初期化
                firebase_admin.initialize_app(cred)
                logger.info("Firebase初期化完了")

            # Firestoreクライアントの取得
            self._db = firestore.client()

            # 暗号化キーの設定
            encryption_key = os.getenv("ENCRYPTION_KEY")
            if encryption_key:
                self._cipher = Fernet(encryption_key.encode())
                logger.info("暗号化キー設定完了")
            else:
                logger.warning("暗号化キーが設定されていません")

        except Exception as e:
            logger.error(f"Firebase初期化エラー: {e}")
            raise

    def _get_credentials(self):
        """Firebase認証情報を取得"""
        # Base64エンコードされたJSONから
        if os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64"):
            try:
                service_account_json = base64.b64decode(
                    os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
                ).decode()
                service_account_dict = json.loads(service_account_json)
                logger.info("Firebase認証情報をBase64から取得")
                return credentials.Certificate(service_account_dict)
            except Exception as e:
                logger.error(f"Base64認証情報デコードエラー: {e}")
                raise

        raise ValueError("Firebase認証情報が設定されていません")

    @property
    def db(self):
        """Firestoreデータベースインスタンスを取得"""
        return self._db

    def decrypt_token(self, encrypted_token: str) -> str:
        """トークンを復号化"""
        if not self._cipher:
            raise ValueError("暗号化キーが設定されていません")
        return self._cipher.decrypt(encrypted_token.encode()).decode()

    def get_user_token(self, user_id: str = "main_user") -> Optional[str]:
        """ユーザーのアクセストークンを取得して復号化"""
        try:
            doc = self._db.collection("users").document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                if "accessToken" in data:
                    logger.info(f"ユーザートークン取得: {user_id}")
                    return self.decrypt_token(data["accessToken"])
            logger.warning(f"ユーザートークンが見つかりません: {user_id}")
            return None
        except Exception as e:
            logger.error(f"トークン取得エラー: {e}")
            return None

    def get_scheduled_posts(
        self, date_str: str, time_slot: int
    ) -> List[Dict[str, Any]]:
        """特定日時の予約投稿を取得"""
        try:
            docs = (
                self._db.collection("posts")
                .where(filter=FieldFilter("postDate", "==", date_str))
                .where(filter=FieldFilter("timeSlot", "==", time_slot))
                .where(filter=FieldFilter("isPosted", "==", False))
                .stream()
            )

            posts = []
            for doc in docs:
                post_data = doc.to_dict()
                post_data["id"] = doc.id
                posts.append(post_data)

            logger.info(
                f"予約投稿取得: {len(posts)}件 (日付: {date_str}, スロット: {time_slot})"
            )
            return posts
        except Exception as e:
            logger.error(f"予約投稿取得エラー: {e}")
            return []

    def update_post_status(
        self,
        post_id: str,
        is_posted: bool,
        x_post_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """投稿ステータスを更新"""
        try:
            update_data = {
                "isPosted": is_posted,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }

            if is_posted and x_post_id:
                update_data["postedAt"] = firestore.SERVER_TIMESTAMP
                update_data["xPostId"] = x_post_id

            if error_message:
                update_data["errorMessage"] = error_message

            self._db.collection("posts").document(post_id).update(update_data)
            logger.info(f"投稿ステータス更新: {post_id}, 投稿済み: {is_posted}")
            return True
        except Exception as e:
            logger.error(f"投稿更新エラー: {e}")
            return False


def get_firestore_client() -> FirestoreClient:
    """Firestoreクライアントのシングルトンインスタンスを取得"""
    return FirestoreClient()
