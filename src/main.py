"""
X Scheduler Pro - Streamlit メインアプリケーション

X API OAuth 2.0 認証を使用したMarkdown投稿管理システム
"""

import streamlit as st
from datetime import datetime, timedelta

# 内部モジュール
try:
    from src.auth.oauth_client import (
        XOAuthClient,
        AuthenticationError,
        TokenExpiredError,
    )
    from src.utils.config import Config
    from src.utils.state_store import StateStore
    from src.components.simple_file_viewer import (
        show_simple_file_viewer,
        show_main_content_area
    )
except ImportError:
    # 直接実行時のパス対応
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.auth.oauth_client import (
        XOAuthClient,
        AuthenticationError,
        TokenExpiredError,
    )
    from src.utils.config import Config
    from src.utils.state_store import StateStore
    from src.components.simple_file_viewer import (
        show_simple_file_viewer,
        show_main_content_area
    )


def initialize_session_state():
    """セッション状態を初期化"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None

    if "user_info" not in st.session_state:
        st.session_state.user_info = None

    if "token_data" not in st.session_state:
        st.session_state.token_data = None

    # OAuth フロー用の一時的な状態
    if "oauth_state" not in st.session_state:
        st.session_state.oauth_state = None

    if "code_verifier" not in st.session_state:
        st.session_state.code_verifier = None

    if "auth_start_time" not in st.session_state:
        st.session_state.auth_start_time = None


def check_session_timeout():
    """セッションタイムアウトをチェック"""
    if st.session_state.authenticated and st.session_state.auth_start_time:
        start_time = st.session_state.auth_start_time
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        if datetime.now() - start_time > timedelta(
            minutes=Config.SESSION_TIMEOUT_MINUTES
        ):
            logout()
            st.warning(
                f"セッションがタイムアウトしました（{Config.SESSION_TIMEOUT_MINUTES}分）"
            )
            st.rerun()


def logout():
    """ログアウト処理"""
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_info = None
    st.session_state.token_data = None
    st.session_state.oauth_state = None
    st.session_state.code_verifier = None
    st.session_state.auth_start_time = None


def handle_oauth_callback():
    """OAuth コールバックを処理"""
    # URLパラメータから認証コードを取得
    query_params = st.query_params

    if "code" in query_params:
        authorization_code = query_params["code"]
        received_state = query_params.get("state")
        error = query_params.get("error")

        if error:
            st.error(f"認証エラー: {error}")
            return False

        if not st.session_state.oauth_state or not st.session_state.code_verifier:
            # StateStoreから復元を試行
            if received_state:
                code_verifier = StateStore.get(received_state)
                if code_verifier:
                    st.session_state.oauth_state = received_state
                    st.session_state.code_verifier = code_verifier
                else:
                    st.error(
                        "認証セッションが見つかりません。再度ログインしてください。"
                    )
                    if st.button("🔄 再度ログインする"):
                        st.rerun()
                    return False
            else:
                st.error("認証情報が不足しています。再度ログインしてください。")
                if st.button("🔄 再度ログインする"):
                    st.rerun()
                return False

        try:
            oauth_client = XOAuthClient()

            # トークンを取得
            token_data = oauth_client.exchange_code_for_token(
                authorization_code=authorization_code,
                code_verifier=st.session_state.code_verifier,
                state=st.session_state.oauth_state,
                received_state=received_state,
            )

            # ユーザー情報を取得
            user_info = oauth_client.get_user_info(token_data["access_token"])

            # セッション状態を更新
            st.session_state.authenticated = True
            st.session_state.access_token = token_data["access_token"]
            st.session_state.refresh_token = token_data.get("refresh_token")
            st.session_state.user_info = user_info
            st.session_state.token_data = token_data
            st.session_state.auth_start_time = datetime.now().isoformat()

            # OAuth一時状態をクリア
            st.session_state.oauth_state = None
            st.session_state.code_verifier = None

            # StateStoreからも削除（セキュリティのため）
            if received_state:
                StateStore.remove(received_state)

            # URLパラメータをクリア
            st.query_params.clear()

            st.success(f"✅ ログインに成功しました: @{user_info['data']['username']}")
            st.balloons()  # 成功の視覚的フィードバック
            st.rerun()

        except (AuthenticationError, TokenExpiredError) as e:
            st.error(f"認証に失敗しました: {str(e)}")
            return False
        except Exception as e:
            st.error(f"予期しないエラーが発生しました: {str(e)}")
            return False

    return True


def show_login_page():
    """ログインページを表示"""
    st.title("🐦 X Scheduler Pro")
    st.markdown("---")

    st.header("🔐 Xアカウントでログインしてください")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("📱 Xでログイン", type="primary", use_container_width=True):
            try:
                oauth_client = XOAuthClient()

                # 認証URLを生成
                auth_url, code_verifier, code_challenge, state = (
                    oauth_client.generate_authorization_url()
                )

                # セッション状態に保存
                st.session_state.oauth_state = state
                st.session_state.code_verifier = code_verifier

                # StateStoreに保存
                StateStore.save(state, code_verifier)

                # X認証画面にリダイレクト
                st.success("🚀 X認証画面に移動します...")
                st.info("認証完了後、自動的にこのアプリに戻ります。")

                # 直接リンク
                st.markdown(f"[📱 Xでログイン]({auth_url})")

                # 自動リダイレクト
                st.components.v1.html(
                    f'<script>window.location.href="{auth_url}"</script>', height=0
                )

            except Exception as e:
                st.error(f"認証URLの生成に失敗しました: {str(e)}")

    st.markdown("---")

    # 注意事項
    with st.expander("📋 利用に関する注意事項"):
        st.markdown(
            """
        **必要な権限:**
        - 投稿権限（tweet.write）
        - ユーザー情報読み取り（users.read）
        **セキュリティ:**
        - OAuth 2.0 + PKCE による安全な認証
        - セッションタイムアウト: 30分
        - アクセストークンは暗号化されて保存されます
        **制限事項:**
        - X API 無料プラン: 17投稿/24時間、500投稿/月
        - ローカル環境での開発では ngrok の使用を推奨
        """
        )

    # 開発者情報
    if Config.is_development():
        with st.expander("🔧 開発者向け情報"):
            st.code(
                f"""
                設定情報:
                - Client ID: {Config.X_CLIENT_ID[:10]}...（一部表示）
                - Redirect URI: {Config.X_REDIRECT_URI}
                - Environment: {'Development' if Config.is_development() else 'Production'}
                """
            )


def show_dashboard():
    """認証後のダッシュボードを表示"""

    # ヘッダー
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("🐦 X Scheduler Pro")
        if st.session_state.user_info and "data" in st.session_state.user_info:
            user_data = st.session_state.user_info["data"]
            st.success(f"✅ ログイン中: @{user_data.get('username', 'unknown')}")

    with col2:
        if st.button("🚪 ログアウト", type="secondary"):
            logout()
            st.rerun()

    st.markdown("---")

    # トークン情報表示
    if st.session_state.token_data:
        with st.expander("🔹 トークン情報", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**アクセストークン**: 有効")
                if "expires_at" in st.session_state.token_data:
                    expires_at = st.session_state.token_data["expires_at"]
                    st.write(f"**有効期限**: {expires_at}")

                # トークンの期限チェック
                oauth_client = XOAuthClient()
                if oauth_client.is_token_expired(st.session_state.token_data):
                    st.warning("⚠️ トークンの有効期限が近づいています")

            with col2:
                st.write("**権限**: 投稿, ユーザー情報読み取り")
                if st.session_state.refresh_token:
                    st.write("**リフレッシュトークン**: 利用可能")

    # 機能メニュー
    st.header("📋 機能メニュー")

    tab1, tab2, tab3 = st.tabs(["📝 投稿作成", "📊 統計情報", "⚙️ 設定"])

    with tab1:
        st.subheader("📝 Markdown投稿作成")
        
        # Task2の機能を統合
        # サイドバーでファイル選択
        selected_file = show_simple_file_viewer()
        
        # メインコンテンツエリア（プレビューと投稿フォーム）
        show_main_content_area()
        
        # レート制限情報（認証済みなので実際のAPI情報を表示可能）
        if selected_file:
            st.markdown("---")
            show_rate_limit_info()

    with tab2:
        st.subheader("📊 投稿統計")

        # モック統計データ
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("今日の投稿", "3", "残り14")
        with col2:
            st.metric("今月の投稿", "45", "残り455")
        with col3:
            st.metric("予約中", "5")

        st.info("📊 詳細な統計機能は Task 3 で実装予定です")

    with tab3:
        st.subheader("⚙️ アプリケーション設定")

        # セッション情報
        st.markdown("**セッション情報**")
        if st.session_state.auth_start_time:
            start_time = st.session_state.auth_start_time
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)

            elapsed = datetime.now() - start_time
            remaining = timedelta(minutes=Config.SESSION_TIMEOUT_MINUTES) - elapsed

            st.write(f"セッション開始時刻: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"残り時間: {remaining}")

        # 環境情報
        st.markdown("**環境情報**")
        st.code(
            f"""
