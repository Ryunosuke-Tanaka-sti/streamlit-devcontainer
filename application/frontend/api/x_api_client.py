"""
X API v2 投稿クライアント

X API v2 を使用してツイートの投稿とレート制限管理を行います。
"""

import json
import logging
from typing import Dict, Any, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


class XAPIError(Exception):
    """X API エラーの基底クラス"""

    pass


class RateLimitError(XAPIError):
    """レート制限エラー"""

    def __init__(self, message: str, reset_time: Optional[int] = None):
        super().__init__(message)
        self.reset_time = reset_time


class AuthenticationError(XAPIError):
    """認証エラー"""

    pass


class BadRequestError(XAPIError):
    """リクエストエラー"""

    pass


class ServerError(XAPIError):
    """サーバーエラー"""

    pass


class NetworkError(XAPIError):
    """ネットワークエラー"""

    pass


class XAPIClient:
    """X API v2 投稿クライアント"""

    def __init__(self, access_token: str):
        """
        Args:
            access_token: OAuth 2.0 アクセストークン
        """
        if not access_token:
            raise ValueError("アクセストークンが必要です")

        self.access_token = access_token
        self.base_url = "https://api.twitter.com/2"
        self.session = requests.Session()

        # 共通ヘッダーを設定
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "X-Scheduler-Pro/1.0",
            }
        )

    def post_tweet(
        self, text: str, reply_settings: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ツイートを投稿

        Args:
            text: ツイート内容（最大280文字）
            reply_settings: 返信設定 ("everyone", "mentionedUsers", "following")

        Returns:
            投稿結果の辞書

        Raises:
            BadRequestError: リクエスト形式エラー
            AuthenticationError: 認証エラー
            RateLimitError: レート制限エラー
            ServerError: サーバーエラー
            NetworkError: ネットワークエラー
        """
        if not text or not text.strip():
            raise BadRequestError("ツイート内容が空です")

        if len(text) > 280:
            raise BadRequestError(f"ツイート内容が長すぎます（{len(text)}/280文字）")

        # リクエストボディを作成
        data = {"text": text.strip()}

        if reply_settings:
            data["reply_settings"] = reply_settings

        try:
            logger.info(f"ツイート投稿開始: {text[:50]}...")

            response = self.session.post(
                f"{self.base_url}/tweets", json=data, timeout=30
            )

            return self._handle_response(response, "ツイート投稿")

        except Timeout:
            raise NetworkError("リクエストがタイムアウトしました")
        except ConnectionError:
            raise NetworkError("ネットワーク接続エラーが発生しました")
        except RequestException as e:
            raise NetworkError(f"ネットワークエラー: {str(e)}")

    def _handle_response(
        self, response: requests.Response, operation: str
    ) -> Dict[str, Any]:
        """
        APIレスポンスを処理

        Args:
            response: requests.Response オブジェクト
            operation: 操作名（ログ用）

        Returns:
            レスポンスデータ

        Raises:
            BadRequestError: 400エラー
            AuthenticationError: 401エラー
            RateLimitError: 429エラー
            ServerError: 500エラー
            XAPIError: その他のエラー
        """
        # ステータスコードによる処理分岐
        if response.status_code == 200 or response.status_code == 201:
            # 成功
            try:
                data = response.json()
                logger.info(f"{operation}成功")
                return data
            except json.JSONDecodeError:
                logger.error(f"JSONデコードエラー: {response.text}")
                raise XAPIError("APIレスポンスの解析に失敗しました")

        elif response.status_code == 400:
            # Bad Request
            error_info = self._extract_error_info(response)
            logger.error(f"{operation}失敗 - Bad Request: {error_info}")
            raise BadRequestError(error_info)

        elif response.status_code == 401:
            # Unauthorized
            error_info = self._extract_error_info(response)
            logger.error(f"{operation}失敗 - Unauthorized: {error_info}")
            raise AuthenticationError(error_info)

        elif response.status_code == 403:
            # Forbidden
            error_info = self._extract_error_info(response)
            logger.error(f"{operation}失敗 - Forbidden: {error_info}")
            raise AuthenticationError(f"アクセス権限がありません: {error_info}")

        elif response.status_code == 404:
            # Not Found
            error_info = self._extract_error_info(response)
            logger.error(f"{operation}失敗 - Not Found: {error_info}")
            raise BadRequestError(f"リソースが見つかりません: {error_info}")

        elif response.status_code == 429:
            # Too Many Requests
            error_info = self._extract_error_info(response)
            logger.error(f"{operation}失敗 - Rate Limited: {error_info}")
            raise RateLimitError(error_info, None)

        elif 500 <= response.status_code < 600:
            # Server Error
            error_info = self._extract_error_info(response)
            logger.error(f"{operation}失敗 - Server Error: {error_info}")
            raise ServerError(error_info)

        else:
            # その他のエラー
            error_info = self._extract_error_info(response)
            logger.error(f"{operation}失敗 - Unknown Error: {error_info}")
            raise XAPIError(f"予期しないエラー: {error_info}")

    def _extract_error_info(self, response: requests.Response) -> str:
        """
        エラーレスポンスから詳細情報を抽出

        Args:
            response: requests.Response オブジェクト

        Returns:
            エラー情報文字列
        """
        try:
            error_data = response.json()

            # X API v2 形式のエラー
            if "errors" in error_data:
                errors = error_data["errors"]
                if isinstance(errors, list) and len(errors) > 0:
                    first_error = errors[0]
                    message = first_error.get("message", "不明なエラー")
                    detail = first_error.get("detail", "")
                    return f"{message}" + (f": {detail}" if detail else "")

            # その他の形式
            if "detail" in error_data:
                return error_data["detail"]

            if "message" in error_data:
                return error_data["message"]

            if "error" in error_data:
                return error_data["error"]

            return f"HTTP {response.status_code}: {response.reason}"

        except (json.JSONDecodeError, TypeError):
            return f"HTTP {response.status_code}: {response.reason}"

    def close(self):
        """セッションをクローズ"""
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self):
        """コンテキストマネージャーの開始"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了"""
        self.close()
