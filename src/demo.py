# streamlit_super_benefits.py
import streamlit as st
import pandas as pd
import numpy as np

# ページの基本設定
st.set_page_config(
    layout="centered",  # ページコンテンツを中央に配置
    page_title="Streamlitって、こんなにすごいんです！",  # ブラウザタブに表示されるタイトル
    initial_sidebar_state="collapsed",  # サイドバーを初期状態で閉じる
)

# ヘッダー
st.title("🚀 Streamlitって、こんなにすごいんです！")

st.write(
    """
Streamlitは、Pythonを使っているなら絶対に知っておきたい、めちゃくちゃ便利なツールなんです！
Web開発の専門知識がなくても、**Pythonのコードだけでサクッと魅力的なWebアプリが作れちゃう**のが最大の魅力。
データを見せたり、モデルをデモしたりするのに、まさにうってつけなんです。
"""
)

st.header("簡易的なグラフ")

chart_data = pd.DataFrame(
    np.random.randn(20, 3),  # 20個のデータポイント、3つの系列
    columns=["データA", "データB", "データC"],  # 列名
)

st.subheader("折れ線グラフ")
# Streamlitのst.line_chart()で折れ線グラフを表示
st.line_chart(chart_data)

st.write(
    """
上部の「データA」「データB」「データC」のチェックボックスをクリックすると、
表示する系列をON/OFFできます。
"""
)

st.subheader("データの確認")
st.dataframe(chart_data)

st.caption("※データはアプリを起動するたびにランダムに生成されます。")

st.header("インタラクション系")
st.subheader("スライダー")
selected_number = st.slider(
    "好きな数字を選んでください:",  # スライダーのラベル
    min_value=0,  # 最小値
    max_value=100,  # 最大値
    value=50,  # 初期値
    step=1,  # ステップ（刻み）
)

st.write(f"あなたが選んだ数字は **{selected_number}** です。")


# ボタンの作成
st.subheader("アクションボタン")
if st.button("メッセージを表示！"):  # ボタンがクリックされたらTrueになる
    st.success(f"ボタンがクリックされました！選ばれた数字は {selected_number} ですね！")
else:
    st.info("上のボタンをクリックしてください。")


st.info(
    "Streamlitがあれば、あなたの作ったデータ分析や機械学習の成果が、もっと多くの人にとって「使える」「面白い」ものになるはずです。ぜひ気軽に試してみてくださいね！"
)
