"""Read-only X thread export using an isolated gallery-dl configuration."""

from __future__ import annotations

import argparse
import datetime as dt
import http.cookiejar
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from .common import AgentCliError, cache_dir, configure_stdio


def backend_python() -> Path:
    root = Path.home() / ".local" / "share" / "agent-clis" / "twitterx" / "venv"
    return root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def normalize_url(value: str) -> tuple[str, str]:
    if re.fullmatch(r"[0-9]{1,25}", value):
        return f"https://x.com/i/web/status/{value}", value
    parsed = urlsplit(value)
    if (parsed.scheme not in ("http", "https") or parsed.hostname not in
            ("x.com", "www.x.com", "twitter.com", "www.twitter.com") or
            parsed.username or parsed.password or parsed.port not in (None, 80, 443)):
        raise AgentCliError("Use an x.com/twitter.com tweet URL or numeric tweet ID.")
    match = re.fullmatch(r"/(?:[A-Za-z0-9_]+|i/web)/status/([0-9]{1,25})(?:/(?:photo|video)/[0-9]+)?/?", parsed.path)
    if not match:
        raise AgentCliError("Expected a tweet URL containing /status/ID.")
    tweet_id = match[1]
    return f"https://x.com/i/web/status/{tweet_id}", tweet_id


def make_config(output: Path, conversation: bool, media: bool) -> dict:
    return {
        "extractor": {
            "base-directory": str(output), "directory": ["media"],
            "filename": "{tweet_id}_{num}.{extension}",
            "children": False, "parent": False, "netrc": False,
            "download": media, "retries": 2, "timeout": 30,
            "cookies-update": False, "proxy-env": False,
            "twitter": {
                "conversations": conversation, "text-tweets": True,
                "videos": True, "quoted": False, "cards": False,
                "twitpic": False, "articles": ["meta", "cover", "media"],
                "ratelimit": "abort", "cookies": None,
                "postprocessors": [{
                    "name": "metadata", "mode": "json", "event": "post",
                    "base-directory": str(output), "directory": ["raw"],
                    "filename": "{tweet_id}.json",
                }],
            },
        },
        "cache": {"file": ":memory:"},
        "output": {"mode": "null", "log": {"level": "error"}},
    }


def filter_cookie_file(source: Path, destination: Path) -> None:
    jar = http.cookiejar.MozillaCookieJar(str(source))
    jar.load(ignore_discard=True)
    filtered = http.cookiejar.MozillaCookieJar(str(destination))
    for cookie in jar:
        if cookie.domain in ("x.com", ".x.com") and cookie.name in ("auth_token", "ct0"):
            filtered.set_cookie(cookie)
    if not any(cookie.name == "auth_token" for cookie in filtered):
        raise AgentCliError("Cookie file contains no unexpired x.com auth_token.")
    filtered.save(ignore_discard=True)


def build_command(args: argparse.Namespace, url: str, config: Path, cookies: Path | None = None) -> list[str]:
    command = [str(backend_python()), "-I", "-m", "gallery_dl", "--config-ignore", "-c", str(config),
               "--post-range", f"1-{args.limit}"]
    if args.browser:
        spec = f"{args.browser}/x.com"
        if args.profile:
            spec += f":{args.profile}"
        command += ["--cookies-from-browser", spec]
    elif cookies:
        command += ["--cookies", str(cookies)]
    command += [url]
    return command


