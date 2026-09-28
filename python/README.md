# Pythonファイル転送ツール

SFTPを利用してファイルを転送するスクリプトです。コマンドラインではJSON設定ファイルのパスだけを指定します。

## 構成

- `upload_module.py`: ローカルディレクトリ直下のファイルをSFTPサーバへアップロードします。
- `download_module.py`: SFTPサーバからファイルを取得し、別のSSHサーバへ中継転送します。
- `transfer_common.py`: 接続、設定読み込み、ファイル抽出、アクセス権処理などの共通処理です。

対象ファイルは指定パスの直下だけです。ファイル名は `filename_pattern` の正規表現で完全一致します。サブディレクトリは対象外です。

## 必要な環境

Paramikoをインストールします。

```bash
python3 -m pip install paramiko
```

## ローカルからSFTPへのアップロード

設定例は `upload_config.example.json` です。

```bash
python3 python/upload_module.py python/upload_config.example.json
```

設定項目:

```json
{
  "local_dir": "/path/to/local",
  "filename_pattern": ".*\\.zip",
  "sftp_server": {
    "host": "sftp.example.com",
    "port": 22,
    "username": "sftp_user",
    "password": "change_me",
    "remote_dir": "/remote/upload/path"
  }
}
```

## SFTPから別SSHサーバへの中継

設定例は `download_config.example.json` です。

```bash
python3 python/download_module.py python/download_config.example.json
```

処理は次の順番です。

1. SFTPサーバの指定ディレクトリ直下から対象ファイルを抽出
2. ローカルの一時ディレクトリへ取得
3. 転送先SSHサーバへSFTP over SSHで転送
4. 転送先へアクセス権を設定
5. ローカルの一時ファイルを削除

設定項目:

```json
{
  "filename_pattern": ".*\\.zip",
  "staging_dir": "/tmp",
  "source_sftp": {
    "host": "sftp.example.com",
    "port": 22,
    "username": "sftp_user",
    "password": "change_me",
    "remote_dir": "/path/to/source"
  },
  "destination_ssh": {
    "host": "ssh.example.com",
    "port": 22,
    "username": "ssh_user",
    "password": "change_me",
    "legacy": false,
    "remote_dir": "/path/to/destination"
  }
}
```

### RHEL 5.6相当のレガシーサーバ

転送先が古いOpenSSHの場合は、`destination_ssh.legacy` を `true` にします。旧KEX、`ssh-rsa`／`ssh-dss`、CBC系暗号などを接続候補へ追加します。

```json
"legacy": true
```

レガシー接続は暗号強度が低い方式を含むため、対象サーバを限定して使用してください。接続できない場合は、Paramikoが出力する `no matching ... found` のエラー内容に応じて候補を調整します。

## アクセス権

アップロード・中継転送のどちらも、元ファイルのmode（例: `0644`）を取得し、転送後に `chmod` で同じmodeを設定します。所有者やグループは変更しません。

## 注意事項

- 接続パスワードはJSONへ平文で記述する方式です。設定ファイルの権限を制限し、リポジトリへ認証情報を登録しないでください。
- 現在の接続処理は未知のホスト鍵を自動受け入れします。本番運用ではホスト鍵検証を追加してください。
- 実行前に、転送先ディレクトリへの書き込み権限と、`staging_dir` への書き込み権限を確認してください。
