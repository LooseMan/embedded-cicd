# embedded-cicd

## 初期設定

Git hooksをルートディレクトリの.githooksディレクトリに格納しています。
有効化のため、リポジトリをクローン（またはプル）した後、以下のコマンドを実行してください。
```zsh
% git config core.hooksPath .githooks
```

## 開発ルール
- **コミットメッセージ**: 必ず `feat:`, `fix:`, `chore:` などの Conventional Commits 形式のプレフィックスを付与してください（例: `feat: add terraform tflint`）。Gitフックによって強制されています。

## コンテナ構成

開発・ビルド環境と、実行時のランタイム環境を分離しています。

- 開発・ビルド環境: Microsoft の devcontainer image
- リリース環境: `debian:bookworm-slim` と実行に必要なライブラリ、バイナリ

各 `Containerfile` は2ステージ構成です。

```text
build   MS devcontainer image。ソースは実行時にマウントする
runtime 事前に生成したバイナリと動的ライブラリだけを含むリリース image
```

`devcontainer.json` は `build` target を使います。`build` stage はソースを同梱せず、開発時にワークスペースをマウントして使います。

runtime image を作るときは、先に `dist/hello_world` を生成します。その後の `docker build` は最後の `runtime` stage を生成します。

```sh
# Go のビルド環境を作成してバイナリを生成
docker build --target build -f go/Containerfile -t go-build:latest go
mkdir -p go/dist
docker run --rm --user root \
  --mount "type=bind,source=$PWD/go,target=/workspace" \
  go-build:latest \
  go build -o /workspace/dist/hello_world .

# Go のリリース image
docker build -f go/Containerfile -t go-runtime:latest go

# Rust も同様に、build stage でバイナリを生成してから runtime image を作る
docker build --target build -f rust/Containerfile -t rust-build:latest rust
mkdir -p rust/dist
docker run --rm --user root \
  --mount "type=bind,source=$PWD/rust,target=/workspace" \
  rust-build:latest \
  sh -c 'cargo build --release && cp target/release/hello /workspace/dist/hello_world'
docker build -f rust/Containerfile -t rust-runtime:latest rust
```

GitHub Actions の `build-go.yml` と `build-rust.yml` は `build` target のコンテナにソースをマウントしてバイナリを生成し、Artifact に保存します。`builder-go.yml` と `builder-rust.yml` は同じ手順で `dist/hello_world` を作成した後、デフォルトの `runtime` image を GHCR に push します。

外部ライブラリが動的リンクされる場合は、対応する実行時パッケージを各 `Containerfile` の `runtime` stage に追加してください。
