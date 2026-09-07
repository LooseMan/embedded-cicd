---
name: gitattributes-file-generator
description: "Generate or edit repository files while honoring .gitattributes, including encoding, line endings, and binary handling."
---

# .gitattributes File Generator

このリポジトリでファイルを生成・編集するときは、リポジトリ直下の `.gitattributes` を基準に、対象ファイルの形式を維持・検証する。ユーザーが指定した対象・内容を優先し、無関係なファイルは変更しない。

## 手順

1. `.gitattributes` を読み、対象パスの実効属性を `git check-attr -a -- <path>` で確認する。必要なら `.git/info/attributes` やグローバル属性も確認する。
2. 既存ファイルは `file`、`xxd` などで実際のエンコーディングと改行を確認する。属性と実体が異なる場合は、変換前にその差異を把握する。
3. 属性に従って生成・編集する。`eol=lf` は LF、`eol=crlf` は CRLF、`working-tree-encoding` は指定エンコーディング、`binary` はバイト列を変更しない。編集ツールが形式を保てない場合は、明示的な変換ツールを使う。
4. `git check-attr` とバイト列で再検証する。テキストは指定エンコーディングで読み書きできること、改行が混在しないこと、バイナリは内容を壊していないことを確認する。
5. 変更したファイル、適用属性、検証結果、未検証事項を簡潔に報告する。

## ルール

- `.gitattributes` の規則を推測で変更・上書きしない。ユーザー指定と矛盾する場合は、対象パスの例外を明示的に追加するか、矛盾を報告する。
- 既存ファイルは依頼された対象だけを変更する。`git add --renormalize` や一括変換は行わない。
- 対象形式で表現できない文字は追加しない。コメントを書く場合は日本語とし、対象エンコーディングで表現できる文字だけを使う。
- 属性が未指定のファイルは、自動変換せず既存のバイト列を基準に扱う。判定できない場合は推測せず報告する。
