# embedded-cicd

## 初期設定

Git hooksをルートディレクトリの.githooksディレクトリに格納しています。有効化のため、リポジトリをクローン（またはプル）した後、以下のコマンドを実行してください。
```zsh
% git config core.hooksPath .githooks
```

## 開発ルール
- **コミットメッセージ**: 必ず `feat:`, `fix:`, `chore:` などの Conventional Commits 形式のプレフィックスを付与してください（例: `feat: add terraform tflint`）。Gitフックによって強制されています。

## コンテナ構成

開発環境、ビルド環境、実行時のランタイム環境を分離しています。

- 開発環境: Microsoft の devcontainer image
- Go ビルド環境: `golang:1.22-bookworm`
- Rust ビルド環境: `rust:1.96-slim-bookworm`
- リリース環境: `debian:bookworm-slim` と実行に必要なライブラリ、バイナリ

各 `Containerfile` は2ステージ構成です。

```text
build   各言語のビルド image。build.sh でバイナリを生成する
runtime 生成済みバイナリと実行時に必要なパッケージだけを含むリリース image
```

Go の `build` stage は `golang:1.22-bookworm`、Rust の `build` stage は `rust:1.96-slim-bookworm` を使用します。各 `build` stage は対応する `build.sh` を実行してバイナリを生成します。開発用コンテナは `.devcontainer` の設定で別途選択します。

本リポジトリは、プロジェクト直下に複数のプロジェクトを並べて管理するモノレポ構成を想定しています。そのため、開発コンテナの設定はルートの `.devcontainer` 配下にプロジェクト単位で配置しています。

```text
.devcontainer/
├── go/devcontainer.json
└── rust/devcontainer.json
```

プロジェクトを追加する場合も同じ構成で設定を追加でき、Go 用・Rust 用など、作業対象に応じた `devcontainer.json` を選択して開発できます。各設定はリポジトリルートをワークスペースとしてマウントし、対象プロジェクトのディレクトリを開く構成です。これにより、プロジェクトごとの `Containerfile` と開発環境の設定を近接させながら、モノレポ全体の管理場所を統一しています。

各 `Containerfile` は、ビルドステージで `build.sh` を実行した後、生成されたバイナリを `debian:bookworm-slim` の runtime stage にコピーします。runtime のエントリーポイントは Bash です。

```sh
# Go のローカルビルド
./go/build.sh

# Go のリリース image
docker build -f go/Containerfile -t go-runtime:latest go

# Rust のローカルビルド
./rust/build.sh

# Rust のリリース image
docker build -f rust/Containerfile -t rust-runtime:latest rust
```

GitHub Actions や GitLab CI からも、各プロジェクトの `build.sh` を利用してバイナリと runtime image を生成します。

外部ライブラリが動的リンクされる場合は、対応する実行時パッケージを各 `Containerfile` の `runtime` stage に追加してください。
