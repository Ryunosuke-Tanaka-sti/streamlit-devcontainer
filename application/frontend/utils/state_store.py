"""
Stateとcode_verifierのマッピングを管理するストア

OAuthのstateパラメータとPKCEのcode_verifierをマッピングして
セッション間で共有できるようにします。
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import threading


class StateStore:
    """StateとCode Verifierのマッピングを管理"""

    # クラス変数として全インスタンスで共有
    _store: Dict[str, Tuple[str, datetime]] = {}
    _lock = threading.Lock()

    # タイムアウト時間（分）
    TIMEOUT_MINUTES = 15

    @classmethod
    def save(cls, state: str, code_verifier: str) -> None:
        """
        StateとCode Verifierのペアを保存

        Args:
            state: OAuth state
            code_verifier: PKCE code verifier
        """
        with cls._lock:
            # 期限切れのエントリをクリーンアップ
            cls._cleanup_expired()

            # 新しいエントリを保存
            expires_at = datetime.now() + timedelta(minutes=cls.TIMEOUT_MINUTES)
            cls._store[state] = (code_verifier, expires_at)

    @classmethod
    def get(cls, state: str) -> Optional[str]:
        """
        Stateに対応するCode Verifierを取得

        Args:
            state: OAuth state

        Returns:
            対応するcode_verifier（見つからない場合はNone）
        """
        with cls._lock:
            if state in cls._store:
                code_verifier, expires_at = cls._store[state]

                # 期限チェック
                if datetime.now() < expires_at:
                    return code_verifier
                else:
                    # 期限切れの場合は削除
                    del cls._store[state]
                    return None
            else:
                return None

    @classmethod
    def remove(cls, state: str) -> None:
        """
        使用済みのStateを削除

        Args:
            state: OAuth state
        """
        with cls._lock:
            if state in cls._store:
                del cls._store[state]

    @classmethod
    def _cleanup_expired(cls) -> None:
        """期限切れのエントリをクリーンアップ"""
        now = datetime.now()
        expired_states = [
            state for state, (_, expires_at) in cls._store.items() if now >= expires_at
        ]

        for state in expired_states:
            del cls._store[state]

    @classmethod
    def clear_all(cls) -> None:
        """全てのエントリをクリア（デバッグ用）"""
        with cls._lock:
            cls._store.clear()
