"""Repeatable browser checks."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin

from .common import AgentCliError, LinkExtractor, main_wrapper, request_text


def cmd_screenshot(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    playwright = shutil.which("playwright") or shutil.which("playwright.cmd")
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if playwright:
        command = [playwright, "screenshot", args.url, str(output)]
    elif npx:
        command = [npx, "playwright", "screenshot", args.url, str(output)]
    else:
        raise AgentCliError(
            "npx/playwright was not found on PATH.\n"
            "Install/setup hint: npm install -g playwright && playwright install chromium"
        )
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise AgentCliError(
            "npx/playwright was not found on PATH.\n"
            "Install/setup hint: npm install -g playwright && playwright install chromium"
        ) from exc
    if completed.returncode != 0:
        raise AgentCliError(
            (completed.stderr or completed.stdout).strip()
            + "\nInstall/setup hint: npm install -g playwright && playwright install chromium"
        )
    print(f"Wrote {output}")
    return 0


def cmd_links(args: argparse.Namespace) -> int:
    html = request_text(args.url, headers={"User-Agent": "agent-clis browserx/0.1"})
    parser = LinkExtractor(args.url)
    parser.feed(html)
    seen: set[str] = set()
    count = 0
    for href, text in parser.links:
        absolute = urljoin(args.url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        print(f"- {text or absolute}: {absolute}")
        count += 1
        if count >= args.limit:
            break
    return 0


def cmd_console(_: argparse.Namespace) -> int:
    raise AgentCliError(
        "console checks are planned but not implemented in v1. Use Playwright MCP for exploratory console inspection."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="browserx", description="Repeatable browser checks.")
    sub = parser.add_subparsers(dest="command", required=True)
    shot = sub.add_parser("screenshot")
    shot.add_argument("url")
    shot.add_argument("--out", "--output", dest="output", required=True)
    shot.set_defaults(func=cmd_screenshot)
    links = sub.add_parser("links")
    links.add_argument("url")
    links.add_argument("--limit", type=int, default=100)
    links.set_defaults(func=cmd_links)
    console = sub.add_parser("console")
    console.add_argument("url")
    console.set_defaults(func=cmd_console)
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
