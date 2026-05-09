"""Concise Semgrep wrapper."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from typing import Any

from .common import AgentCliError, cache_json, main_wrapper, print_json


def run_semgrep(args: argparse.Namespace) -> dict[str, Any]:
    exe = shutil.which("semgrep")
    if not exe:
        raise AgentCliError("semgrep not found on PATH. Install Semgrep first: python -m pip install semgrep")
    command = [exe, "scan", "--json", "--config", args.config, args.path]
    if args.severity:
        command.extend(["--severity", args.severity])
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=env, encoding="utf-8", errors="replace")
    if completed.returncode not in {0, 1}:
        raise AgentCliError(completed.stderr.strip() or completed.stdout.strip() or "semgrep failed")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AgentCliError(f"Could not parse Semgrep JSON: {exc}") from exc


def print_findings(data: dict[str, Any], limit: int) -> None:
    results = data.get("results", [])
    if not results:
        print("No Semgrep findings.")
        return
    for idx, finding in enumerate(results[:limit], start=1):
        extra = finding.get("extra", {})
        path = finding.get("path", "")
        start = finding.get("start", {})
        line = start.get("line", "?")
        severity = extra.get("severity", "")
        rule = finding.get("check_id", "")
        message = extra.get("message", "")
        print(f"{idx}. {severity} {path}:{line} {rule}")
        if message:
            print(f"   {message}")
    if len(results) > limit:
        print(f"[{len(results) - limit} more findings omitted]")


def cmd_scan(args: argparse.Namespace) -> int:
    data = run_semgrep(args)
    cache_path = cache_json("semgrepx", f"{args.config}:{args.path}", data)
    if args.format == "json":
        print_json(data)
    else:
        print_findings(data, args.limit)
        print(f"[raw cached: {cache_path}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semgrepx", description="Run Semgrep and print concise findings.")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Run a Semgrep scan.")
    scan.add_argument("path", nargs="?", default=".")
    scan.add_argument("--config", default="auto")
    scan.add_argument("--severity", choices=["INFO", "WARNING", "ERROR"])
    scan.add_argument("--limit", type=int, default=50)
    scan.add_argument("--format", choices=["text", "json"], default="text")
    scan.set_defaults(func=cmd_scan)
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
