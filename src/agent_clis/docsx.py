"""Documentation lookup CLI."""

from __future__ import annotations

import argparse
from urllib.parse import urlparse

from .common import html_to_text, main_wrapper, print_json, request_text, truncate
from .searchx import cmd_search as searchx_cmd_search


def cmd_search(args: argparse.Namespace) -> int:
    args.query = f"{args.query} official documentation"
    args.type = "auto"
    return searchx_cmd_search(args)


def cmd_read(args: argparse.Namespace) -> int:
    html = request_text(args.url, headers={"User-Agent": "agent-clis docsx/0.1"})
    text = html_to_text(html)
    parsed = urlparse(args.url)
    if args.format == "json":
        print_json({"url": args.url, "host": parsed.netloc, "text": truncate(text, args.max_chars)})
    else:
        print(f"# {parsed.netloc}")
        print(f"URL: {args.url}")
        print()
        print(truncate(text, args.max_chars if not args.full else 0))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docsx",
        description="Documentation search/read CLI. Search uses Exa via EXA_API_KEY; read fetches a URL directly.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search docs, preferring official sources.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--max-chars", type=int, default=1000)
    search.add_argument("--format", choices=["markdown", "json"], default="markdown")
    search.set_defaults(func=cmd_search)

    read = sub.add_parser("read", help="Read and compact a documentation page URL.")
    read.add_argument("url")
    read.add_argument("--max-chars", type=int, default=4000)
    read.add_argument("--full", action="store_true")
    read.add_argument("--format", choices=["markdown", "json"], default="markdown")
    read.set_defaults(func=cmd_read)
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
