"""Read-only Reddit research CLI.

Reads public old.reddit.com pages and parses the long-stable markup.
Access is rate-limited per IP: space repeated calls a few seconds apart.
"""

from __future__ import annotations

import argparse
import os
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit

import requests

from .common import AgentCliError, cache_json, clean_ws, main_wrapper, print_json, truncate

OLD_REDDIT = "https://old.reddit.com"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
RETRY_DELAYS = [5, 10]


def headers() -> dict[str, str]:
    return {"User-Agent": os.getenv("REDDIT_USER_AGENT", BROWSER_UA)}


def fetch_html(url: str, params: dict | None = None) -> str:
    for attempt, delay in enumerate([0, *RETRY_DELAYS]):
        if delay:
            time.sleep(delay)
        response = requests.get(url, headers=headers(), params=params, timeout=30)
        if response.status_code == 429 and attempt < len(RETRY_DELAYS):
            continue
        if response.status_code == 429:
            raise AgentCliError(
                f"GET {url} rate-limited (HTTP 429) after retries. "
                "Unauthenticated Reddit access is throttled per IP; wait ~30s and retry."
            )
        if response.status_code >= 400:
            raise AgentCliError(
                f"GET {url} failed: HTTP {response.status_code}. "
                "Reddit may be blocking this network; retry later or set REDDIT_USER_AGENT."
            )
        return response.text
    raise AgentCliError(f"GET {url} failed.")


def old_reddit_url(url: str) -> str:
    """Convert a reddit.com thread URL (or bare path) to an old.reddit.com URL."""
    parts = urlsplit(url)
    path = (parts.path or url).split("?")[0].rstrip("/")
    if path.endswith(".json"):
        path = path[: -len(".json")]
    if not path.startswith("/"):
        path = "/" + path
    return OLD_REDDIT + path


