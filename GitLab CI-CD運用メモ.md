# GitLab CI/CD運用メモ

## パイプライン

ルートの`.gitlab-ci.yml`から4つのCIジョブを読み込む。

| ジョブ | 処理 |
| --- | --- |
| `build-go` | Go builderイメージでバイナリをビルドし、成果物として保存 |
| `build-rust` | Rust builderイメージでバイナリをビルドし、成果物として保存 |
| `build-go-builder` | Go builderイメージをビルドし、GitLab Container Registryへpush |
| `build-rust-builder` | Rust builderイメージをビルドし、GitLab Container Registryへpush |

自動実行は`main`ブランチへのpushに限定し、各ジョブはGitHub Actionsと同じ対象ファイルの変更で起動する。GitLabの画面からパイプラインを手動実行すると4ジョブがmanualとして表示され、必要なフローだけを個別に開始できる。

## Container Registry

GitLab CIではプロジェクトに紐づくGitLab Container Registryを使用する。イメージは以下のパスへ保存される。

```text
$CI_REGISTRY_IMAGE/go-builder:latest
$CI_REGISTRY_IMAGE/rust-builder:latest
```

`CI_REGISTRY`、`CI_REGISTRY_IMAGE`、`CI_REGISTRY_USER`、`CI_REGISTRY_PASSWORD`の定義済み変数を使うため、認証用の独自CI/CD変数は不要。プロジェクトでContainer Registryを有効にすること。

GitLab RunnerはDocker-in-Dockerを使うため、Docker executorでは`privileged`を許可する必要がある。