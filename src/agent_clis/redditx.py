"""Read-only Reddit research CLI."""

from __future__ import annotations

import argparse
import os
from urllib.parse import quote_plus

from .common import AgentCliError, cache_json, main_wrapper, print_json, request_json, truncate


def headers() -> dict[str, str]:
    return {"User-Agent": os.getenv("REDDIT_USER_AGENT", "agent-clis/0.1 read-only research")}


def reddit_json_url(url: str) -> str:
    clean = url.split("?")[0].rstrip("/")
    if clean.endswith(".json"):
        return clean
    return clean + ".json"


def cmd_search(args: argparse.Namespace) -> int:
    if args.subreddit:
        url = f"https://www.reddit.com/r/{args.subreddit}/search.json"
        params = {"q": args.query, "restrict_sr": "1", "limit": args.limit, "sort": args.sort}
    else:
        url = "https://www.reddit.com/search.json"
        params = {"q": args.query, "limit": args.limit, "sort": args.sort}
    data = request_json("GET", url, headers=headers(), params=params)
    cache_path = cache_json("redditx", args.query, data)
    if args.format == "json":
        print_json(data)
    else:
        children = data.get("data", {}).get("children", [])
        for idx, child in enumerate(children, start=1):
            item = child.get("data", {})
            print(f"## {idx}. {item.get('title', '(untitled)')}")
            print(f"URL: https://www.reddit.com{item.get('permalink', '')}")
            print(f"Subreddit: r/{item.get('subreddit', '')} | score: {item.get('score', 0)} | comments: {item.get('num_comments', 0)}")
            text = truncate(item.get("selftext", ""), args.max_chars)
            if text:
                print()
                print(text)
            print()
        print(f"[raw cached: {cache_path}]")
    return 0


def cmd_thread(args: argparse.Namespace) -> int:
    url = reddit_json_url(args.url)
    data = request_json("GET", url, headers=headers())
    cache_path = cache_json("redditx", url, data)
    if args.format == "json":
        print_json(data)
        return 0
    if not isinstance(data, list) or len(data) < 2:
        raise AgentCliError("Unexpected Reddit thread JSON shape.")
    post = data[0]["data"]["children"][0]["data"]
    print(f"# {post.get('title', '(untitled)')}")
    print(f"URL: https://www.reddit.com{post.get('permalink', '')}")
    print(f"Subreddit: r/{post.get('subreddit', '')} | score: {post.get('score', 0)} | comments: {post.get('num_comments', 0)}")
    body = truncate(post.get("selftext", ""), args.max_chars)
    if body:
        print()
        print(body)
    print()
    comments = data[1]["data"]["children"]
    printed = 0
    for child in comments:
        if child.get("kind") != "t1":
            continue
        item = child.get("data", {})
        print(f"## Comment {printed + 1} | score: {item.get('score', 0)} | u/{item.get('author', '')}")
        print(truncate(item.get("body", ""), args.max_chars))
        print()
        printed += 1
        if printed >= args.top:
            break
    print(f"[raw cached: {cache_path}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="redditx", description="Read-only Reddit research CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search Reddit.")
    search.add_argument("query")
    search.add_argument("--subreddit")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--sort", choices=["relevance", "hot", "top", "new", "comments"], default="relevance")
    search.add_argument("--max-chars", type=int, default=800)
    search.add_argument("--format", choices=["markdown", "json"], default="markdown")
    search.set_defaults(func=cmd_search)

    thread = sub.add_parser("thread", help="Fetch a Reddit thread.")
    thread.add_argument("url")
    thread.add_argument("--top", type=int, default=20)
    thread.add_argument("--max-chars", type=int, default=1200)
    thread.add_argument("--format", choices=["markdown", "json"], default="markdown")
    thread.set_defaults(func=cmd_thread)
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