class SearchResultParser(HTMLParser):
    """Extract post results from an old.reddit.com search page."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._depth = 0
        self._capture: str | None = None
        self._capture_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class") or ""
        if tag == "div" and "search-result-link" in cls:
            self._current = {
                "title": "",
                "url": "",
                "subreddit": "",
                "score": "",
                "comments": "",
                "preview": "",
            }
            self._depth = 1
            return
        if self._current is None:
            return
        if tag == "div":
            self._depth += 1
            if "search-result-body" in cls:
                self._capture = "preview"
                self._capture_depth = self._depth
        elif tag == "a":
            if "search-title" in cls:
                self._current["url"] = attrs_dict.get("href") or ""
                self._capture = "title"
            elif "search-subreddit-link" in cls:
                self._capture = "subreddit"
            elif "search-comments" in cls:
                self._capture = "comments"
        elif tag == "span" and "search-score" in cls:
            self._capture = "score"

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag == "div":
            if self._capture == "preview" and self._depth == self._capture_depth:
                self._capture = None
            self._depth -= 1
            if self._depth <= 0:
                self.results.append({k: clean_ws(v) for k, v in self._current.items()})
                self._current = None
        elif tag in {"a", "span"} and self._capture != "preview":
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._capture:
            self._current[self._capture] += data


class ThreadParser(HTMLParser):
    """Extract the post and comments from an old.reddit.com thread page."""

    def __init__(self) -> None:
        super().__init__()
        self.post: dict[str, str] = {"title": "", "subreddit": "", "score": "", "selftext": ""}
        self.comments: list[dict[str, str]] = []
        self._things: list[dict[str, str]] = []
        self._capture: str | None = None
        self._capture_depth = 0
        self._div_depth = 0
        self._title_pending = False

    def _current_thing(self) -> dict[str, str] | None:
        return self._things[-1] if self._things else None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class") or ""
        if tag == "div":
            self._div_depth += 1
            if "thing" in cls.split() or " thing " in f" {cls} ":
                if "comment" in cls:
                    thing = {
                        "kind": "comment",
                        "author": attrs_dict.get("data-author") or "",
                        "permalink": attrs_dict.get("data-permalink") or "",
                        "score": "",
                        "body": "",
                    }
                elif "link" in cls or "self" in cls:
                    thing = {"kind": "post"}
                    self.post["subreddit"] = attrs_dict.get("data-subreddit") or ""
                else:
                    return
                thing["_depth"] = self._div_depth
                self._things.append(thing)
            elif "usertext-body" in cls and self._things:
                self._capture = "body"
                self._capture_depth = self._div_depth
            elif "score" in cls.split() and self._things and self._current_thing().get("kind") == "post":
                if "unvoted" in cls:
                    self._capture = "post_score"
                    self._capture_depth = self._div_depth
        elif tag == "a" and "title" in cls.split() and not self.post["title"]:
            self._title_pending = True
        elif tag == "span" and "score" in cls.split() and "unvoted" in cls:
            thing = self._current_thing()
            if thing is not None and thing.get("kind") == "comment" and not thing["score"]:
                self._capture = "comment_score"
                self._capture_depth = self._div_depth

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._capture == "comment_score":
            self._capture = None
        elif tag == "a":
            self._title_pending = False
        elif tag == "div":
            if self._capture in {"body", "post_score"} and self._div_depth == self._capture_depth:
                self._capture = None
            thing = self._current_thing()
            if thing is not None and self._div_depth == thing["_depth"]:
                self._things.pop()
                if thing["kind"] == "comment":
                    del thing["_depth"]
                    thing["body"] = clean_ws(thing["body"])
                    thing["score"] = clean_ws(thing["score"])
                    self.comments.append(thing)
            self._div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._title_pending:
            self.post["title"] += data
            return
        if not self._capture:
            return
        thing = self._current_thing()
        if self._capture == "body" and thing is not None:
            if thing["kind"] == "comment":
                thing["body"] += data
            else:
                self.post["selftext"] += data
        elif self._capture == "post_score":
            self.post["score"] += data
        elif self._capture == "comment_score" and thing is not None:
            thing["score"] += data


def cmd_search(args: argparse.Namespace) -> int:
    if args.subreddit:
        url = f"{OLD_REDDIT}/r/{args.subreddit}/search"
        params = {"q": args.query, "restrict_sr": "on", "sort": args.sort, "limit": args.limit}
    else:
        url = f"{OLD_REDDIT}/search"
        params = {"q": args.query, "sort": args.sort, "limit": args.limit}
    html = fetch_html(url, params)
    parser = SearchResultParser()
    parser.feed(html)
    results = parser.results[: args.limit]
    for item in results:
        item["url"] = item["url"].replace("https://old.reddit.com", "https://www.reddit.com")
    cache_path = cache_json("redditx", args.query, results)
    if args.format == "json":
        print_json(results)
        return 0
    if not results:
        print("No post results. (Reddit may have served a challenge page; retry in ~30s.)")
    for idx, item in enumerate(results, start=1):
        print(f"## {idx}. {item['title']}")
        print(f"URL: {item['url']}")
        print(f"{item['subreddit']} | {item['score'] or '? points'} | {item['comments'] or '? comments'}")
        preview = truncate(item["preview"], args.max_chars)
        if preview:
            print()
            print(preview)
        print()
    print(f"[raw cached: {cache_path}]")
    return 0


def cmd_thread(args: argparse.Namespace) -> int:
    url = old_reddit_url(args.url)
    html = fetch_html(url, {"limit": max(args.top, 20)})
    parser = ThreadParser()
    parser.feed(html)
    data = {"post": {k: clean_ws(v) for k, v in parser.post.items()}, "comments": parser.comments}
    cache_path = cache_json("redditx", url, data)
    if args.format == "json":
        print_json(data)
        return 0
    post = data["post"]
    if not post["title"]:
        raise AgentCliError("Could not parse thread page (Reddit may have served a challenge page; retry in ~30s).")
    print(f"# {post['title']}")
    print(f"URL: {url.replace('https://old.reddit.com', 'https://www.reddit.com')}")
    print(f"r/{post['subreddit']} | score: {post['score'] or '?'}")
    body = truncate(post["selftext"], args.max_chars)
    if body:
        print()
        print(body)
    print()
    for idx, comment in enumerate(data["comments"][: args.top], start=1):
        print(f"## Comment {idx} | {comment['score'] or 'score ?'} | u/{comment['author']}")
        print(truncate(comment["body"], args.max_chars))
        print()
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
