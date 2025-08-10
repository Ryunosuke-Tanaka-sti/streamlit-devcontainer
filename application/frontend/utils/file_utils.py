"""
ファイル操作ユーティリティ

Markdownファイルの読み込み、保存、削除などの基本的な操作を提供します。
"""

import os
import glob
from datetime import datetime
from typing import List, Dict, Tuple
import streamlit as st


class FileManager:
    """Markdownファイル管理クラス"""

    def __init__(self, base_dir: str = "markdown"):
        self.base_dir = base_dir
        self.ensure_directory_exists()

    def ensure_directory_exists(self) -> None:
        """ベースディレクトリが存在することを確認"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_file_list(self, sort_by: str = "name") -> List[Dict[str, str]]:
        """
        Markdownファイル一覧を取得

        Args:
            sort_by: ソート方法 ("name", "modified")

        Returns:
            ファイル情報のリスト
        """
        pattern = os.path.join(self.base_dir, "*.md")
        files = glob.glob(pattern)

        file_info_list = []
        for file_path in files:
            try:
                stat = os.stat(file_path)
                file_info = {
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "size": stat.st_size,
                }
                file_info_list.append(file_info)
            except OSError:
                continue

        # ソート
        if sort_by == "modified":
            file_info_list.sort(key=lambda x: x["modified"], reverse=True)
        else:
            file_info_list.sort(key=lambda x: x["name"].lower())

        return file_info_list

    def load_file_content(self, file_path: str) -> Tuple[bool, str]:
        """
        ファイルの内容を読み込み

        Args:
            file_path: ファイルパス

        Returns:
            (成功フラグ, ファイル内容)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return True, content
        except FileNotFoundError:
            return False, "ファイルが見つかりません。"
        except PermissionError:
            return False, "ファイルの読み込み権限がありません。"
        except UnicodeDecodeError:
            return False, "ファイルの文字エンコーディングが無効です。"
        except Exception as e:
            return False, f"ファイル読み込みエラー: {str(e)}"

    def get_file_stats(self, file_path: str) -> Dict[str, any]:
        """
        ファイルの統計情報を取得

        Args:
            file_path: ファイルパス

        Returns:
            ファイル統計情報
        """
        try:
            success, content = self.load_file_content(file_path)
            if not success:
                return {"error": content}

            # 文字数カウント
            char_count = len(content)
            line_count = content.count("\n") + 1 if content else 0
            word_count = len(content.split()) if content else 0

            # ファイル情報
            stat = os.stat(file_path)

            return {
                "char_count": char_count,
                "line_count": line_count,
                "word_count": word_count,
                "file_size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "twitter_chars_remaining": max(0, 280 - char_count),
            }
        except Exception as e:
            return {"error": f"統計情報の取得に失敗: {str(e)}"}


def get_file_manager() -> FileManager:
    """
    FileManagerのシングルトンインスタンスを取得

    Returns:
        FileManagerインスタンス
    """
    if "file_manager" not in st.session_state:
        st.session_state.file_manager = FileManager()
    return st.session_state.file_manager
