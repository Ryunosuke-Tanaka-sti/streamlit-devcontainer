"""
X API OAuth 2.0 認証クライアント

OAuth 2.0 Authorization Code Flow with PKCE を使用して
X API への認証を行います。
"""

import base64
import requests
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta

from .pkce_utils import PKCEUtils
from ..utils.config import Config


class AuthenticationError(Exception):
    """認証エラー"""

    pass


class TokenExpiredError(AuthenticationError):
    """トークン期限切れエラー"""

    pass


class XOAuthClient:
    """
    X API OAuth 2.0 認証クライアント
    """

    def __init__(self):
        self.client_id = Config.X_CLIENT_ID
        self.client_secret = Config.X_CLIENT_SECRET
        self.redirect_uri = Config.X_REDIRECT_URI

        if not self.client_id:
            raise ValueError("X_CLIENT_ID が設定されていません")

    def generate_authorization_url(self) -> Tuple[str, str, str, str]:
        """
        認証 URL を生成

        Returns:
            (authorization_url, code_verifier, code_challenge, state) のタプル
        """
        # PKCE ペアと state を生成
        code_verifier, code_challenge, state = PKCEUtils.generate_pkce_pair()

        # 認証 URL のパラメータ
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(Config.OAUTH_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        authorization_url = f"{Config.X_AUTHORIZE_URL}?{urlencode(params)}"

        return authorization_url, code_verifier, code_challenge, state

    def exchange_code_for_token(
        self,
        authorization_code: str,
        code_verifier: str,
        state: str,
        received_state: str,
    ) -> Dict[str, Any]:
        """
        認証コードをアクセストークンに交換

        Args:
            authorization_code: X から受け取った認証コード
            code_verifier: PKCE の code_verifier
            state: 送信した state パラメータ
            received_state: 受け取った state パラメータ

        Returns:
            トークン情報の辞書

        Raises:
            AuthenticationError: 認証エラー
        """
        # state パラメータの検証
        if not PKCEUtils.verify_state(state, received_state):
            raise AuthenticationError(
                "state パラメータが一致しません。CSRF 攻撃の可能性があります。"
            )

        # トークンリクエストのパラメータ
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code": authorization_code,
            "code_verifier": code_verifier,
        }

        # Basic認証ヘッダーを追加
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}",
        }

        try:
            response = requests.post(
                Config.X_TOKEN_URL, data=data, headers=headers, timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()

                # 有効期限を計算
                expires_in = token_data.get("expires_in", 7200)  # デフォルト 2時間
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                token_data["expires_at"] = expires_at.isoformat()

                return token_data
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get(
                    "error_description",
                    error_data.get("error", f"HTTP {response.status_code}"),
                )
                raise AuthenticationError(f"トークン取得エラー: {error_msg}")

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"ネットワークエラー: {str(e)}")

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        ユーザー情報を取得

        Args:
            access_token: アクセストークン

        Returns:
            ユーザー情報の辞書

        Raises:
            AuthenticationError: 認証エラー
            TokenExpiredError: トークン期限切れ
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(Config.X_USER_INFO_URL, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise TokenExpiredError("アクセストークンが期限切れです")
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get(
                    "detail", 
                    error_data.get("title", f"HTTP {response.status_code}")
                )
                raise AuthenticationError(f"ユーザー情報取得エラー: {error_msg}")

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"ネットワークエラー: {str(e)}")

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        リフレッシュトークンでアクセストークンを更新

        Args:
            refresh_token: リフレッシュトークン

        Returns:
            新しいトークン情報

        Raises:
            AuthenticationError: 認証エラー
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        # Basic認証ヘッダーを追加
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}",
        }

        try:
            response = requests.post(
                Config.X_TOKEN_URL, data=data, headers=headers, timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()

                # 有効期限を計算
                expires_in = token_data.get("expires_in", 7200)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                token_data["expires_at"] = expires_at.isoformat()

                return token_data
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get(
                    "error_description",
                    error_data.get("error", f"HTTP {response.status_code}"),
                )
                raise AuthenticationError(f"トークン更新エラー: {error_msg}")

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"ネットワークエラー: {str(e)}")

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

    @staticmethod
    def parse_callback_url(
        callback_url: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        コールバックURLからパラメータを抽出

        Args:
            callback_url: X からのコールバックURL

        Returns:
            (authorization_code, state, error) のタプル
        """
        try:
            parsed = urlparse(callback_url)
            query_params = parse_qs(parsed.query)

            code = query_params.get("code", [None])[0]
            state = query_params.get("state", [None])[0]
            error = query_params.get("error", [None])[0]

            return code, state, error

        except Exception:
            return None, None, "URLの解析に失敗しました"
