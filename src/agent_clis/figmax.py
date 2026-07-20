"""Read-only Figma REST API CLI."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from .common import (
    AgentCliError,
    DEFAULT_TIMEOUT,
    cache_dir,
    cache_json,
    main_wrapper,
    print_json,
    request_json,
    require_env,
    truncate,
)


FIGMA_BASE = "https://api.figma.com"

SUMMARY_NODE_TYPES = {
    "CANVAS",
    "FRAME",
    "COMPONENT",
    "COMPONENT_SET",
    "INSTANCE",
    "SECTION",
    "GROUP",
}


def figma_headers() -> dict[str, str]:
    token = require_env(
        "FIGMA_TOKEN",
        "Create a personal access token in Figma (Settings > Security) and set it as an environment variable.",
    )
    return {"X-Figma-Token": token}


def parse_file_ref(ref: str) -> tuple[str, str | None]:
    """Return (file_key, node_id) from a Figma URL or bare file key."""
    if "figma.com" not in ref:
        return ref, None
    parsed = urlparse(ref)
    match = re.match(r"^/(?:file|design|board|proto|slides)/([A-Za-z0-9]+)", parsed.path)
    if not match:
        raise AgentCliError(f"Could not parse a file key from URL: {ref}")
    node_id = None
    values = parse_qs(parsed.query).get("node-id")
    if values:
        node_id = normalize_node_id(values[0])
    return match.group(1), node_id


def normalize_node_id(node_id: str) -> str:
    """Convert URL-style node ids like 1-23 to API-style 1:23."""
    if ":" not in node_id and re.fullmatch(r"\d+-\d+", node_id):
        return node_id.replace("-", ":")
    return node_id


def resolve_node_ids(args: argparse.Namespace, url_node_id: str | None) -> str:
    if args.id:
        return ",".join(normalize_node_id(i.strip()) for i in args.id.split(","))
    if url_node_id:
        return url_node_id
    raise AgentCliError("No node id given. Pass --id or use a URL with a node-id parameter.")


def describe_node(node: dict[str, Any]) -> str:
    parts = [f"{node.get('name', '(unnamed)')} [{node.get('type', '?')}] id={node.get('id', '?')}"]
    box = node.get("absoluteBoundingBox")
    if isinstance(box, dict) and box.get("width") is not None:
        parts.append(f"{round(box['width'])}x{round(box['height'])}")
    text = node.get("characters")
    if isinstance(text, str) and text:
        snippet = text if len(text) <= 80 else text[:80].rstrip() + "..."
        parts.append(f'text="{snippet}"')
    return " ".join(parts)


def print_tree(node: dict[str, Any], indent: int, max_depth: int, all_types: bool) -> None:
    if node.get("type") in SUMMARY_NODE_TYPES or all_types or indent == 0:
        print("  " * indent + describe_node(node))
    if max_depth and indent >= max_depth:
        return
    for child in node.get("children", []) or []:
        print_tree(child, indent + 1, max_depth, all_types)


def cmd_file(args: argparse.Namespace) -> int:
    file_key, _ = parse_file_ref(args.file)
    params: dict[str, Any] = {"depth": args.depth}
    data = request_json(
        "GET", f"{FIGMA_BASE}/v1/files/{file_key}", headers=figma_headers(), params=params
    )
    cache_path = cache_json("figmax", file_key, data)
    if args.format == "json":
        print_json(data)
        return 0
    print(f"# {data.get('name', '(unnamed file)')}")
    print(f"Key: {file_key}")
    print(f"Last modified: {data.get('lastModified', '?')}  Editor: {data.get('editorType', '?')}")
    print()
    print_tree(data.get("document", {}), 0, 0, args.all_nodes)
    print()
    print(f"[raw cached: {cache_path}]")
    return 0


def cmd_node(args: argparse.Namespace) -> int:
    file_key, url_node_id = parse_file_ref(args.file)
    ids = resolve_node_ids(args, url_node_id)
    params: dict[str, Any] = {"ids": ids}
    if args.depth:
        params["depth"] = args.depth
    data = request_json(
        "GET", f"{FIGMA_BASE}/v1/files/{file_key}/nodes", headers=figma_headers(), params=params
    )
    cache_path = cache_json("figmax", f"{file_key}:{ids}", data)
    if args.format == "json":
        print_json(data)
        return 0
    for node_id, entry in (data.get("nodes") or {}).items():
        if not entry:
            print(f"## {node_id}: not found")
            continue
        print(f"## {node_id}")
        print_tree(entry.get("document", {}), 0, 0, all_types=True)
        print()
    print(f"[raw cached: {cache_path}]")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    file_key, url_node_id = parse_file_ref(args.file)
    ids = resolve_node_ids(args, url_node_id)
    params: dict[str, Any] = {"ids": ids, "format": args.fmt, "scale": args.scale}
    data = request_json(
        "GET", f"{FIGMA_BASE}/v1/images/{file_key}", headers=figma_headers(), params=params
    )
    if data.get("err"):
        raise AgentCliError(f"Figma render failed: {data['err']}")
    out_dir = Path(args.out) if args.out else cache_dir("figmax")
    out_dir.mkdir(parents=True, exist_ok=True)
    for node_id, url in (data.get("images") or {}).items():
        if not url:
            print(f"{node_id}: render failed (null image)")
            continue
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        if response.status_code >= 400:
            raise AgentCliError(f"Download failed: HTTP {response.status_code}")
        safe_id = node_id.replace(":", "-")
        path = out_dir / f"{file_key}-{safe_id}.{args.fmt}"
        path.write_bytes(response.content)
        print(f"{node_id}: {path}")
    return 0


def cmd_comments(args: argparse.Namespace) -> int:
    file_key, _ = parse_file_ref(args.file)
    data = request_json(
        "GET",
        f"{FIGMA_BASE}/v1/files/{file_key}/comments",
        headers=figma_headers(),
        params={"as_md": "true"},
    )
    cache_path = cache_json("figmax", f"{file_key}-comments", data)
    if args.format == "json":
        print_json(data)
        return 0
    comments = data.get("comments", [])
    if not comments:
        print("No comments.")
        return 0
    for comment in comments[: args.limit]:
        user = (comment.get("user") or {}).get("handle", "?")
        created = comment.get("created_at", "?")
        resolved = " (resolved)" if comment.get("resolved_at") else ""
        print(f"- {user} @ {created}{resolved}")
        print(f"  {truncate(comment.get('message', ''), args.max_chars)}")
    print()
    print(f"[{len(comments)} total; raw cached: {cache_path}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="figmax", description="Read-only Figma REST API CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    file_cmd = sub.add_parser("file", help="Summarize a file's page/frame tree.")
    file_cmd.add_argument("file", help="Figma file URL or file key.")
    file_cmd.add_argument("--depth", type=int, default=2, help="Document tree depth to fetch (default 2).")
    file_cmd.add_argument("--all-nodes", action="store_true", help="Print every node type, not just containers.")
    file_cmd.add_argument("--format", choices=["markdown", "json"], default="markdown")
    file_cmd.set_defaults(func=cmd_file)

    node = sub.add_parser("node", help="Inspect specific nodes.")
    node.add_argument("file", help="Figma file URL (node-id param respected) or file key.")
    node.add_argument("--id", help="Comma separated node ids (1:23 or 1-23).")
    node.add_argument("--depth", type=int, default=None, help="Subtree depth to fetch.")
    node.add_argument("--format", choices=["markdown", "json"], default="markdown")
    node.set_defaults(func=cmd_node)

    export = sub.add_parser("export", help="Render nodes to image files.")
    export.add_argument("file", help="Figma file URL (node-id param respected) or file key.")
    export.add_argument("--id", help="Comma separated node ids (1:23 or 1-23).")
    export.add_argument("--fmt", choices=["png", "jpg", "svg", "pdf"], default="png")
    export.add_argument("--scale", type=float, default=1, help="Scale factor 0.01-4 (default 1).")
    export.add_argument("--out", help="Output directory (default: figmax cache dir).")
    export.set_defaults(func=cmd_export)

    comments = sub.add_parser("comments", help="List comments on a file.")
    comments.add_argument("file", help="Figma file URL or file key.")
    comments.add_argument("--limit", type=int, default=20)
    comments.add_argument("--max-chars", type=int, default=500)
    comments.add_argument("--format", choices=["markdown", "json"], default="markdown")
    comments.set_defaults(func=cmd_comments)
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
