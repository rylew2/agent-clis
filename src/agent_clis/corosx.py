"""Read-only COROS cache reports."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .common import AgentCliError, main_wrapper, print_json


DEFAULT_DB = Path.home() / ".config" / "coros-mcp" / "cache.db"
STAT_QUERIES = {
    "daily_records": "SELECT COUNT(*) AS count, MIN(date) AS first_day, MAX(date) AS last_day FROM daily_records",
    "sleep_records": "SELECT COUNT(*) AS count, MIN(date) AS first_day, MAX(date) AS last_day FROM sleep_records",
    "activities": "SELECT COUNT(*) AS count, MIN(start_day) AS first_day, MAX(start_day) AS last_day FROM activities",
}
RANGE_QUERIES = {
    "daily_records": "SELECT date AS day, data, synced_at FROM daily_records WHERE date >= ? AND date <= ? ORDER BY date DESC LIMIT ?",
    "sleep_records": "SELECT date AS day, data, synced_at FROM sleep_records WHERE date >= ? AND date <= ? ORDER BY date DESC LIMIT ?",
    "activities": "SELECT start_day AS day, data, synced_at FROM activities WHERE start_day >= ? AND start_day <= ? ORDER BY start_day DESC LIMIT ?",
}


def db_path() -> Path:
    return Path(os.getenv("COROS_CACHE_DB", DEFAULT_DB))


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise AgentCliError(f"COROS cache not found: {path}. Sync with coros-mcp first or set COROS_CACHE_DB.")
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def today_yyyymmdd() -> str:
    return dt.date.today().strftime("%Y%m%d")


def weeks_ago(weeks: int) -> str:
    return (dt.date.today() - dt.timedelta(days=weeks * 7)).strftime("%Y%m%d")


def table_stats(con: sqlite3.Connection, table: str) -> dict[str, Any]:
    row = con.execute(STAT_QUERIES[table]).fetchone()
    return dict(row)


def read_rows(table: str, start: str, end: str, limit: int) -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute(RANGE_QUERIES[table], (start, end, limit)).fetchall()
    parsed = []
    for row in rows:
        data = json.loads(row["data"])
        parsed.append({"day": row["day"], "synced_at": row["synced_at"], "data": data})
    return parsed


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    data = record["data"]
    if not isinstance(data, dict):
        return record
    preferred = [
        "date",
        "start_time",
        "name",
        "sport_name",
        "distance",
        "duration",
        "training_load",
        "sleep_time",
        "total_sleep",
        "avg_hr",
        "hrv",
        "resting_hr",
        "calories",
    ]
    summary = {"day": record["day"]}
    for key in preferred:
        if key in data and data[key] not in (None, "", []):
            summary[key] = data[key]
    if len(summary) == 1:
        for key, value in list(data.items())[:8]:
            if value not in (None, "", []):
                summary[key] = value
    return summary


def print_records(records: list[dict[str, Any]], full: bool) -> None:
    if full:
        print_json(records)
        return
    for record in records:
        print_json(summarize_record(record))


def cmd_status(_: argparse.Namespace) -> int:
    with connect() as con:
        data = {
            "db_path": str(db_path()),
            "daily_records": table_stats(con, "daily_records"),
            "sleep_records": table_stats(con, "sleep_records"),
            "activities": table_stats(con, "activities"),
        }
    print_json(data)
    return 0


def range_args(args: argparse.Namespace) -> tuple[str, str]:
    return args.start or weeks_ago(args.weeks), args.end or today_yyyymmdd()


def cmd_daily(args: argparse.Namespace) -> int:
    start, end = range_args(args)
    print_records(read_rows("daily_records", start, end, args.limit), args.full)
    return 0


def cmd_sleep(args: argparse.Namespace) -> int:
    start, end = range_args(args)
    print_records(read_rows("sleep_records", start, end, args.limit), args.full)
    return 0


def cmd_activities(args: argparse.Namespace) -> int:
    start, end = range_args(args)
    print_records(read_rows("activities", start, end, args.limit), args.full)
    return 0


def add_range_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--weeks", type=int, default=4)
    parser.add_argument("--start", help="YYYYMMDD start day")
    parser.add_argument("--end", help="YYYYMMDD end day")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--full", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="corosx", description="Read-only reports from the coros-mcp SQLite cache.")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)
    daily = sub.add_parser("daily")
    add_range_options(daily)
    daily.set_defaults(func=cmd_daily)
    sleep = sub.add_parser("sleep")
    add_range_options(sleep)
    sleep.set_defaults(func=cmd_sleep)
    acts = sub.add_parser("activities")
    add_range_options(acts)
    acts.set_defaults(func=cmd_activities)
    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
