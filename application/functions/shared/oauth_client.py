"""
X API OAuth 2.0 認証クライアント (Azure Functions版)

OAuth 2.0 リフレッシュトークンを使用してアクセストークンを更新します。
"""

import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)


class TokenError(Exception):
    """トークン関連エラー"""

    pass


class OAuthClient:
    """X API OAuth 2.0 クライアント (Azure Functions版)"""

    def __init__(self, client_id: str, client_secret: str):
        """
        Args:
            client_id: X API Client ID
            client_secret: X API Client Secret
        """
        if not client_id or not client_secret:
            raise ValueError("Client ID と Client Secret が必要です")

        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://api.x.com/2/oauth2/token"

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        リフレッシュトークンでアクセストークンを更新

        Args:
            refresh_token: リフレッシュトークン

        Returns:
            新しいトークン情報の辞書
            {
                "access_token": str,
                "token_type": str,
                "expires_in": int,
                "refresh_token": str (optional),
                "scope": str,
                "expires_at": str (ISO format)
            }

        Raises:
            TokenError: トークン更新エラー
        """
        if not refresh_token:
            raise ValueError("リフレッシュトークンが必要です")

        # Basic認証用のクレデンシャルをエンコード
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        try:
            logger.info("アクセストークンのリフレッシュを開始")

            response = requests.post(
                self.token_url, data=data, headers=headers, timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()

                # 有効期限を計算
                expires_in = token_data.get("expires_in", 7200)  # デフォルト2時間
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                token_data["expires_at"] = expires_at.isoformat()

                logger.info("アクセストークンのリフレッシュに成功")
                return token_data

            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get(
                    "error_description",
                    error_data.get("error", f"HTTP {response.status_code}"),
                )
                logger.error(f"トークン更新エラー: {error_msg}")
                raise TokenError(f"トークン更新エラー: {error_msg}")

        except requests.exceptions.RequestException as e:
            logger.error(f"ネットワークエラー: {str(e)}")
            raise TokenError(f"ネットワークエラー: {str(e)}")

    def is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        """
        トークンが期限切れかどうかを確認

        Args:
            token_data: トークン情報

        Returns:
            期限切れかどうか
        """
        if "expires_at" not in token_data:
            return True

        try:
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            # 5分の余裕を持たせる
            return datetime.now() >= expires_at - timedelta(minutes=5)
        except (ValueError, TypeError):
            return True

    def verify_token(self, access_token: str) -> bool:
        """
        アクセストークンの検証（X APIのユーザー情報エンドポイントを使用）

        Args:
            access_token: アクセストークン

        Returns:
            有効かどうか
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                "https://api.x.com/2/users/me", headers=headers, timeout=10
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
