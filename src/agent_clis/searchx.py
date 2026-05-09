"""Compact Exa search/fetch CLI."""

from __future__ import annotations

import argparse
from typing import Any

from .common import AgentCliError, cache_json, main_wrapper, print_json, request_json, require_env, truncate


EXA_BASE = "https://api.exa.ai"


def exa_headers() -> dict[str, str]:
    return {
        "x-api-key": require_env("EXA_API_KEY", "Set it as a user environment variable; do not commit it."),
        "Content-Type": "application/json",
    }


def result_text(result: dict[str, Any]) -> str:
    text = result.get("text")
    if isinstance(text, str):
        return text
    contents = result.get("contents")
    if isinstance(contents, dict):
        value = contents.get("text") or contents.get("summary")
        if isinstance(value, str):
            return value
    highlights = result.get("highlights")
    if isinstance(highlights, list):
        return "\n".join(str(x) for x in highlights)
    return ""


def print_results(data: dict[str, Any], max_chars: int) -> None:
    for idx, result in enumerate(data.get("results", []), start=1):
        title = result.get("title") or "(untitled)"
        url = result.get("url") or result.get("id") or ""
        published = result.get("publishedDate") or result.get("published_date") or ""
        print(f"## {idx}. {title}")
        if url:
            print(f"URL: {url}")
        if published:
            print(f"Published: {published}")
        text = truncate(result_text(result), max_chars)
        if text:
            print()
            print(text)
        print()


def cmd_search(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "query": args.query,
        "numResults": args.limit,
        "contents": {"text": True},
    }
    if args.type:
        payload["type"] = args.type
    data = request_json("POST", f"{EXA_BASE}/search", headers=exa_headers(), payload=payload)
    cache_path = cache_json("searchx", args.query, data)
    if args.format == "json":
        print_json(data)
    else:
        print_results(data, args.max_chars)
        print(f"[raw cached: {cache_path}]")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    payload = {"urls": [args.url], "text": True}
    data = request_json("POST", f"{EXA_BASE}/contents", headers=exa_headers(), payload=payload)
    cache_path = cache_json("searchx", args.url, data)
    if args.format == "json":
        print_json(data)
    else:
        results = data.get("results", [])
        if not results:
            raise AgentCliError("No content returned.")
        print_results({"results": results}, args.max_chars if not args.full else 0)
        print(f"[raw cached: {cache_path}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="searchx", description="Compact Exa web search/fetch CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search the web with Exa.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--max-chars", type=int, default=1200)
    search.add_argument(
        "--type",
        choices=["auto", "neural", "fast", "deep-lite", "deep", "deep-reasoning", "instant"],
        default=None,
    )
    search.add_argument("--format", choices=["markdown", "json"], default="markdown")
    search.set_defaults(func=cmd_search)

    fetch = sub.add_parser("fetch", help="Fetch clean content for a URL with Exa.")
    fetch.add_argument("url")
    fetch.add_argument("--max-chars", type=int, default=4000)
    fetch.add_argument("--full", action="store_true")
    fetch.add_argument("--format", choices=["markdown", "json"], default="markdown")
    fetch.set_defaults(func=cmd_fetch)
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
