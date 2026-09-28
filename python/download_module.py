#!/usr/bin/env python3
"""SFTPサーバから別のSSHサーバへファイルを中継転送する。"""

from __future__ import annotations

import argparse
import posixpath
import sys
import tempfile
from pathlib import Path

from transfer_common import (
    ServerConfig,
    SftpSession,
    file_mode,
    find_remote_files,
    get_filename_pattern,
    load_config,
)


def forward_files(
    source_sftp,
    destination_sftp,
    source_server: ServerConfig,
    destination_server: ServerConfig,
    candidates,
    staging_dir: Path,
) -> int:
    forwarded_count = 0
    with tempfile.TemporaryDirectory(dir=staging_dir) as temporary_dir:
        for entry in candidates:
            source_path = posixpath.join(source_server.remote_dir, entry.filename)
            destination_path = posixpath.join(
                destination_server.remote_dir, entry.filename
            )
            local_path = Path(temporary_dir) / entry.filename
            mode = file_mode(entry)

            source_sftp.get(source_path, str(local_path))
            destination_sftp.put(str(local_path), destination_path, confirm=True)
            destination_sftp.chmod(destination_path, mode)
            print(f"forwarded: {source_path} -> {destination_path} (mode={mode:04o})")
            forwarded_count += 1
    return forwarded_count


def forward_matching_files(config: dict[str, object]) -> int:
    staging_dir = Path(config["staging_dir"])
    source_server = ServerConfig.from_dict(config, "source_sftp")
    destination_server = ServerConfig.from_dict(config, "destination_ssh")
    pattern = get_filename_pattern(config)
    if not staging_dir.is_dir():
        raise NotADirectoryError(f"一時保存先がディレクトリではありません: {staging_dir}")

    with SftpSession(source_server) as source_sftp:
        candidates = find_remote_files(source_sftp, source_server.remote_dir, pattern)
        with SftpSession(destination_server) as destination_sftp:
            return forward_files(
                source_sftp,
                destination_sftp,
                source_server,
                destination_server,
                candidates,
                staging_dir,
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SFTPサーバから別のSSHサーバへファイルを中継転送します。"
    )
    parser.add_argument("config", type=Path, help="JSON設定ファイル")
    args = parser.parse_args()
    try:
        count = forward_matching_files(load_config(args.config))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    print(f"完了: {count} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
