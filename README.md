# Python環境


## トラブルシューティング

### ファイルのUID：GIDがvscodeとならない

1. WSL環境に戻り、ログインしているユーザーのUID：GIDを調べる

    ```bash

    id
    
    ```
2. `.env`を作成し、情報を入力 

    ```bash
    
    cp sample.env .env
    
    ```

3. DevContainer立ち上げ