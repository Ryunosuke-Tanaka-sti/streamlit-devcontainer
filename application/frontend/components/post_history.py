"""
投稿履歴表示コンポーネント

Firestoreから投稿履歴を取得して表示する機能
"""

from datetime import datetime
from typing import Dict, Any

import streamlit as st


def show_post_history():
    """投稿履歴を表示"""
    firebase_client = get_firebase_client()

    tab1, tab2, tab3 = st.tabs(["📝 最近の投稿", "📅 今日の投稿", "🔍 検索"])

    with tab1:
        show_recent_posts(firebase_client)

    with tab2:
        show_today_posts(firebase_client)

    with tab3:
        show_post_search(firebase_client)


def get_firebase_client():
    """ファイアベースクライアントを取得"""
    try:
        from db.firebase_client import get_firebase_client
    except ImportError:
        import sys
        import os

        sys.path.append(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        from db.firebase_client import get_firebase_client
    return get_firebase_client()


def get_config():
    """設定クラスを取得"""
    try:
        from utils.config import Config
    except ImportError:
        import sys
        import os

        sys.path.append(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        from utils.config import Config
    return Config


def show_recent_posts(firebase_client):
    """最近の投稿を表示"""
    st.subheader("📝 最近の投稿（10件）")

    # タブコンテキストを設定
    st.session_state.current_tab_context = "recent"

    col1, col2 = st.columns([1, 1])
    with col1:
        show_posted_only = st.checkbox("投稿済みのみ", value=True)
    with col2:
        if st.button("🔄 更新", key="refresh_recent"):
            st.rerun()

    recent_posts = firebase_client.get_recent_posts(10, show_posted_only)

    if not recent_posts:
        st.info("投稿履歴がありません")
        return

    for post in recent_posts:
        display_post_card(post)


def show_today_posts(firebase_client):
    """今日の投稿を表示"""
    st.subheader("📅 今日の投稿")

    # タブコンテキストを設定
    st.session_state.current_tab_context = "today"

    today = datetime.now().strftime("%Y/%m/%d")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.write(f"**日付: {today}**")

    with col2:
        if st.button("🔄 更新", key="refresh_today"):
            st.rerun()

    # 今日の投稿を取得
    all_posts = firebase_client.get_posts_by_date(today)
    posted_posts = firebase_client.get_posts_by_date(today, is_posted=True)
    pending_posts = firebase_client.get_posts_by_date(today, is_posted=False)

    # 統計情報
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 合計投稿", len(all_posts))
    with col2:
        st.metric("✅ 投稿済み", len(posted_posts))
    with col3:
        st.metric("⏳ 予約中", len(pending_posts))

    # 投稿一覧
    if all_posts:
        for post in all_posts:
            display_post_card(post)
    else:
        st.info("今日の投稿はありません")


def show_post_search(firebase_client):
    """投稿検索機能"""
    st.subheader("🔍 投稿検索")

    # タブコンテキストを設定
    st.session_state.current_tab_context = "search"

    col1, col2 = st.columns(2)
    with col1:
        search_date = st.date_input(
            "検索日付", value=datetime.now().date(), max_value=datetime.now().date()
        )

    with col2:
        status_filter = st.selectbox("投稿状態", ["すべて", "投稿済み", "未投稿"])

    if st.button("🔍 検索"):
        date_str = search_date.strftime("%Y/%m/%d")

        if status_filter == "すべて":
            posts = firebase_client.get_posts_by_date(date_str)
        elif status_filter == "投稿済み":
            posts = firebase_client.get_posts_by_date(date_str, is_posted=True)
        else:  # 未投稿
            posts = firebase_client.get_posts_by_date(date_str, is_posted=False)

        if posts:
            st.success(f"📊 {len(posts)}件の投稿が見つかりました")
            for post in posts:
                display_post_card(post)
        else:
            st.info("該当する投稿がありません")


def display_post_card(post: Dict[str, Any]):
    """投稿カードを表示"""
    Config = get_config()

    # ステータスに応じたスタイル
    if post.get("isPosted"):
        status_emoji = "✅"
    else:
        status_emoji = "⏳"

    # ヘッダー行
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.write(f"**{status_emoji} {post.get('postDate', '不明')}**")

    with col2:
        if post.get("timeSlot") is not None:
            time_label = Config.get_time_slot_label(post["timeSlot"])
            st.write(f"⏰ {time_label}")
        else:
            st.write("📱 即時投稿")

    with col3:
        # 削除ボタン（タブごとに一意のキーを生成）
        tab_context = st.session_state.get("current_tab_context", "main")
        delete_key = f"delete_{tab_context}_{post['id']}"

        # 削除確認状態を管理
        confirm_key = f"confirm_delete_{tab_context}_{post['id']}"

        # 削除確認が求められているかチェック
        if st.session_state.get(confirm_key, False):
            # 確認ダイアログを表示
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ はい", key=f"yes_{confirm_key}"):
                    # 削除実行
                    if execute_delete(post["id"]):
                        st.success("投稿を削除しました")
                    else:
                        st.error("削除に失敗しました")
                    st.session_state[confirm_key] = False
                    st.rerun()
            with col_no:
                if st.button("❌ いいえ", key=f"no_{confirm_key}"):
                    st.session_state[confirm_key] = False
                    st.rerun()
        else:
            # 通常の削除ボタン
            if st.button("🗑️", key=delete_key, help="投稿を削除"):
                st.session_state[confirm_key] = True
                st.rerun()

    # 投稿内容（改行保持）
    content = post.get("content", "")
    if len(content) > 200:
        content = content[:200] + "..."

    # 改行を保持して表示
    st.markdown("**📝 投稿内容:**")
    st.text(content)

    # 詳細情報
    if post.get("isPosted"):
        if post.get("xPostId"):
            st.write(f"🔗 ツイートID: `{post['xPostId']}`")
        if post.get("postedAt"):
            # Firestoreのタイムスタンプを処理
            posted_time = post["postedAt"]
            if hasattr(posted_time, "seconds"):
                posted_time = datetime.fromtimestamp(posted_time.seconds)
            st.write(f"📅 投稿時刻: {posted_time}")
    else:
        if post.get("errorMessage"):
            st.error(f"❌ エラー: {post['errorMessage']}")

    # 作成時刻
    if post.get("createdAt"):
        created_time = post["createdAt"]
        if hasattr(created_time, "seconds"):
            created_time = datetime.fromtimestamp(created_time.seconds)
        st.caption(f"作成日時: {created_time}")

    st.divider()


def execute_delete(post_id: str) -> bool:
    """投稿削除を実行"""
    firebase_client = get_firebase_client()
    return firebase_client.delete_post(post_id)
