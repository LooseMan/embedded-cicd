#!/usr/bin/env python3
"""ローカル直下のファイルをSFTPサーバへアップロードする。"""

from __future__ import annotations

import argparse
import posixpath
import sys
from pathlib import Path

from transfer_common import (
    ServerConfig,
    SftpSession,
    file_mode,
    find_local_files,
    get_filename_pattern,
    load_config,
)


def upload_matching_files(config: dict[str, object]) -> int:
    local_dir = Path(config["local_dir"])
    server = ServerConfig.from_dict(config, "sftp_server")
    candidates = find_local_files(local_dir, get_filename_pattern(config))
    uploaded_count = 0

    with SftpSession(server) as sftp:
        for local_path in candidates:
            remote_path = posixpath.join(server.remote_dir, local_path.name)
            mode = file_mode(local_path.stat())
            sftp.put(str(local_path), remote_path, confirm=True)
            sftp.chmod(remote_path, mode)
            print(f"uploaded: {local_path} -> {remote_path} (mode={mode:04o})")
            uploaded_count += 1
    return uploaded_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ローカル直下のファイルをSFTPへアップロードします。"
    )
    parser.add_argument("config", type=Path, help="JSON設定ファイル")
    args = parser.parse_args()
    try:
        count = upload_matching_files(load_config(args.config))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    print(f"完了: {count} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
