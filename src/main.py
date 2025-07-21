import streamlit as st


def main():
    """
    使用方法:
        streamlit run main.py

    必要なライブラリ:
        - streamlit
    """
    top_page = st.Page(
        page="demo.py", title="Top", icon=":material/home:", default=True
    )
    chat = st.Page(page="chat.py", title="chat", icon=":material/apps:")

    pg = st.navigation([top_page, chat])
    pg.run()


if __name__ == "__main__":
    main()
