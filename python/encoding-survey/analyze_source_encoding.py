#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

try:
    import chardet
except ImportError:
    print("ERROR: chardet is not installed.", file=sys.stderr)
    print("Install: python -m pip install chardet", file=sys.stderr)
    raise SystemExit(1)


SAMPLE_SIZE = 256 * 1024
CHUNK_SIZE = 1024 * 1024


def detect_utf16(sample: bytes) -> str | None:
    """Detect UTF-16 from its BOM or its typical alternating NUL bytes."""

    if sample.startswith(b"\xff\xfe"):
        return "UTF-16LE"
    if sample.startswith(b"\xfe\xff"):
        return "UTF-16BE"

    # BOM-less UTF-16 is common in source trees.  ASCII-heavy text has a NUL
    # in every other byte; this also prevents chardet from calling it UTF-8.
    if len(sample) < 4:
        return None
    even_nuls = sample[::2].count(b"\x00")
    odd_nuls = sample[1::2].count(b"\x00")
    even_ratio = even_nuls / len(sample[::2])
    odd_ratio = odd_nuls / len(sample[1::2])

    if odd_ratio >= 0.20 and odd_ratio >= even_ratio * 2:
        return "UTF-16LE"
    if even_ratio >= 0.20 and even_ratio >= odd_ratio * 2:
        return "UTF-16BE"
    return None


def count_eol(data: bytes) -> tuple[int, int, int]:
    """Return the number of CRLF, LF, and CR line endings in *data*."""

    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    return crlf, lf, cr


def classify_eol(crlf: int, lf: int, cr: int) -> str:
    """Classify line-ending counts using the tool's public labels."""

    kinds = sum(value > 0 for value in (crlf, lf, cr))

    if kinds == 0:
        return "NONE"
    if kinds > 1:
        return "MIXED"
    if crlf:
        return "CRLF"
    if lf:
        return "LF"
    return "CR"


def detect(path: Path) -> tuple[str, str]:
    """Detect a file's encoding and line-ending style."""
    with path.open("rb") as f:
        sample = f.read(SAMPLE_SIZE)

    if not sample:
        return "EMPTY", "NONE"
    utf16_encoding = detect_utf16(sample)
    if utf16_encoding:
        encoding = utf16_encoding
    elif b"\x00" in sample:
        return "BINARY", "BINARY"
    else:
        encoding = chardet.detect(sample).get("encoding") or "UNKNOWN"

    crlf, lf, cr = count_eol(sample)

    if not (crlf or lf or cr) and len(sample) == SAMPLE_SIZE:
        with path.open("rb") as f:
            f.seek(len(sample))
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                chunk_crlf, chunk_lf, chunk_cr = count_eol(chunk)
                crlf += chunk_crlf
                lf += chunk_lf
                cr += chunk_cr
                if crlf or lf or cr:
                    break

    return encoding, classify_eol(crlf, lf, cr)


def get_group(path: Path) -> tuple[str, str]:
    name = path.name
    if name.startswith(".") and name.count(".") == 1:
        return "filename", name
    if path.suffix:
        return "extension", path.suffix.lower()
    return "filename", name


def normalize_summary_encoding(encoding: str) -> str:
    """Normalize equivalent encodings for summary.csv."""

    if encoding.upper() == "ASCII":
        return "UTF-8"
    return encoding


def survey(
    target: Path,
    output: Path,
    excludes: set[str],
) -> None:
    """Recursively survey files below *target*."""
    output.mkdir(parents=True, exist_ok=True)

    files_csv = output / "files.csv"
    summary_csv = output / "summary.csv"

    summary = Counter()
    total = 0

    with files_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "type", "key", "encoding", "eol"])
        for root, dirs, files in os.walk(target):
            dirs[:] = [directory for directory in dirs
                       if directory not in excludes]
            for filename in files:
                path = Path(root) / filename
                if not path.is_file():
                    continue
                total += 1
                group_type, key = get_group(path)
                try:
                    encoding, eol = detect(path)
                except OSError:
                    encoding = "ERROR"
                    eol = "ERROR"
                writer.writerow([path.relative_to(target).as_posix(),
                                 group_type, key, encoding, eol])
                if encoding not in {"BINARY", "ERROR", "EMPTY"}:
                    summary_encoding = normalize_summary_encoding(encoding)
                    summary[group_type, key, summary_encoding, eol] += 1

    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "encoding", "eol", "count"])
        for (group_type, key, encoding, eol), count in sorted(summary.items()):
            if group_type == "extension":
                key = "*" + key
            writer.writerow([key, encoding, eol, count])

    print(f"Survey completed: {total} files")

    if excludes:
        print("Excluded directories: " + ", ".join(sorted(excludes)))

    print(f"Files   : {files_csv}")
    print(f"Summary : {summary_csv}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fast encoding/EOL survey for SVN -> Git migration."
    )
    parser.add_argument("target", type=Path, help="Target directory to survey.")
    parser.add_argument("-o", "--output", type=Path, default=Path("output"),
                        help="Output directory (default: ./output).")
    parser.add_argument("-e", "--exclude", action="append", default=[],
                        metavar="DIRNAME",
                        help="Directory name to exclude. Can be specified multiple times.")

    args = parser.parse_args()

    target = args.target.resolve()

    if not target.is_dir():
        print(f"ERROR: not a directory: {target}", file=sys.stderr)
        return 1

    survey(target, args.output.resolve(), set(args.exclude))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
