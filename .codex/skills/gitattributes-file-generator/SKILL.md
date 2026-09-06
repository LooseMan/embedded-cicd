---
name: gitattributes-file-generator
description: "Use for every file generation or edit in this repository, and for validating files against .gitattributes, including LF, CP932/CRLF, path-specific attributes, and binary-file handling."
---

# .gitattributes File Generator

このリポジトリでファイルを生成・編集・変換する場合は、依頼内容にかかわらず必ずこのスキルを適用する。リポジトリ直下の `.gitattributes` を唯一の設定源として、指定された属性に合うファイルを生成・検証する。

生成物にコメント構文がある場合、コメントは日本語で記述する。対象形式にコメント構文がない場合や、機械的に埋め込まれる固定コメントは除く。文字コード制約がある場合は、日本語コメントもその文字コードで表現できる文字だけを使う。

## Workflow

1. リポジトリルートを特定し、`.gitattributes` を最初に読む。
   - ファイル生成・編集の依頼では、他の作業手順より先に必ず読む。
2. ファイル内の有効な規則を分類する。
   - `text=auto` などのデフォルト規則
   - `eol=lf` の規則
   - `working-tree-encoding=cp932` と `eol=crlf` の規則
   - 特定パスに対する規則
   - `binary` の規則
3. ユーザーが指定した出力先・ファイル名・内容を優先する。指定がない場合は、各分類を確認できる最小限の代表ファイルを生成する。
4. 必要な親ディレクトリを作成する。既存ファイルは、ユーザーが上書きを明示しない限り変更しない。
5. 生成内容を属性に合わせて書き込む。
   - `eol=lf`: LF (`0x0a`) のみを使う。
   - `eol=crlf`: CRLF (`0x0d 0x0a`) を使う。
   - `working-tree-encoding=cp932`: CP932 でエンコードする。CP932 で表現できない文字は使わず、書き込み後にデコードできることを確認する。
   - `binary`: テキストとして改行変換せず、バイナリ内容を保持する。画像やPDFのダミーを作る場合は、拡張子だけでなく内容の妥当性も確認する。
6. Git が実際に適用する属性を確認する。
   - `git check-attr -a -- <path>`
   - 必要に応じて `git check-attr --all --cached -- <path>` も実行する。
7. バイト列を検査する。LF対象にCRLFがないこと、CRLF対象の改行がCRLFであること、CP932対象がCP932として読み書きできること、バイナリ対象が変更されていないことを確認する。
8. 生成したファイル、適用された属性、検証結果、検証できなかった点を簡潔に報告する。

## Rules

- `.gitattributes` の規則を推測で上書きしない。矛盾する規則や未対応の属性があれば、該当パターンと解釈を報告して停止する。
- `.git/info/attributes`、グローバル属性、`.gitignore` を必要に応じて確認し、`.gitattributes` だけでは実効結果を説明できない場合はその旨を報告する。
- Git のパターンは通常の glob と完全には一致しないため、パスを変更する前に `git check-attr` で確認する。
- `*.bat` や `*.cmd` のような CP932対象には、絵文字やUTF-8固有文字を含めない。
- `*.md` や `*.sh` は、内容をUTF-8で作成しても改行は必ずLFにする。
- 生成後に `git add --renormalize` や既存ファイルの一括変換を実行しない。依頼されたファイルの生成・検証だけを行う。
- 失敗した場合は、属性の問題、エンコーディングの問題、改行の問題を分けて報告し、部分的に成功したファイルも明示する。

## Default Fixture Set

出力対象が指定されていない場合は、既存ファイルを確認してから、次のうち不足しているものだけを提案または生成する。

- `fixtures/lf/sample.md`: UTF-8、LF
- `fixtures/lf/sample.sh`: UTF-8、LF
- `src/linux_scripts/sample.sh`: UTF-8、LF
- `fixtures/cp932/sample.bat`: CP932、CRLF
- `fixtures/cp932/sample.cmd`: CP932、CRLF
- `docs/legacy_sjis/sample.txt`: UTF-8、CRLF（この規則は改行だけを固定する）
- `fixtures/binary/sample.png`: 有効なPNGバイト列、改行変換なし
- `fixtures/binary/sample.jpg`: 有効なJPEGバイト列、改行変換なし
- `fixtures/binary/sample.pdf`: 有効なPDFバイト列、改行変換なし

代表ファイルの生成が依頼の目的に対して過剰な場合は、必要な分類だけを対象にする。テスト用ファイルを生成した場合は、テスト用であることが分かるディレクトリに置き、不要な大きなバイナリは作らない。
