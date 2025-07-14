# chat_demo_app.py
import streamlit as st
import time

# ページの基本設定
st.set_page_config(layout="centered", page_title="AIチャットデモ")

st.title("💬 AIチャットデモ")

st.write("""
Streamlitのチャット機能を使って、簡単な対話を体験してみましょう！
下の入力ボックスにメッセージを入力して送信してください。
""")

# チャット履歴を保持するセッションステートを初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去のメッセージを表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーからの入力を受け付ける
if prompt := st.chat_input("何か話しかけてください..."):
    # ユーザーのメッセージをチャット履歴に追加して表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # アシスタント（AI）の応答を生成
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):  # AIが応答を生成している間のスピナー
            time.sleep(1)  # 応答を生成するまでの擬似的な遅延

            response = ""
            if "こんにちは" in prompt or "こんばんは" in prompt or "おは" in prompt:
                response = "こんにちは！何かお手伝いできることはありますか？"
            elif "ありがとう" in prompt:
                response = "どういたしまして！お役に立てて嬉しいです。"
            elif "天気" in prompt:
                response = "すみません、今の天気情報は分かりません。私はまだ学習中です！"
            elif "名前" in prompt:
                response = "私はStreamlitのデモアシスタントです！"
            elif "streamlit" in prompt.lower():
                response = "StreamlitはPythonでWebアプリを簡単に作れる素晴らしいツールですよ！"
            elif "さようなら" in prompt or "またね" in prompt:
                response = "またお話ししましょう！良い一日を！"
            else:
                response = "申し訳ありません、その質問にはまだお答えできません。もっと勉強しますね！"

            st.markdown(response)
    # アシスタントのメッセージをチャット履歴に追加
    st.session_state.messages.append({"role": "assistant", "content": response})

st.markdown("---")
st.caption("※これはデモ目的の簡易的な応答です。")
