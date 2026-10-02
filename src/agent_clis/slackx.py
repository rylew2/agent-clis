"""Read-only Slack message CLI."""

from __future__ import annotations

import argparse
import os
import re
from typing import Any
from urllib.parse import urlparse

from .common import AgentCliError, cache_json, main_wrapper, print_json, request_json, require_env, truncate


SLACK_BASE = "https://slack.com/api"
PERMALINK_RE = re.compile(r"/archives/([^/]+)/p(\d{11,})")
MENTION_RE = re.compile(r"<@([UW][A-Z0-9]+)>")


def slack_token() -> str:
    try:
        return require_env("SLACK_TOKEN", "Or set SLACK_USER_TOKEN / SLACK_BOT_TOKEN.")
    except AgentCliError:
        pass
    for name in ("SLACK_USER_TOKEN", "SLACK_BOT_TOKEN"):
        value = os.getenv(name)
        if value:
            return value
    raise AgentCliError("Missing SLACK_TOKEN, SLACK_USER_TOKEN, or SLACK_BOT_TOKEN.")


def slack_api(method: str, params: dict[str, Any]) -> dict[str, Any]:
    data = request_json(
        "GET",
        f"{SLACK_BASE}/{method}",
        headers={"Authorization": f"Bearer {slack_token()}"},
        params=params,
    )
    if not isinstance(data, dict):
        raise AgentCliError(f"Slack {method} returned an unexpected response.")
    if not data.get("ok"):
        raise AgentCliError(f"Slack {method} failed: {data.get('error', 'unknown_error')}")
    return data


def parse_permalink(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    match = PERMALINK_RE.search(parsed.path)
    if not match:
        raise AgentCliError("Expected a Slack permalink like https://.../archives/C123/p1234567890123456.")
    channel, digits = match.groups()
    return channel, f"{digits[:-6]}.{digits[-6:]}"


def message_author(message: dict[str, Any], users: dict[str, str]) -> str:
    user = message.get("user")
    if isinstance(user, str):
        return users.get(user, user)
    username = message.get("username")
    if isinstance(username, str):
        return username
    bot_id = message.get("bot_id")
    if isinstance(bot_id, str):
        return bot_id
    return "unknown"


def message_text(message: dict[str, Any], users: dict[str, str]) -> str:
    text = str(message.get("text") or "")
    if not users:
        return text
    return MENTION_RE.sub(lambda match: f"@{users.get(match.group(1), match.group(1))}", text)


def collect_user_ids(messages: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for message in messages:
        user = message.get("user")
        if isinstance(user, str):
            ids.add(user)
        for match in MENTION_RE.finditer(str(message.get("text") or "")):
            ids.add(match.group(1))
    return ids


def resolve_users(messages: list[dict[str, Any]]) -> dict[str, str]:
    users: dict[str, str] = {}
    for user_id in sorted(collect_user_ids(messages)):
        try:
            data = slack_api("users.info", {"user": user_id})
        except AgentCliError:
            continue
        user = data.get("user")
        if not isinstance(user, dict):
            continue
        profile = user.get("profile") if isinstance(user.get("profile"), dict) else {}
        name = profile.get("display_name") or profile.get("real_name") or user.get("name") or user_id
        users[user_id] = str(name)
    return users


def fetch_message(channel: str, ts: str) -> dict[str, Any]:
    data = slack_api(
        "conversations.history",
        {
            "channel": channel,
            "latest": ts,
            "inclusive": "true",
            "limit": 1,
        },
    )
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        raise AgentCliError("No Slack message returned for that permalink.")
    message = messages[0]
    if not isinstance(message, dict):
        raise AgentCliError("Slack returned an unexpected message shape.")
    if message.get("ts") != ts:
        raise AgentCliError(f"Slack returned nearest message {message.get('ts')}, not requested {ts}.")
    return message


def fetch_thread(channel: str, ts: str, limit: int) -> list[dict[str, Any]]:
    data = slack_api("conversations.replies", {"channel": channel, "ts": ts, "limit": limit})
    messages = data.get("messages")
    if not isinstance(messages, list):
        raise AgentCliError("Slack returned an unexpected thread shape.")
    return [message for message in messages if isinstance(message, dict)]


def print_messages(messages: list[dict[str, Any]], users: dict[str, str], max_chars: int) -> None:
    for idx, message in enumerate(messages, start=1):
        print(f"## {idx}. {message_author(message, users)} | {message.get('ts', '')}")
        subtype = message.get("subtype")
        if subtype:
            print(f"Subtype: {subtype}")
        text = truncate(message_text(message, users), max_chars)
        if text:
            print()
            print(text)
        files = message.get("files")
        if isinstance(files, list) and files:
            print()
            print("Files:")
            for file in files:
                if isinstance(file, dict):
                    print(f"- {file.get('title') or file.get('name') or file.get('id')}")
        print()


def output_messages(
    *,
    label: str,
    channel: str,
    ts: str,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
) -> int:
    cache_path = cache_json("slackx", label, {"channel": channel, "ts": ts, "messages": messages})
    if args.format == "json":
        print_json({"channel": channel, "ts": ts, "messages": messages, "cache_path": str(cache_path)})
        return 0
    users = resolve_users(messages) if args.resolve_users else {}
    print_messages(messages, users, args.max_chars)
    print(f"[raw cached: {cache_path}]")
    return 0


def cmd_message(args: argparse.Namespace) -> int:
    channel, ts = parse_permalink(args.permalink)
    message = fetch_message(channel, ts)
    return output_messages(
        label=args.permalink,
        channel=channel,
        ts=ts,
        messages=[message],
        args=args,
    )


def cmd_thread(args: argparse.Namespace) -> int:
    channel, ts = parse_permalink(args.permalink)
    messages = fetch_thread(channel, ts, args.limit)
    return output_messages(
        label=args.permalink,
        channel=channel,
        ts=ts,
        messages=messages,
        args=args,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slackx", description="Read-only Slack message CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    message = sub.add_parser("message", help="Fetch one Slack message from a permalink.")
    message.add_argument("permalink")
    message.add_argument("--resolve-users", action="store_true")
    message.add_argument("--max-chars", type=int, default=2000)
    message.add_argument("--format", choices=["markdown", "json"], default="markdown")
    message.set_defaults(func=cmd_message)

    thread = sub.add_parser("thread", help="Fetch a Slack thread from a permalink.")
    thread.add_argument("permalink")
    thread.add_argument("--limit", type=int, default=50)
    thread.add_argument("--resolve-users", action="store_true")
    thread.add_argument("--max-chars", type=int, default=2000)
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
