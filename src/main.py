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
    about = st.Page(page="chat.py", title="About", icon=":material/apps:")

    pg = st.navigation([top_page, about])
    pg.run()


if __name__ == "__main__":
    main()
