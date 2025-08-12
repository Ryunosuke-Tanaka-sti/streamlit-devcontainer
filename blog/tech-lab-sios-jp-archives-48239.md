# DevContainerでStreamlit開発を始める方法：Docker＋VSCode | SIOS Tech. Lab

**URL:** [https://tech-lab.sios.jp/archives/48239](https://tech-lab.sios.jp/archives/48239)

**メタディスクリプション:** StreamlitをDevContainerで開発する環境構築を実践解説。Docker+VSCode+Gitの統合開発環境からflake8設定まで完全対応

## 目次

1. [挨拶](#挨拶)
2. [Stremlit開発環境をDevContainerで作成する](#stremlit開発環境をdevcontainerで作成する)
   - [ディレクトリ構成](#ディレクトリ構成)
   - [Dockerfile](#dockerfile)
   - [compose.yml](#composeyml)
   - [devcontainer.json](#devcontainerjson)
   - [フォーマット＆リンター設定](#フォーマットリンター設定)
3. [Stremlitのデモ](#stremlitのデモ)
4. [まとめ](#まとめ)

## 挨拶

ども！最近はAI関連からInfrastructure as Code（IaC）などにも入門して幅広いブログを執筆している龍ちゃんです。最近はブログ執筆にAIを導入して、執筆スピードと質が上がっているような気がして楽しいですね。7月にまとめた内容は8月の初頭に45分セミナーにまとめるので、激しめに検証を進めています。

さて今回は「Stremlit」のお話になります。最近ふんわりとStremlitを書く機会が増えたので、DevContainerで開発する環境構築をまとめていこうと思います。

## Stremlit開発環境をDevContainerで作成する

今回は、開発環境を使いまわす可能性を考慮してGitに環境を上げています。もし使いたい方がいれば、[リポジトリをクローン](https://github.com/Ryunosuke-Tanaka-sti/streamlit-devcontainer)して利用してください。

### ディレクトリ構成

今回作成する環境のディレクトリ構成になります。venvなどでも構築できるように`.devcontainer`内でコンテナの定義をすべて収めています。リポジトリのトップからマウントすることで、コンテナ内でGit操作をすることができます。

```
.
├── .devcontainer
│   ├── Dockerfile
│   ├── compose.yml
│   └── devcontainer.json
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── sample.env
├── setup.cfg
└── src
    └── main.py
```

### Dockerfile

ベースイメージは、[Microsoftが出しているPython 3.11のベースイメージ](https://hub.docker.com/r/microsoft/devcontainers-python)を利用しています。利点として、以下の二点があります。

- Gitが標準で搭載されている
- vscodeユーザーがデフォルトで作成されている（非rootユーザー）
- コード解析・フォーマッター「flake8」「black」が標準搭載

Dockerfile内で行っている処理は、pipのアップグレードのみになります。

```dockerfile
# Use the official Microsoft Python image (Debian Bullseye based)
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Set the working directory
WORKDIR /home/vscode/python

# Install Python packages that are commonly used
RUN pip install --upgrade pip

# Keep the container running
CMD ["sleep", "infinity"]
```

### compose.yml

将来的な拡張（データベース等）を考えて、composeファイルで定義しています。リポジトリのルートディレクトリからマウントすることで、仮想環境内からGitコマンドを直接実行することができます。

Streamlitでデフォルトで公開されるポート（8501）を接続しています。

```yaml
services:
  python:
    build:
      context: .
      dockerfile: ./Dockerfile
    tty: true
    volumes:
      - type: bind
        source: ../
        target: /home/vscode/python
    restart: always
    ports:
      - "8501:8501"
```

### devcontainer.json

今回作成するファイルの中で最も記述量が多いファイルになります。基本的にコピー＆ペーストで大丈夫です。設定している主要項目としては以下になります。

- 拡張機能の追加
- 開発環境設定
- 開発用feature（Azure CLI・GitHub CLI）

開発環境設定では、pylintを無効化してflake8を有効化するように設定しています。ファイルをセーブしたタイミングでリンターとフォーマッターが実行されるように設定しています。

```json
{
    "name": "Streamlit",
    "service": "python",
    "dockerComposeFile": "./compose.yml",
    "workspaceFolder": "/home/vscode/python",
    "shutdownAction": "stopCompose",
    "customizations": {
        "vscode": {
            "extensions": [
                "ms-python.python",
                "ms-python.black-formatter",
                "ms-vscode.vscode-json",
                "ms-python.flake8"
            ],
            "settings": {
                "python.defaultInterpreterPath": "/usr/local/bin/python",
                "python.formatting.provider": "black",
                "terminal.integrated.defaultProfile.linux": "bash",
                "python.linting.enabled": true,
                "python.linting.pylintEnabled": true,
                "python.linting.lintOnSave": true,
                "python.linting.flake8Enabled": true,
                "[python]": {
                    "editor.formatOnSave": true,
                    "editor.defaultFormatter": "ms-python.black-formatter"
                }
            }
        }
    },
    "features": {
        "ghcr.io/devcontainers/features/azure-cli:1": {},
        "ghcr.io/devcontainers/features/github-cli": {}
    },
    "forwardPorts": [
        8501
    ],
    "portsAttributes": {
        "8501": {
            "label": "Streamlit",
            "onAutoForward": "notify"
        }
    },
    "postCreateCommand": "pip install -r requirements.txt",
    "remoteUser": "vscode",
    "updateRemoteUserUID": true
}
```

featureとしてAzure CLIとGitHub CLIをインストールしています。これは将来的にデプロイ先をAzure Web Apps on Containerでデプロイすることを考慮して設定しています。

### フォーマット＆リンター設定

前段の設定のみで開発を進めることができますが、一転問題があります。flake8とblackのデフォルトの設定が競合してしまい、問題が発生します。flake8かblackのどちらかに設定を合わせる必要があります。`setup.cfg`ファイルを作成して、以下の内容をコピー＆ペーストすることで設定することが可能です。

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503, E501
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    .env,
    env
```

## Stremlitのデモ

ここまでで開発環境は整備することができたので、Stremlitで簡易的なページを作成を進めていきます。

まずは、Stremlitの機能をインストールをしましょう。

```bash
# stremlitのインストール
pip install streamlit

# requirements.txtにインストールしたファイルの設定
pip freeze > requirements.txt 
```

`src > main.py`を設定して以下のファイルをコピー＆ペーストをしてください。

```python
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

st.title("🚀 Streamlitの素晴らしい利点")

st.write(
    "Streamlitを使えば、データサイエンスのプロジェクトを瞬く間にインタラクティブなWebアプリに変えることができます。"
    "もう複雑なWeb開発の知識は必要ありません！"
)

st.subheader("💡 利点1: 圧倒的な手軽さ")
st.write(
    "Pythonの知識だけで、データスクリプトから直接Webアプリを作成できます。HTML、CSS、JavaScriptなどの"
    "フロントエンドの知識は一切不要です。これにより、開発時間を大幅に短縮できます。"
)
st.code(
    """
import streamlit as st
st.title("こんにちは、Streamlit！")
st.write("これはたった数行のコードです。")
"""
)

st.subheader("⚡ 利点2: 迅速なプロトタイピング")
st.write(
    "コードを変更するたびに、アプリがリアルタイムで更新されます。これにより、アイデアをすぐに形にし、"
    "フィードバックを得ながら反復的に開発を進めることができます。まるでライブコーディングをしているようです！"
)
st.info(
    "💡 ヒント: このページを保存して、Streamlitを実行したままコードを編集してみてください。"
)

st.subheader("📊 利点3: 美しいデータ可視化が簡単に")
st.write(
    "Matplotlib, Plotly, Altairなどの既存のPython可視化ライブラリとシームレスに統合できます。数行のコードで"
    "インタラクティブなグラフやダッシュボードを作成できます。"
)

# サンプルグラフの表示

chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])
st.line_chart(chart_data)
st.bar_chart(chart_data)

st.subheader("🔄 利点4: インタラクティブなウィジェット")
st.write(
    "スライダー、ボタン、テキスト入力など、多様なウィジェットを簡単に組み込むことができます。"
    "これにより、ユーザーがデータと対話できる動的なアプリケーションを作成できます。"
)

# インタラクティブなデモ
value = st.slider("スライダーを動かしてみてください", 0, 100, 50)
st.write(f"現在の値: {value}")

button_clicked = st.button("ボタンを押してみてください")
if button_clicked:
    st.success("ボタンが押されました！")

user_text = st.text_input("ここに何か入力してください", "Streamlitは最高！")
st.write(f"あなたが入力した内容: {user_text}")

st.subheader("☁️ 利点5: デプロイのしやすさ")
st.write(
    "Streamlit Community Cloudを使えば、数クリックでアプリをWebに公開できます。また、Dockerなどの"
    "コンテナ技術と組み合わせることで、より柔軟なデプロイも可能です。"
)

st.video("https://www.youtube.com/watch?v=NtLCVE9hwb8")  # Streamlitの紹介動画（例）

st.write("---")
st.markdown(
    "### まとめ\n"
    "Streamlitは、データサイエンティストやアナリストがアイデアを迅速に具現化し、"
    "それをインタラクティブな形で共有するための強力なツールです。"
    "ぜひご自身のプロジェクトで試してみてください！"
)

st.balloons()
```

ファイルを作成したら、以下のコマンドで起動することができます。

```bash
streamlit run src/main.py
```

デフォルトで`http://0.0.0.0:8501`が立ち上がって真っ白な画面が立ち上がってもあせらなくて大丈夫です。`http://localhost:8501`にアクセスしてみてください。以下の画面が表示されれば成功です。

## まとめ

今回は、StreamlitをDevContainerで開発する環境構築について詳しく見てきました。DevContainerを使うことで、チーム内での開発環境統一や、プロジェクトの引き継ぎがスムーズになりますね。

特に今回のポイントとしては、MicrosoftのPython 3.11ベースイメージを使うことで、Gitやコード解析ツールが標準搭載されている点が大きなメリットでした。また、flake8とblackの設定競合問題も、setup.cfgファイルで解決できることがわかりました。

Streamlitは本当に手軽にデータアプリケーションを作成できる素晴らしいツールです。今回構築した環境なら、コードを変更するたびにリアルタイムで結果を確認できるので、開発効率が格段に向上します。

皆さんも、ぜひこの環境でStreamlitアプリケーション開発にチャレンジしてみてください！GitHubリポジトリも公開しているので、クローンして即座に開発を始められます。

次回は、このStreamlit環境をAzure Web Apps on Containerでデプロイする方法について解説予定です。お楽しみに！

こちらのブログ「[Infrastructure as Code実践：Azure SWA×Bicep×GitHub Actions](https://tech-lab.sios.jp/archives/48079)」と同様の手順でBicepで環境作成からAzureへのデプロイまで目指していきます。