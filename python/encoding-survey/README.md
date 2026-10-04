# encoding-survey

SVN から Git への移行前に、既存ファイルの文字コードと改行コードを調査するためのツールです。

## 目的

このツールは**元ファイルを変更しません**。

以下を調査します。

- 拡張子があるファイル
  - `.cpp`
  - `.h`
  - `.c`
  - `.xml`
  - など、拡張子単位で集計
- 拡張子がないファイル
  - `Makefile`
  - `README`
  - `.gitignore`
  - など、ファイル名単位で集計
- 文字コード
- 改行コード
  - `CRLF`
  - `LF`
  - `CR`
  - `MIXED`
  - `NONE`
- 文字コード判定の confidence
- バイナリ／読み取りエラー

## 実行

```bash
python -m pip install -r requirements.txt
python analyze.py /path/to/svn-working-copy
```

出力先を指定する場合:

```bash
python analyze.py /path/to/svn-working-copy -o survey-result
```

## 出力

### files.csv

ファイル単位の生データです。

```text
path,type,key,size_bytes,status,encoding,confidence,eol,error
src/main.cpp,extension,.cpp,12345,OK,SHIFT_JIS,0.9900,CRLF,
src/main.h,extension,.h,5432,OK,SHIFT_JIS,0.9800,CRLF,
Makefile,filename,Makefile,1024,OK,ascii,1.0000,LF,
```

### summary.csv

拡張子／ファイル名 × 文字コード × 改行コードで集計します。

```text
key,encoding,eol,count
*.cpp,SHIFT_JIS,CRLF,120
*.cpp,UTF-8-SIG,LF,3
*.h,SHIFT_JIS,CRLF,80
Makefile,ascii,LF,1
```

この結果から、例えば

- `.cpp` は `SHIFT_JIS + CRLF` が標準
- `.cpp` に `UTF-8 + LF` の例外が3件
- `.h` は `SHIFT_JIS + CRLF`
- `Makefile` は `ASCII + LF`

といった判断ができます。

## 注意

文字コード判定はヒューリスティックです。

特に日本語ソースでは `Shift_JIS` / `CP932` などの判定が完全に確定するとは限らないため、`confidence` も確認してください。

また、NUL バイトを含むファイルは第一段階では `BINARY` として扱います。

## 次の段階

この調査結果を確認してから、

1. 拡張子／ファイル名ごとの標準文字コードを決める
2. 標準改行コードを決める
3. 標準から外れるファイルを例外一覧として抽出
4. `.gitattributes` を設計
5. Git checkout 後の文字コード／改行コードを検証

という流れに進めます。

このツール自体は、現段階では `.gitattributes` を生成・変更しません。
