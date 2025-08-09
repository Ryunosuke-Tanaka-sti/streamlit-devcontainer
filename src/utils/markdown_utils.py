"""
Markdown処理ユーティリティ

Markdownファイルの解析、HTML変換、メタデータ抽出などの機能を提供します。
"""

import re
import markdown
from typing import Dict, Tuple
import streamlit as st


class MarkdownProcessor:
    """Markdown処理クラス"""

    def __init__(self):
        # Markdown Extensions
        self.md = markdown.Markdown(
            extensions=[
                "extra",  # 拡張構文サポート
                "codehilite",  # シンタックスハイライト
                "toc",  # 目次生成
            ],
            extension_configs={"codehilite": {"css_class": "highlight"}},
        )

    def convert_to_html(self, markdown_text: str) -> str:
        """
        MarkdownをHTMLに変換

        Args:
            markdown_text: Markdownテキスト

        Returns:
            HTML文字列
        """
        try:
            # リセット（前の変換結果をクリア）
            self.md.reset()
            return self.md.convert(markdown_text)
        except Exception as e:
            return f'<p style="color: red;">Markdown変換エラー: {str(e)}</p>'

    def extract_metadata(self, markdown_text: str) -> Dict[str, any]:
        """
        Markdownファイルからメタデータを抽出

        Args:
            markdown_text: Markdownテキスト

        Returns:
            メタデータ辞書
        """
        metadata = {
            "title": "",
            "hashtags": [],
            "char_count": len(markdown_text),
            "word_count": len(markdown_text.split()),
            "line_count": markdown_text.count("\n") + 1,
            "twitter_length": self.calculate_twitter_length(markdown_text),
        }

        # タイトル抽出（最初のH1見出し）
        title_match = re.search(r"^#\s+(.+)", markdown_text, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # ハッシュタグ抽出
        hashtags = re.findall(r"#(\w+)", markdown_text)
        metadata["hashtags"] = list(set(hashtags))  # 重複を除去

        return metadata

    def calculate_twitter_length(self, text: str) -> int:
        """
        Twitter投稿時の文字数を計算

        Args:
            text: テキスト

        Returns:
            Twitter文字数
        """
        # Markdownの構文記号を除去して実際の表示文字数を計算
        clean_text = self.strip_markdown_syntax(text)
        return len(clean_text)

    def strip_markdown_syntax(self, markdown_text: str) -> str:
        """
        Markdown構文記号を除去

        Args:
            markdown_text: Markdownテキスト

        Returns:
            プレーンテキスト
        """
        # 基本的なMarkdown構文を除去
        text = markdown_text

        # 見出し記号
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

        # 太字・イタリック
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"\*(.*?)\*", r"\1", text)
        text = re.sub(r"__(.*?)__", r"\1", text)
        text = re.sub(r"_(.*?)_", r"\1", text)

        # リンク
        text = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", text)

        # コードブロック・インライン
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`([^`]*)`", r"\1", text)

        # リスト記号
        text = re.sub(r"^\s*[-*+]\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)

        # 引用
        text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)

        # 水平線
        text = re.sub(r"^(-{3,}|\*{3,})$", "", text, flags=re.MULTILINE)

        # 余分な空行を除去
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def validate_for_twitter(
        self, markdown_text: str
    ) -> Tuple[bool, str, Dict[str, any]]:
        """
        Twitter投稿用のバリデーション

        Args:
            markdown_text: Markdownテキスト

        Returns:
            (バリデーション結果, エラーメッセージ, 詳細情報)
        """
        twitter_text = self.strip_markdown_syntax(markdown_text)
        char_count = len(twitter_text)

        validation_info = {
            "char_count": char_count,
            "char_limit": 280,
            "chars_remaining": 280 - char_count,
            "twitter_text": twitter_text,
            "is_valid": char_count <= 280,
        }

        if char_count == 0:
            return False, "投稿内容が空です。", validation_info
        elif char_count > 280:
            return (
                False,
                f"文字数が上限を超えています（{char_count}/280文字）",
                validation_info,
            )
        else:
            return True, "投稿可能です。", validation_info


def get_markdown_processor() -> MarkdownProcessor:
    """
    MarkdownProcessorのシングルトンインスタンスを取得

    Returns:
        MarkdownProcessorインスタンス
    """
    if "markdown_processor" not in st.session_state:
        st.session_state.markdown_processor = MarkdownProcessor()
    return st.session_state.markdown_processor
