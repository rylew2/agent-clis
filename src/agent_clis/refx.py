"""Ref MCP endpoint wrapper."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import requests

from .common import AgentCliError, cache_json, main_wrapper, print_json, require_env, truncate


REF_MCP_URL = "https://api.ref.tools/mcp"
SEARCH_TOOL = "ref_search_documentation"
READ_TOOL = "ref_read_url"


class RefMcpClient:
    def __init__(self) -> None:
        self.endpoint = os.getenv("REF_MCP_URL", REF_MCP_URL)
        self.api_key = require_env("REF_API_KEY", "Create one at https://ref.tools/keys and add it to .env.")
        self.session_id: str | None = None
        self.next_id = 1

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "x-ref-api-key": self.api_key,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _parse_response(self, response: requests.Response) -> dict[str, Any] | None:
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self.session_id = session_id
        if response.status_code in {202, 204} or not response.text.strip():
            return None
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            messages: list[dict[str, Any]] = []
            for line in response.text.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line.removeprefix("data:").strip()
                if payload and payload != "[DONE]":
                    messages.append(json.loads(payload))
            return messages[-1] if messages else None
        return response.json()

    def request(self, method: str, params: dict[str, Any] | None = None, *, notify: bool = False) -> dict[str, Any] | None:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = self.next_id
            self.next_id += 1
        if params is not None:
            body["params"] = params

        response = requests.post(self.endpoint, headers=self._headers(), json=body, timeout=60)
        if response.status_code >= 400:
            raise AgentCliError(f"Ref MCP {method} failed: HTTP {response.status_code} {response.text[:500]}")
        message = self._parse_response(response)
        if message and message.get("error"):
            raise AgentCliError(f"Ref MCP {method} failed: {message['error']}")
        return message

    def initialize(self) -> None:
        self.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "refx", "version": "0.1.0"},
            },
        )
        self.request("notifications/initialized", notify=True)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        message = self.request("tools/call", {"name": name, "arguments": arguments})
        if not message or "result" not in message:
            raise AgentCliError(f"Ref MCP {name} returned no result.")
        result = message["result"]
        text = extract_mcp_text(result)
        if isinstance(result, dict) and result.get("isError"):
            raise AgentCliError(text or f"Ref MCP tool {name} returned an error.")
        if text.lower().startswith("not enough credits"):
            raise AgentCliError(text)
        return result

    def list_tools(self) -> dict[str, Any]:
        self.initialize()
        message = self.request("tools/list")
        if not message or "result" not in message:
            raise AgentCliError("Ref MCP tools/list returned no result.")
        return message["result"]


def extract_mcp_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        content = value.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return "\n\n".join(parts).strip()
        for key in ("text", "markdown", "result", "message"):
            if isinstance(value.get(key), str):
                return value[key]
    return json.dumps(value, indent=2, ensure_ascii=False)


def cmd_search(args: argparse.Namespace) -> int:
    client = RefMcpClient()
    result = client.call_tool(SEARCH_TOOL, {"query": args.query})
    cache_path = cache_json("refx", args.query, result)
    if args.format == "json":
        print_json(result)
    else:
        print(truncate(extract_mcp_text(result), args.max_chars))
        print()
        print(f"[raw cached: {cache_path}]")
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    client = RefMcpClient()
    result = client.call_tool(READ_TOOL, {"url": args.url})
    cache_path = cache_json("refx", args.url, result)
    if args.format == "json":
        print_json(result)
    else:
        print(truncate(extract_mcp_text(result), args.max_chars if not args.full else 0))
        print()
        print(f"[raw cached: {cache_path}]")
    return 0


def cmd_tools(args: argparse.Namespace) -> int:
    client = RefMcpClient()
    result = client.list_tools()
    if args.format == "json":
        print_json(result)
    else:
        for tool in result.get("tools", []):
            print(f"- {tool.get('name', '(unknown)')}: {tool.get('description', '')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="refx",
        description="Ref documentation lookup CLI using Ref's MCP HTTP endpoint.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search documentation with Ref.")
    search.add_argument("query")
    search.add_argument("--max-chars", type=int, default=4000)
    search.add_argument("--format", choices=["markdown", "json"], default="markdown")
    search.set_defaults(func=cmd_search)

    read = sub.add_parser("read", help="Read a URL with Ref.")
    read.add_argument("url")
    read.add_argument("--max-chars", type=int, default=4000)
    read.add_argument("--full", action="store_true")
    read.add_argument("--format", choices=["markdown", "json"], default="markdown")
    read.set_defaults(func=cmd_read)

    tools = sub.add_parser("tools", help="List Ref MCP tools.")
    tools.add_argument("--format", choices=["markdown", "json"], default="markdown")
    tools.set_defaults(func=cmd_tools)

    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
