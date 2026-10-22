#!/usr/bin/env python3
"""新規追加ファイルの文字コードと改行ルールを検査し、確認後に修正する。"""

from __future__ import annotations

import argparse
import codecs
import fnmatch
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


RULES_FILE = ".file-format-rules"


@dataclass(frozen=True)
class FileAttributes:
    """1ファイルに適用する文字コードと改行形式。"""

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


def existing_files(root: Path, requested: list[str], changed: bool = False) -> list[Path]:
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

    if changed:
        output = run_git(
            "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", cwd=root, text=False
        )
        paths = []
        for raw_path in bytes(output).split(b"\0"):
            if not raw_path:
                continue
            path = root / os.fsdecode(raw_path)
            if path.is_file():
                paths.append(path)
        return paths

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


def load_rules(root: Path) -> list[tuple[str, FileAttributes]]:
    """独立したルールファイルを読み込む。後勝ちでgitattributesに近い動作にする。"""
    rules_path = root / RULES_FILE
    if not rules_path.is_file():
        return []

    rules: list[tuple[str, FileAttributes]] = []
    for line_number, line in enumerate(rules_path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            fields = shlex.split(stripped, comments=True)
        except ValueError as error:
            raise ValueError(f"{rules_path}:{line_number}: ルールを解釈できません: {error}") from error
        if len(fields) < 2:
            raise ValueError(f"{rules_path}:{line_number}: パターンと属性を指定してください")

        values: dict[str, str] = {}
        for field in fields[1:]:
            try:
                name, value = field.split("=", 1)
            except ValueError:
                raise ValueError(f"{rules_path}:{line_number}: 属性は name=value 形式で指定してください") from None
            if name not in {"encoding", "eol"} or not value:
                raise ValueError(f"{rules_path}:{line_number}: 未対応の属性です: {name}")
            values[name] = value
        if not values:
            raise ValueError(f"{rules_path}:{line_number}: encoding または eol が必要です")
        rules.append((fields[0], FileAttributes(values.get("encoding"), values.get("eol"))))
    return rules


def rule_value(root: Path, path: Path, rules: list[tuple[str, FileAttributes]]) -> FileAttributes:
    """ルールファイルのパターンに一致する最後のルールを返す。"""
    relative = path.relative_to(root).as_posix()
    matched = FileAttributes(None, None)
    for pattern, attributes in rules:
        normalized = pattern.removeprefix("/")
        if fnmatch.fnmatchcase(relative, normalized) or (
            "/" not in normalized and fnmatch.fnmatchcase(path.name, normalized)
        ):
            matched = attributes
    return matched


def codec_name(name: str) -> str:
    """Git属性名をPythonのcodec名に変換し、利用可能か確認する。"""
    aliases = {
        "cp932": "cp932",
        "sjis": "cp932",
        "shift-jis": "cp932",
        "shift_jis": "cp932",
    }
    normalized = aliases.get(name.lower(), name)
    try:
        return codecs.lookup(normalized).name
    except LookupError:
        raise ValueError(f"未対応の文字コード属性です: {name}") from None


def eol_problem(data: bytes, expected: str | None) -> str | None:
    """指定された改行形式に適合しているか確認する。"""
    if expected not in ("lf", "crlf"):
        return None
    current = eol_name(data)
    expected_name = expected.upper()
    return None if current == expected_name else f"改行: 期待 {expected_name} / 現在 {current}"


def eol_name(data: bytes) -> str:
    """バイト列の改行形式を表示用の名前で返す。"""
    has_crlf = b"\r\n" in data
    has_lf = b"\n" in data.replace(b"\r\n", b"")
    has_cr = b"\r" in data.replace(b"\r\n", b"")
    kinds = sum((has_crlf, has_lf, has_cr))
    if kinds == 0:
        return "なし"
    if kinds > 1:
        return "混在"
    if has_crlf:
        return "CRLF"
    if has_lf:
        return "LF"
    return "CR"


def detected_encoding(data: bytes, expected: str) -> str:
    """期待値以外の代表的な文字コードで現在値を推定する。"""
    euc_score = 0
    sjis_score = 0
    for index, value in enumerate(data[:-1]):
        following = data[index + 1]
        if 0xA1 <= value <= 0xFE and 0xA1 <= following <= 0xFE:
            euc_score += 1
        if (0x81 <= value <= 0x9F or 0xE0 <= value <= 0xFC) and (
            0x40 <= following <= 0x7E or 0x80 <= following <= 0xFC
        ):
            sjis_score += 1
    if euc_score > sjis_score and euc_score:
        return "EUC-JP"
    if sjis_score > euc_score and sjis_score:
        return "SJIS"

    candidates = [expected, "utf-8-sig", "utf-8", "cp932", "euc_jp"]
    for candidate in dict.fromkeys(candidates):
        try:
            data.decode(codec_name(candidate))
        except (UnicodeDecodeError, ValueError):
            continue
        return (
            candidate.upper()
            .replace("UTF-8-SIG", "UTF-8(BOM)")
            .replace("CP932", "SJIS")
            .replace("EUC_JP", "EUC-JP")
        )
    return "判定不能"


def inspect_file(path: Path, attributes: FileAttributes) -> Problem | None:
    """1ファイルを検査し、不一致があれば問題を返す。"""
    data = path.read_bytes()
    reasons: list[str] = []

    if attributes.encoding:
        try:
            data.decode(codec_name(attributes.encoding))
        except (UnicodeDecodeError, ValueError) as error:
            current = detected_encoding(data, attributes.encoding)
            reasons.append(f"エンコード: 期待 {attributes.encoding} / 現在 {current}")

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
        description="指定したファイルセット、またはリポジトリ全体の形式ルールを検査します。"
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
    parser.add_argument(
        "--changed",
        action="store_true",
        help="コミットに追加・変更されたファイルだけを検査する",
    )
    return parser.parse_args()


def main() -> int:
    """検査と、ユーザー確認後の修正を実行する。"""
    args = parse_arguments()
    try:
        root = repository_root()
        problems: list[Problem] = []
        checked = 0
        rules = load_rules(root)
        for path in existing_files(root, args.paths, args.changed):
            attributes = rule_value(root, path, rules)
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
