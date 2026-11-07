# Rust 開発運用

## 開発プロセス方針

正式運用では、Rustモジュールをコンテナイメージに組み込み、コンテナ経由で機能を利用します。ただし、開発中にこの手順を毎回行うと、イメージのビルドやコンテナの停止・再生成に時間がかかり、古いモジュールを使い続けるリスクもあります。

そのため開発段階では、次の方針で運用します。

- コンテナを使わず、ローカルでRustモジュールを差分ビルドする
- 動作確認にはデバッグビルドを使う
- `rust-analyzer` でタグジャンプや入力補助を利用する
- CodeLLDBで実行中のデーモンへアタッチしてGUIデバッグする
- `hdlctl.sh` で旧プロセスを停止し、ビルドした新モジュールへ切り替える

デバッグビルドはリリースビルドよりファイルサイズや実行性能で不利ですが、開発時のデバッグ性を優先します。

## hdlctl

`hdlctl.sh` は、Rustバイナリをローカルでビルドして起動する開発用スクリプトです。

```bash
# デバッグビルド（インクリメンタルビルド）
./rust/hdlctl.sh hello

# リリースビルド
./rust/hdlctl.sh --release hello
```

リリース用バイナリだけをビルドする場合は `build.sh` を使います。スクリプトのディレクトリへ移動してからビルドするため、どこから実行しても動作します。

```bash
./rust/build.sh
# api_server が生成される
# rust/openapi.json も生成される

# OpenAPI定義だけを生成
cargo run --manifest-path rust/Cargo.toml --bin generate_openapi
```

コンテナイメージのビルド時も、ビルドステージから同じ `build.sh` を実行します。実行ステージは `debian:bookworm-slim` で、エントリーポイントは Bash です。

第1引数に基底名を指定すると、`-handler` を付加した名前がCargoのバイナリ名・プロセス名・コンテナ名として使われます。

```text
cargo build --bin hello-handler
target/debug/hello-handler
```

起動前に、同名の稼働中コンテナがあれば `docker stop` で停止します。同名コンテナがなければ、ホスト上の同名プロセスを停止します。

## 環境変数

`rust/.env` を起動時に `source` し、定義された変数をRustプロセスへ引き継ぎます。

```dotenv
EXAMPLE=value
```

`.env` がない場合、起動は失敗します。秘密情報を含む場合はGitへコミットしないでください。

## CodeLLDBでデバッグ

`hdlctl.sh` は起動時にPIDを表示します。

```text
[hdlctl] starting hello-handler (pid=12345)
```

VS Codeの `Rust daemon: Attach` を実行し、表示されたPIDを入力すると、`.vscode/launch.json` の設定でCodeLLDBがアタッチします。

デバッグビルドで起動してください。リリースビルドでは最適化により、ステップ実行や変数表示が扱いにくくなる場合があります。
