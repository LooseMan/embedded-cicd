"""SFTP転送で共通して使用する設定・接続・ファイル処理。"""

from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    username: str
    password: str
    remote_dir: str
    legacy: bool = False

    @classmethod
    def from_dict(cls, config: dict[str, object], name: str) -> "ServerConfig":
        try:
            server = config[name]
            if not isinstance(server, dict):
                raise TypeError(f"{name}はオブジェクトにしてください")
            return cls(
                host=str(server["host"]),
                port=int(server["port"]),
                username=str(server["username"]),
                password=str(server["password"]),
                remote_dir=str(server["remote_dir"]),
                legacy=bool(server.get("legacy", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{name}の設定が不足しているか不正です: {exc}") from exc


def load_config(config_path: Path) -> dict[str, object]:
    """JSON設定ファイルを読み込む。"""
    try:
        with config_path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON設定ファイルが不正です: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("JSON設定のルートはオブジェクトにしてください")
    return config


def get_filename_pattern(config: dict[str, object]):
    """設定からファイル名正規表現を作成する。"""
    try:
        return re.compile(str(config["filename_pattern"]))
    except re.error as exc:
        raise ValueError(f"ファイル名の正規表現が不正です: {exc}") from exc
    except KeyError as exc:
        raise ValueError("filename_patternが設定されていません") from exc


def _add_supported(current, additional, supported):
    return tuple(dict.fromkeys((*current, *(x for x in additional if x in supported))))


def _connect_legacy(paramiko, server: ServerConfig):
    transport = paramiko.Transport((server.host, server.port))
    options = transport.get_security_options()
    options.kex = _add_supported(
        options.kex, ("diffie-hellman-group1-sha1",), transport._kex_info
    )
    options.key_types = _add_supported(
        options.key_types, ("ssh-rsa", "ssh-dss"), transport._key_info
    )
    options.ciphers = _add_supported(
        options.ciphers,
        ("aes128-cbc", "aes256-cbc", "3des-cbc", "blowfish-cbc"),
        transport._cipher_info,
    )
    options.digests = _add_supported(
        options.digests, ("hmac-md5",), transport._mac_info
    )
    transport.connect(username=server.username, password=server.password)
    return transport


class SftpSession:
    """通常SSHとレガシーSSHの両方に対応したSFTPセッション。"""

    def __init__(self, server: ServerConfig):
        self.server = server
        self.client = None
        self.transport = None
        self.sftp = None

    def __enter__(self):
        try:
            import paramiko
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Paramikoが必要です。`python3 -m pip install paramiko` で導入してください。"
            ) from exc
        if self.server.legacy:
            self.transport = _connect_legacy(paramiko, self.server)
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        else:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.server.host,
                port=self.server.port,
                username=self.server.username,
                password=self.server.password,
            )
            self.sftp = self.client.open_sftp()
        return self.sftp

    def __exit__(self, exc_type, exc_value, traceback):
        if self.sftp is not None:
            self.sftp.close()
        if self.client is not None:
            self.client.close()
        if self.transport is not None:
            self.transport.close()


def find_local_files(local_dir: Path, pattern) -> list[Path]:
    if not local_dir.is_dir():
        raise NotADirectoryError(f"ローカルパスがディレクトリではありません: {local_dir}")
    return sorted(
        path for path in local_dir.iterdir()
        if path.is_file() and pattern.fullmatch(path.name) is not None
    )


def find_remote_files(sftp, remote_dir: str, pattern):
    return sorted(
        entry for entry in sftp.listdir_attr(remote_dir)
        if stat.S_ISREG(entry.st_mode)
        and pattern.fullmatch(entry.filename) is not None
    )


def file_mode(file_stat) -> int:
    return stat.S_IMODE(file_stat.st_mode)
