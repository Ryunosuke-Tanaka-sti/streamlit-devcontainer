"""
PKCE (Proof Key for Code Exchange) ユーティリティ

OAuth 2.0 のPKCE 拡張を実装し、コードインターセプト攻撃から保護します。
"""

import secrets
import hashlib
import base64
from typing import Tuple


class PKCEUtils:
    """
    PKCE (Proof Key for Code Exchange) ユーティリティクラス
    """

    @staticmethod
    def generate_code_verifier(length: int = 128) -> str:
        """
        code_verifier を生成

        Args:
            length: 文字列の長さ（43-128文字）

        Returns:
            ランダムな code_verifier 文字列
        """
        if not 43 <= length <= 128:
            raise ValueError("code_verifierの長さは43-128文字である必要があります")

        # URLセーフな文字を使用
        allowed_chars = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        )
        return "".join(secrets.choice(allowed_chars) for _ in range(length))

    @staticmethod
    def generate_code_challenge(code_verifier: str, method: str = "S256") -> str:
        """
        code_challenge を生成

        Args:
            code_verifier: 生成された code_verifier
            method: ハッシュメソッド（S256 または plain）

        Returns:
            code_challenge 文字列
        """
        if method == "S256":
            # SHA256 ハッシュを計算
            digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            # Base64URL エンコード
            challenge = base64.urlsafe_b64encode(digest).decode("utf-8")
            # パディングを除去
            return challenge.rstrip("=")
        elif method == "plain":
            return code_verifier
        else:
            raise ValueError(f"サポートされていない method: {method}")

    @staticmethod
    def generate_state(length: int = 32) -> str:
        """
        CSRF 攻撃防止用の state パラメータを生成

        Args:
            length: state の長さ

        Returns:
            ランダムな state 文字列
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_pkce_pair(verifier_length: int = 128) -> Tuple[str, str, str]:
        """
        PKCE ペアと state を一度に生成

        Args:
            verifier_length: code_verifier の長さ

        Returns:
            (code_verifier, code_challenge, state) のタプル
        """
        code_verifier = PKCEUtils.generate_code_verifier(verifier_length)
        code_challenge = PKCEUtils.generate_code_challenge(code_verifier, "S256")
        state = PKCEUtils.generate_state()

        return code_verifier, code_challenge, state

    @staticmethod
    def verify_state(expected_state: str, received_state: str) -> bool:
        """
        state パラメータを検証

        Args:
            expected_state: 送信時に生成した state
            received_state: コールバックで受け取った state

        Returns:
            一致するかどうか
        """
        if not expected_state or not received_state:
            return False

        # タイミング攻撃を防ぐための定数時間比較
        return secrets.compare_digest(expected_state, received_state)