環境: {'開発' if Config.is_development() else '本番'}
リダイレクトURI: {Config.X_REDIRECT_URI}
セッションタイムアウト: {Config.SESSION_TIMEOUT_MINUTES}分
        """
        )


def main():
    """メイン関数"""
    # ページ設定
    st.set_page_config(
        page_title="X Scheduler Pro",
        page_icon="🐦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # CSS スタイル
    st.markdown(
        """
    <style>
    .main {
        padding-top: 1rem;
    }
    .stButton > button {
        width: 100%;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    try:
        # セッション状態の初期化
        initialize_session_state()

        # セッションタイムアウトのチェック
        check_session_timeout()

        # OAuth コールバックの処理
        if not st.session_state.authenticated:
            if not handle_oauth_callback():
                show_login_page()
                return

        # 認証状態に応じて表示
        if st.session_state.authenticated:
            show_dashboard()
        else:
            show_login_page()

    except Exception as e:
        st.error(f"アプリケーションエラー: {str(e)}")
        st.exception(e)

        # エラー時はログアウト
        if st.button("🔄 アプリケーションをリセット"):
            logout()
            st.rerun()


def show_rate_limit_info():
    """レート制限情報の表示（モック）"""
    st.subheader("📊 API制限状況（モックデータ）")
    
    # モックレート制限データを表示
    # 実際の実装では認証済みトークンを使用してX APIからレート制限を取得する
    if st.session_state.access_token:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "日次制限", 
                "8/17",
                delta="残り9回",
                help="モック: X API Basic プランの日次投稿制限"
            )
            st.progress(8/17, text="日次使用率: 47%")
        
        with col2:
            st.metric(
                "月次制限",
                "150/500", 
                delta="残り350回",
                help="モック: X API Basic プランの月次投稿制限"
            )
            st.progress(150/500, text="月次使用率: 30%")
        
        st.caption("🔄 モック: 次回リセット: 16時間後 (JST)")
        st.info("💡 これはモックデータです。実際の制限情報はX APIから取得されます。")
    else:
        st.warning("⚠️ 認証情報が無効です")


if __name__ == "__main__":
    main()
