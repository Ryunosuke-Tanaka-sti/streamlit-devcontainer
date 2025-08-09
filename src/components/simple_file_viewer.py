"""
シンプルファイル参照コンポーネント

サイドバーでMarkdownファイルの参照・選択のみを行い、
メインエリアでプレビューを表示するシンプルなコンポーネント
編集・削除・作成機能は含まない
"""

import streamlit as st
import os
from typing import Optional


from utils.file_utils import get_file_manager
from utils.markdown_utils import get_markdown_processor


def show_simple_file_viewer() -> Optional[str]:
    """
    サイドバーでシンプルなファイル参照機能を表示

    Returns:
        選択されたファイルのパス（選択されていない場合はNone）
    """
    st.sidebar.header("📁 Markdownファイル参照")

    # ファイル一覧の表示
    selected_file = show_file_list_sidebar()

    return selected_file


def show_file_list_sidebar() -> Optional[str]:
    """サイドバーでファイル一覧表示"""
    file_manager = get_file_manager()

    # ソート・検索機能
    sort_by = st.sidebar.selectbox(
        "📊 ソート順",
        ["name", "modified"],
        format_func=lambda x: "ファイル名" if x == "name" else "更新日時",
        key="simple_sort",
    )

    search_term = st.sidebar.text_input(
        "🔍 ファイル検索", placeholder="ファイル名を入力...", key="simple_search"
    )

    # ファイル一覧取得
    try:
        file_list = file_manager.get_file_list(sort_by)
    except Exception as e:
        st.sidebar.error(f"ファイル一覧の取得に失敗: {str(e)}")
        return None

    # 検索フィルタリング
    if search_term:
        file_list = [f for f in file_list if search_term.lower() in f["name"].lower()]

    if not file_list:
        st.sidebar.info("📝 Markdownファイルが見つかりません")
        return None

    # ファイル選択UI
    st.sidebar.write(f"**ファイル一覧 ({len(file_list)}件)**")

    selected_file = st.session_state.get("selected_file")

    for file_info in file_list:
        is_selected = selected_file == file_info["path"]
        filename = file_info["name"]

        # ファイル選択ボタン
        if st.sidebar.button(
            f"{'📄' if is_selected else '📝'} {filename}",
            key=f"simple_file_{file_info['path']}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state.selected_file = file_info["path"]
            st.rerun()

    return selected_file


def show_main_content_area():
    """メインエリアでのコンテンツ表示"""
    selected_file = st.session_state.get("selected_file")

    if not selected_file:
        st.info(
            "👈 左のサイドバーからMarkdownファイルを選択してください。\n\n"
            "**機能:**\n"
            "- 📊 ファイルのソート・検索\n"
            "- 📋 Markdownプレビュー表示\n"
            "- 📤 X投稿作成フォーム"
        )
        return

    file_manager = get_file_manager()
    markdown_processor = get_markdown_processor()

    filename = os.path.basename(selected_file)

    # ファイル読み込み
    success, content = file_manager.load_file_content(selected_file)

    if not success:
        st.error(f"ファイル読み込みエラー: {content}")
        return

    # CSS for sticky right pane
    st.markdown(
        """
        <style>
        .stColumn:nth-child(2) > div {
            position: sticky;
            top: 20px;
            max-height: calc(100vh - 40px);
            overflow-y: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 2カラムレイアウト
    col1, col2 = st.columns([1, 1])

    with col1:
        # プレビューエリア
        show_content_preview(content, filename, markdown_processor)

    with col2:
        # 投稿エリア（sticky対応）
        show_post_interface(content, filename)


def show_content_preview(content: str, filename: str, markdown_processor):
    """コンテンツのプレビュー表示"""
    # ヘッダー
    st.header(f"📋 {filename}")

    # シンプルなHTMLプレビューのみ
    html_content = markdown_processor.convert_to_html(content)
    st.markdown(html_content, unsafe_allow_html=True)


def show_post_interface(content: str, filename: str):
    """投稿インターフェースの表示"""
    from datetime import datetime, timedelta

    st.header("📤 投稿作成")

    # 投稿用のテキストボックス（session_stateでテキストを管理）
    text_key = f"post_text_{filename}"
    
    # フォームクリア用のフラグをチェック
    clear_form_key = f"clear_form_{filename}"
    should_clear = st.session_state.get(clear_form_key, False)

    if should_clear:
        # フラグをリセットしてテキストをクリア
        st.session_state[clear_form_key] = False
        st.session_state[text_key] = ""

    # テキストエリアの初期値を設定
    if text_key not in st.session_state:
        st.session_state[text_key] = ""

    post_text = st.text_area(
        "投稿テキスト",
        value=st.session_state[text_key],
        height=200,
        help="編集可能です。文字数制限: 280文字",
        placeholder="ここに投稿内容を入力してください...",
        key=text_key
    )

    # 文字数表示
    char_count = len(post_text)
    if char_count > 280:
        st.error(f"⚠️ 文字数制限超過: {char_count}/280文字")
    else:
        st.success(f"✅ 文字数OK: {char_count}/280文字")

    st.markdown("---")

    # 投稿タイプ選択
    post_type = st.radio("投稿タイプ", ["即時投稿", "予約投稿"], horizontal=True)

    if post_type == "予約投稿":
        st.subheader("📅 予約設定")

        # 日付指定
        scheduled_date = st.date_input(
            "投稿日",
            value=datetime.now().date() + timedelta(days=1),
            min_value=datetime.now().date(),
        )

        # 投稿時刻選択（ボタン形式）
        st.write("⏰ **投稿時刻を選択**")

        # セッション状態から選択された時刻を取得
        selected_time = st.session_state.get("selected_post_time", None)

        time_options = [
            {"time": "09:00", "label": "🕘 9時", "emoji": "🌅"},
            {"time": "12:00", "label": "🕐 12時", "emoji": "☀️"},
            {"time": "15:00", "label": "🕒 15時", "emoji": "🌤️"},
            {"time": "21:00", "label": "🕘 21時", "emoji": "🌙"},
        ]

        # 2列でボタンを配置
        col1, col2 = st.columns(2)

        for i, time_option in enumerate(time_options):
            col = col1 if i % 2 == 0 else col2

            with col:
                is_selected = selected_time == time_option["time"]
                button_label = f"{time_option['emoji']} {time_option['time'][:2]}時"

                if st.button(
                    button_label,
                    key=f"time_btn_{time_option['time']}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.selected_post_time = time_option["time"]
                    st.rerun()

    st.markdown("---")

    # 投稿ボタン
    button_text = "📤 投稿する" if post_type == "即時投稿" else "⏰ 予約投稿する"
    button_disabled = (
        char_count > 280
        or char_count == 0
        or (post_type == "予約投稿" and not selected_time)
    )

    if st.button(button_text, type="primary", disabled=button_disabled):
        success = execute_post_action(
            post_type,
            post_text,
            filename,
            scheduled_date if post_type == "予約投稿" else None,
            selected_time if post_type == "予約投稿" else None,
        )

        # 投稿成功時にフォームをクリア（即時投稿・予約投稿両方）
        if success:
            # テキストボックスと時刻選択をクリア
            if "selected_post_time" in st.session_state:
                del st.session_state.selected_post_time
            # フォームクリアフラグを設定
            clear_form_key = f"clear_form_{filename}"
            st.session_state[clear_form_key] = True
            st.rerun()


def execute_post_action(
    post_type: str, text: str, filename: str, scheduled_date=None, selected_time=None
):
    """投稿アクションの実行（モック接続）"""
    import time
    import random

    # 認証チェック（モック環境でも認証状態は確認）
    if not st.session_state.get("authenticated", False):
        st.error("❌ 認証が必要です")
        return False

    if not st.session_state.get("access_token"):
        st.error("❌ アクセストークンが無効です")
        return False

    with st.spinner("投稿処理中...（モック接続）"):
        time.sleep(1)

        # === モック投稿処理 ===
        # 実際のX API接続は行わず、モック処理でデモンストレーション
        # 本番環境では以下のような実装になる:
        # oauth_client = XOAuthClient()
        # success = oauth_client.create_tweet(text, st.session_state.access_token)
        
        # 投稿内容のバリデーション（実際の実装と同様）
        if not text or len(text.strip()) == 0:
            st.error("❌ 投稿内容が空です")
            return False
        
        if len(text) > 280:
            st.error(f"❌ 文字数制限超過: {len(text)}/280文字")
            return False

        # モック成功率: 50%
        success = random.random() < 0.5

        if success:
            # 投稿成功時はフォームクリアのみ（軽量化のため視覚効果は削除）
            return True
        else:
            # モックエラーメッセージ
            error_messages = [
                "モック: ネットワークエラーが発生しました",
                "モック: API制限に達しました",
                "モック: 認証エラーが発生しました",
            ]
            st.error(f"❌ 投稿に失敗しました: {random.choice(error_messages)}")

            if st.button("🔄 再試行"):
                st.rerun()

            return False
