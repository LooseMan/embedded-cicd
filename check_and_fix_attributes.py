#!/usr/bin/env python3
""".gitattributesの文字コードと改行指定を検査し、確認後に修正する。"""

from __future__ import annotations

import argparse
import codecs
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileAttributes:
    """1ファイルに対してGitが返した属性。"""

    encoding: str | None
    eol: str | None


@dataclass
class Problem:
    """修正対象ファイルと検出理由。"""

    path: Path
    attributes: FileAttributes
    reasons: list[str]


def run_git(*arguments: str, cwd: Path, text: bool = True) -> str | bytes:
    """Gitコマンドを実行し、失敗時は内容を表示して終了する。"""
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=text,
        )
    except FileNotFoundError:
        raise RuntimeError("gitコマンドが見つかりません。") from None
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() if isinstance(error.stderr, str) else ""
        raise RuntimeError(f"Gitコマンドに失敗しました: {detail}") from error
    return result.stdout


def repository_root() -> Path:
    """実行場所に関係なくリポジトリのルートを取得する。"""
    root = run_git("rev-parse", "--show-toplevel", cwd=Path.cwd())
    return Path(str(root).strip()).resolve()


def existing_files(root: Path, requested: list[str]) -> list[Path]:
    """指定ファイル、または追跡済み・未追跡（無視対象を除く）を列挙する。"""
    if requested:
        paths: set[Path] = set()
        for value in requested:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            candidate = candidate.resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                raise RuntimeError(f"リポジトリ外のパスは指定できません: {value}") from None
            if candidate == root / ".git" or (root / ".git") in candidate.parents:
                raise RuntimeError(f".git配下は指定できません: {value}")
            if candidate.is_file():
                paths.add(candidate)
            elif candidate.is_dir():
                paths.update(path for path in candidate.rglob("*") if path.is_file())
            else:
                raise RuntimeError(f"ファイルまたはディレクトリが見つかりません: {value}")
        return sorted(paths)

    output = run_git(
        "ls-files", "--cached", "--others", "--exclude-standard", "-z", cwd=root, text=False
    )
    paths: list[Path] = []
    for raw_path in bytes(output).split(b"\0"):
        if not raw_path:
            continue
        path = root / os.fsdecode(raw_path)
        if path.is_file():
            paths.append(path)
    return paths


def attribute_value(root: Path, path: Path) -> FileAttributes:
    """Gitの実効属性を取得する。通常のglob解釈はGitに任せる。"""
    relative = path.relative_to(root).as_posix()
    output = str(run_git("check-attr", "working-tree-encoding", "eol", "--", relative, cwd=root))
    values: dict[str, str] = {}
    for line in output.splitlines():
        _, name, value = line.rsplit(": ", 2)
        values[name] = value

    def configured(name: str) -> str | None:
        value = values.get(name)
        return None if value in (None, "unspecified", "unset") else value

    return FileAttributes(configured("working-tree-encoding"), configured("eol"))


def codec_name(name: str) -> str:
    """Git属性名をPythonのcodec名に変換し、利用可能か確認する。"""
    aliases = {"cp932": "cp932", "shift-jis": "cp932", "shift_jis": "cp932"}
    normalized = aliases.get(name.lower(), name)
    try:
        return codecs.lookup(normalized).name
    except LookupError:
        raise ValueError(f"未対応の文字コード属性です: {name}") from None


def eol_problem(data: bytes, expected: str | None) -> str | None:
    """指定された改行形式に適合しているか確認する。"""
    if expected not in ("lf", "crlf"):
        return None
    if expected == "lf":
        if b"\r" in data:
            return "LF指定ですがCRを含んでいます"
    elif b"\n" in data.replace(b"\r\n", b"") or b"\r" in data.replace(b"\r\n", b""):
        return "CRLF指定ですが単独の改行コードを含んでいます"
    return None


def inspect_file(path: Path, attributes: FileAttributes) -> Problem | None:
    """1ファイルを検査し、不一致があれば問題を返す。"""
    data = path.read_bytes()
    reasons: list[str] = []

    if attributes.encoding:
        try:
            data.decode(codec_name(attributes.encoding))
        except (UnicodeDecodeError, ValueError) as error:
            reasons.append(f"文字コード不一致（{attributes.encoding}: {error}）")

    line_reason = eol_problem(data, attributes.eol)
    if line_reason:
        reasons.append(line_reason)

    return Problem(path, attributes, reasons) if reasons else None


def decode_for_fix(data: bytes, target_encoding: str) -> str:
    """修正前の文字列を安全に推定する。推測できない場合は修正しない。"""
    target = codec_name(target_encoding)
    candidates = ["utf-8-sig", "utf-8", target, "euc_jp"]
    for candidate in dict.fromkeys(candidates):
        try:
            return data.decode(candidate)
        except UnicodeDecodeError:
            continue
    raise UnicodeError("入力ファイルの文字コードを安全に判定できません")


def fixed_bytes(path: Path, attributes: FileAttributes) -> bytes:
    """指定属性に合わせたバイト列を作成する。"""
    original = path.read_bytes()
    if attributes.encoding:
        text = decode_for_fix(original, attributes.encoding)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if attributes.eol == "crlf":
            text = text.replace("\n", "\r\n")
        return text.encode(codec_name(attributes.encoding))

    # 文字コード指定がない場合は、改行だけをバイト列として変換する。
    normalized = original.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return normalized.replace(b"\n", b"\r\n") if attributes.eol == "crlf" else normalized


def fix_file(problem: Problem) -> None:
    """修正結果を一時ファイル経由で安全に置き換える。"""
    replacement = fixed_bytes(problem.path, problem.attributes)
    temporary = problem.path.with_name(f".{problem.path.name}.attribute-check.tmp")
    try:
        temporary.write_bytes(replacement)
        os.replace(temporary, problem.path)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser(
        description="指定したファイルセット、またはリポジトリ全体の属性を検査します。"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="検査対象のファイルまたはディレクトリ（省略時は未無視ファイルを全件検査）",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="不一致を表示するだけで、修正確認を行わない",
    )
    return parser.parse_args()


def main() -> int:
    """検査と、ユーザー確認後の修正を実行する。"""
    args = parse_arguments()
    try:
        root = repository_root()
        problems: list[Problem] = []
        checked = 0
        for path in existing_files(root, args.paths):
            attributes = attribute_value(root, path)
            if not attributes.encoding and not attributes.eol:
                continue
            checked += 1
            problem = inspect_file(path, attributes)
            if problem:
                problems.append(problem)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 2

    print(f"検査対象: {checked}ファイル")
    if not problems:
        print("不一致はありません。")
        return 0

    print(f"不一致: {len(problems)}ファイル")
    for problem in problems:
        relative = problem.path.relative_to(root)
        print(f"- {relative}: {'; '.join(problem.reasons)}")

    if args.check_only:
        print("--check-only指定のため修正しません。")
        return 1

    answer = input("上記ファイルを修正しますか？ [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("修正をキャンセルしました。")
        return 1

    failed = 0
    for problem in problems:
        try:
            fix_file(problem)
            print(f"修正しました: {problem.path.relative_to(root)}")
        except (OSError, UnicodeError, ValueError) as error:
            failed += 1
            print(f"修正失敗: {problem.path.relative_to(root)}: {error}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
