"""Shared helpers for agent CLIs."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests


DEFAULT_TIMEOUT = 30

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


class AgentCliError(RuntimeError):
    """Expected CLI error with a clean message."""


def require_env(name: str, help_text: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    extra = f" {help_text}" if help_text else ""
    raise AgentCliError(f"Missing {name}.{extra}")


def cache_dir(tool: str) -> Path:
    base = Path(os.getenv("AGENT_CLIS_CACHE", Path.home() / ".cache" / "agent-clis"))
    path = base / tool
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_json(tool: str, label: str, data: Any) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:12]
    path = cache_dir(tool) / f"{stamp}-{digest}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars].rstrip() + f"\n\n[truncated {omitted} chars]"


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def clean_ws(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    response = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise AgentCliError(f"{method} {url} failed: HTTP {response.status_code} {response.text[:500]}")
    return response.json()


def request_text(url: str, *, headers: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    response = requests.get(url, headers=headers, timeout=timeout)
    if response.status_code >= 400:
        raise AgentCliError(f"GET {url} failed: HTTP {response.status_code} {response.text[:500]}")
    return response.text


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_stack.append(tag)
        if tag in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_stack:
            self.parts.append(data)

    def text(self) -> str:
        return clean_ws("".join(self.parts))


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href:
            self.links.append((self._current_href, clean_ws(" ".join(self._current_text))))
            self._current_href = None
            self._current_text = []


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()


def main_wrapper(func) -> int:
    try:
        return func()
    except AgentCliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
