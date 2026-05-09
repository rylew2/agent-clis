"""Approximate token counts for saved command output."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from .common import main_wrapper


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    wordish = len(re.findall(r"\S+", text))
    by_chars = math.ceil(len(text) / 4)
    by_words = math.ceil(wordish * 1.3)
    return max(by_chars, by_words)


def measure_text(label: str, text: str) -> dict[str, Any]:
    encoded = text.encode("utf-8")
    return {
        "label": label,
        "bytes": len(encoded),
        "chars": len(text),
        "words": len(re.findall(r"\S+", text)),
        "estimated_tokens": estimate_tokens(text),
    }


def print_markdown(rows: list[dict[str, Any]]) -> None:
    print("| Label | Bytes | Chars | Words | Estimated tokens |")
    print("|---|---:|---:|---:|---:|")
    for row in rows:
        print(
            f"| {row['label']} | {row['bytes']} | {row['chars']} | "
            f"{row['words']} | {row['estimated_tokens']} |"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokensx",
        description="Estimate token counts for text files or stdin.",
    )
    parser.add_argument("paths", nargs="*", help="Files to measure. Reads stdin when omitted.")
    parser.add_argument("-f", "--format", choices=["table", "json"], default="table")
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        rows: list[dict[str, Any]] = []
        if args.paths:
            for raw_path in args.paths:
                path = Path(raw_path)
                rows.append(measure_text(str(path), path.read_text(encoding="utf-8", errors="replace")))
        else:
            rows.append(measure_text("stdin", sys.stdin.read()))

        if args.format == "json":
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            print_markdown(rows)
        return 0

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
