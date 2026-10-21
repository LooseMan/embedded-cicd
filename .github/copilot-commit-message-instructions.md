# コミットメッセージ生成ルール

ステージされた変更内容だけを根拠に、次のルールでコミットメッセージを生成してください。

- Conventional Commits 形式にする。
- 形式は `<type>(<scope>): <subject>` とする。`scope` は必要な場合だけ付ける。
- `type` は `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf` のいずれかにする。
- `subject` は変更内容を表す簡潔な命令形・現在形にする。
- `subject` の末尾にピリオドを付けない。
- 生成結果はコミットメッセージだけにする。説明文、Markdown のコードブロック、引用符は付けない。
- 例: `feat(auth): ログイン機能を追加`