def collect_posts(output: Path) -> list[dict]:
    posts = []
    for path in sorted((output / "raw").glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        tweet_id = str(raw["tweet_id"])
        if not re.fullmatch(r"[0-9]+", tweet_id):
            raise AgentCliError("Unexpected tweet ID in metadata.")
        author = raw.get("author") or {}
        media = sorted(p.relative_to(output).as_posix()
                       for p in (output / "media").glob(f"{tweet_id}_*") if p.is_file())
        posts.append({
            "id": tweet_id, "url": f"https://x.com/i/web/status/{tweet_id}",
            "author": author.get("name", ""), "name": author.get("nick", ""),
            "date": raw.get("date"), "text": raw.get("content", ""),
            "reply_to": str(raw.get("reply_id") or ""),
            "conversation_id": str(raw.get("conversation_id") or ""),
            "media_count": raw.get("count", 0), "media": media,
            "article": raw.get("article"),
            "metadata_file": path.relative_to(output).as_posix(),
        })
    return sorted(posts, key=lambda p: int(p["id"]))


def render_markdown(data: dict) -> str:
    lines = ["# X thread export", "", f"Source: {data['source_url']}", "",
             "Includes the tweets and replies returned by X. Deleted, hidden, or inaccessible posts may be absent.", "",
             f"Posts: {len(data['posts'])}; retrieval status: {data['status']}; configured limit: {data['limit']}.", ""]
    for post in data["posts"]:
        lines += [f"## @{post['author']} — {post['date'] or post['id']}", "",
                  post["url"], "", post["text"], ""]
        if post.get("article"):
            lines += ["Article metadata: " + json.dumps(post["article"], ensure_ascii=False), ""]
        for media in post["media"]:
            if Path(media).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                lines.append(f"![Attached media]({media})")
            else:
                lines.append(f"[Attached media]({media})")
        lines.append("")
    return "\n".join(lines)


def export(args: argparse.Namespace) -> int:
    url, tweet_id = normalize_url(args.url)
    if not backend_python().is_file():
        raise AgentCliError("Missing isolated gallery-dl backend. See docs/TWITTERX.md for installation.")
    version_result = subprocess.run([str(backend_python()), "-I", "-m", "gallery_dl", "--version"],
                                    capture_output=True, text=True, timeout=30, check=False)
    if version_result.returncode:
        raise AgentCliError("Isolated gallery-dl backend failed its version check.")
    version = version_result.stdout.strip()
    if args.profile and not args.browser:
        raise AgentCliError("--profile requires --browser.")
    if args.cookies and not args.cookies.is_file():
        raise AgentCliError("Cookie file does not exist.")
    output = args.output or cache_dir("twitterx") / f"{tweet_id}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    output = output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise AgentCliError("Output must be a new or empty directory to avoid mixing exports.")
    output.mkdir(parents=True, exist_ok=True)
    config = make_config(output, args.command == "thread", not args.no_media)
    status = "retrieved"
    reason = None
    with tempfile.TemporaryDirectory(prefix="twitterx-") as temporary:
        config_path = Path(temporary) / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        cookies = None
        if args.cookies:
            cookies = Path(temporary) / "x-cookies.txt"
            filter_cookie_file(args.cookies, cookies)
        try:
            # Fixed argument list, no shell. Raw stderr is withheld: upstream errors
            # can contain credentials or remote content.
            result = subprocess.run(build_command(args, url, config_path, cookies),
                                    capture_output=True, timeout=args.timeout, check=False)
            if result.returncode:
                status, reason = "partial", f"gallery-dl exited with code {result.returncode}"
        except subprocess.TimeoutExpired:
            status, reason = "partial", f"retrieval exceeded {args.timeout} seconds"
    posts = collect_posts(output)
    if not posts:
        raise AgentCliError("No posts retrieved. X may require login; use --browser firefox (or --cookies FILE). Chrome on Windows may prevent cookie decryption. The URL may also be inaccessible.")
    if args.command == "thread" and len(posts) >= args.limit and status == "retrieved":
        status = "limit-reached"
    data = {
        "source_url": url, "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "backend": f"gallery-dl {version}", "status": status, "reason": reason,
        "limit": args.limit, "media_requested": not args.no_media, "posts": posts,
    }
    (output / "thread.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "thread.md").write_text(render_markdown(data), encoding="utf-8")
    media_count = sum(len(p["media"]) for p in posts)
    summary = {"output": str(output), "posts": len(posts), "media_files": media_count,
               "status": status, "reason": reason}
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Saved {len(posts)} posts and {media_count} media files to {output}\nStatus: {status}")
        if reason:
            print(reason, file=sys.stderr)
    return 1 if status == "partial" else 0


def positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="twitterx", description="Export X/Twitter text and media. Read-only; ignores gallery-dl ambient configuration.")
    parser.add_argument("--version", action="version", version="twitterx 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("thread", "Export a conversation, including replies."), ("read", "Export a single tweet.")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("url", help="Tweet URL or numeric ID.")
        command.add_argument("-o", "--output", type=Path, help="New/empty output directory; default: local twitterx cache.")
        auth = command.add_mutually_exclusive_group()
        auth.add_argument("--browser", choices=("firefox", "chrome", "edge", "brave"), help="Explicitly read only x.com cookies from this browser.")
        auth.add_argument("--cookies", type=Path, help="Your Netscape-format cookie file; never copied into exports.")
        command.add_argument("--profile", help="Browser profile name or path.")
        command.add_argument("--no-media", action="store_true", help="Export text/metadata without downloading media.")
        command.add_argument("--limit", type=positive_int, default=200, help="Maximum posts (default: 200).")
        command.add_argument("--timeout", type=positive_int, default=300, help="Overall timeout in seconds (default: 300).")
        command.add_argument("--json", action="store_true", help="Print a compact JSON summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        return export(args)
    except http.cookiejar.LoadError:
        print("twitterx: Cookie file must use Netscape format.", file=sys.stderr)
        return 1
    except (AgentCliError, OSError, ValueError) as exc:
        print(f"twitterx: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
