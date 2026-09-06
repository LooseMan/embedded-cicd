# GitHub Container Registry（GHCR）運用メモ

## イメージ名の基本形

GHCR のイメージ名は次の形式で指定する。

```text
ghcr.io/<OWNER>/<IMAGE_NAME>:<TAG>
```

`OWNER` は GitHub のユーザー名または Organization 名であり、リポジトリ名ではない。

例えば、GitHub ユーザーが `LooseMan`、リポジトリ名が `embedded-cicd` の場合は、次のようになる。

```text
ghcr.io/looseman/embedded-cicd-go-builder:latest
ghcr.io/looseman/embedded-cicd-rust-builder:latest
```

## 小文字に統一する

Docker のイメージリポジトリ名は小文字でなければならない。

```text
ghcr.io/LooseMan/go-builder:latest  # エラー
ghcr.io/looseman/go-builder:latest  # 正しい
```

GitHub のユーザー名や Organization 名に大文字が含まれる可能性があるため、GitHub Actions ではタグを作る前に小文字化する。

```yaml
- name: Normalize image namespace
  id: image
  env:
    OWNER: ${{ github.repository_owner }}
  run: echo "namespace=ghcr.io/${OWNER,,}" >> "$GITHUB_OUTPUT"
```

その後、次のように使用する。

```yaml
tags: ${{ steps.image.outputs.namespace }}/go-builder:latest
```

## リポジトリ名をイメージ名に含める場合

リポジトリ名は `OWNER` の代わりにはならない。イメージ名の一部として含める。

```yaml
tags: ${{ steps.image.outputs.namespace }}/${{ github.event.repository.name }}-go-builder:latest
```

この場合、`github.event.repository.name` は `embedded-cicd` となる。

## GitHub Actions の権限

GHCR へ push するワークフローには、少なくとも次の権限が必要である。

```yaml
permissions:
  contents: read
  packages: write
```

ログインには、通常 `GITHUB_TOKEN` を使用する。

```yaml
- name: Log in to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

## pull とアクセス権限

GHCR の Container パッケージは、公開設定なら認証なしで pull できる。private または internal の場合は、パッケージの読み取り権限を持つユーザーまたは GitHub Actions が必要である。

GitHub Actions から private または internal イメージを利用する場合は、`packages: read` を付与してログインする。

```yaml
permissions:
  contents: read
  packages: read

steps:
  - name: Log in to GHCR
    uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
```

`docker run ghcr.io/<OWNER>/<IMAGE_NAME>:<TAG>` は、ローカルにイメージがなければ自動的に pull する。取得処理を明示したい場合は、次のように `docker pull` を先に実行する。

```yaml
- name: Pull builder image
  run: docker pull "$IMAGE"
```

公開イメージであればログインと `packages: read` は省略できるが、ビルダーイメージにはコンパイラーなどの実行環境が含まれるため、通常は private のまま Actions の `GITHUB_TOKEN` で読み取る構成を推奨する。

なお、イメージを push する場合は `packages: write` が必要である。`read` は取得専用、`write` は取得と push の権限である。

## 手動実行

push 以外に Actions 画面から実行したい場合は、トリガーに `workflow_dispatch` を追加する。

```yaml
on:
  push:
    branches:
      - main
  workflow_dispatch:
```

## このリポジトリでの推奨命名

リポジトリ名を `embedded-cicd` とする場合、GHCR のパッケージ名は次のようにする。

```text
go-builder
rust-builder
```

リポジトリ名を明示したい場合は、次の形式も使用できる。

```text
embedded-cicd-go-builder
embedded-cicd-rust-builder
```

## ビルダーイメージの更新条件

ビルダーイメージは、アプリケーションのソースコード変更では再ビルドしない。
ビルド環境を変更する次のファイルが `main` ブランチへ push された場合だけ、自動ビルドする。

```text
.github/workflows/builder-go.yml
.github/workflows/builder-rust.yml
go/Containerfile
rust/Containerfile
```

ソースコードを変更した場合や、その他のファイルだけを変更した場合は自動実行されない。
必要な場合は GitHub Actions の `Run workflow` から `workflow_dispatch` で手動実行する。

https://kkato.dev/posts/ghcr/

https://github.com/LooseMan?tab=packages
