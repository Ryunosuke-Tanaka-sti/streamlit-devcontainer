"""
Firebase/Firestore クライアント

Firebase Admin SDKを使用したFirestore接続とデータ管理
"""

import base64
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

import firebase_admin
from firebase_admin import credentials, firestore
from cryptography.fernet import Fernet
from google.cloud.firestore_v1 import FieldFilter


class FirebaseClient:
    """Firebase/Firestore クライアント"""

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
        if not firebase_admin._apps:
            # サービスアカウントキーの取得
            cred = self._get_credentials()

            # Firebaseアプリケーションの初期化
            firebase_admin.initialize_app(cred)

        # Firestoreクライアントの取得
        self._db = firestore.client()

        # 暗号化キーの設定
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if encryption_key:
            self._cipher = Fernet(encryption_key.encode())

    def _get_credentials(self):
        """Firebase認証情報を取得"""
        # 方法1: ファイルパスから
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            return credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

        # 方法2: Base64エンコードされたJSONから
        if os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64"):
            service_account_json = base64.b64decode(
                os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
            ).decode()
            service_account_dict = json.loads(service_account_json)
            return credentials.Certificate(service_account_dict)

        raise ValueError("Firebase認証情報が設定されていません")

    @property
    def db(self):
        """Firestoreデータベースインスタンスを取得"""
        return self._db

    def encrypt_token(self, token: str) -> str:
        """トークンを暗号化"""
        if not self._cipher:
            raise ValueError("暗号化キーが設定されていません")
        return self._cipher.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """トークンを復号化"""
        if not self._cipher:
            raise ValueError("暗号化キーが設定されていません")
        return self._cipher.decrypt(encrypted_token.encode()).decode()

    # === Users コレクション操作 ===

    def save_user_token(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        user_id: str = "main_user",
    ) -> bool:
        """ユーザーのアクセストークンとリフレッシュトークンを暗号化して保存"""
        try:
            encrypted_access_token = self.encrypt_token(access_token)
            user_data = {
                "accessToken": encrypted_access_token,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }

            # リフレッシュトークンがあれば暗号化して保存
            if refresh_token:
                encrypted_refresh_token = self.encrypt_token(refresh_token)
                user_data["refreshToken"] = encrypted_refresh_token

            self._db.collection("users").document(user_id).set(user_data, merge=True)
            return True
        except Exception as e:
            print(f"トークン保存エラー: {e}")
            return False

    def get_user_tokens(self, user_id: str = "main_user") -> Dict[str, Optional[str]]:
        """ユーザーのアクセストークンとリフレッシュトークンを取得して復号化"""
        try:
            doc = self._db.collection("users").document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                result = {"access_token": None, "refresh_token": None}

                if "accessToken" in data:
                    result["access_token"] = self.decrypt_token(data["accessToken"])

                if "refreshToken" in data:
                    result["refresh_token"] = self.decrypt_token(data["refreshToken"])

                return result
            return {"access_token": None, "refresh_token": None}
        except Exception as e:
            print(f"トークン取得エラー: {e}")
            return {"access_token": None, "refresh_token": None}

    def get_user_token(self, user_id: str = "main_user") -> Optional[str]:
        """ユーザーのアクセストークンを取得して復号化（後方互換性のため維持）"""
        tokens = self.get_user_tokens(user_id)
        return tokens.get("access_token")

    # === Posts コレクション操作 ===

    def create_post(
        self,
        content: str,
        post_date: Optional[str] = None,
        time_slot: Optional[int] = None,
    ) -> Optional[str]:
        """投稿を作成"""
        try:
            post_data = {
                "postDate": post_date or datetime.now().strftime("%Y/%m/%d"),
                "timeSlot": time_slot,
                "isPosted": False,
                "content": content,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "postedAt": None,
                "xPostId": None,
                "errorMessage": None,
            }

            # ドキュメントを追加
            doc_ref = self._db.collection("posts").add(post_data)
            return doc_ref[1].id
        except Exception as e:
            print(f"投稿作成エラー: {e}")
            return None

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
            return True
        except Exception as e:
            print(f"投稿更新エラー: {e}")
            return False

    def get_posts_by_date(
        self, date_str: str, is_posted: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """特定日の投稿を取得"""
        try:
            query = self._db.collection("posts").where(
                filter=FieldFilter("postDate", "==", date_str)
            )

            if is_posted is not None:
                query = query.where(filter=FieldFilter("isPosted", "==", is_posted))

            docs = query.stream()
            posts = []
            for doc in docs:
                post_data = doc.to_dict()
                post_data["id"] = doc.id
                posts.append(post_data)

            return posts
        except Exception as e:
            print(f"投稿取得エラー: {e}")
            return []

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

            return posts
        except Exception as e:
            print(f"予約投稿取得エラー: {e}")
            return []

    def get_recent_posts(
        self, limit: int = 10, posted_only: bool = True
    ) -> List[Dict[str, Any]]:
        """最近の投稿を取得"""
        try:
            query = self._db.collection("posts")

            if posted_only:
                query = query.where(filter=FieldFilter("isPosted", "==", True))
                query = query.order_by("postedAt", direction=firestore.Query.DESCENDING)
            else:
                query = query.order_by(
                    "createdAt", direction=firestore.Query.DESCENDING
                )

            query = query.limit(limit)
            docs = query.stream()

            posts = []
            for doc in docs:
                post_data = doc.to_dict()
                post_data["id"] = doc.id
                posts.append(post_data)

            return posts
        except Exception as e:
            print(f"最近の投稿取得エラー: {e}")
            return []

    def delete_post(self, post_id: str) -> bool:
        """投稿を削除"""
        try:
            self._db.collection("posts").document(post_id).delete()
            return True
        except Exception as e:
            print(f"投稿削除エラー: {e}")
            return False


def get_firebase_client() -> FirebaseClient:
    """Firebaseクライアントのシングルトンインスタンスを取得"""
    return FirebaseClient()
