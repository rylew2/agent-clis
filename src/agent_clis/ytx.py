"""Fetch YouTube transcripts from the command line."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
VIDEO_URL_RE = re.compile(r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})")


def extract_video_id(url_or_id: str) -> str:
    match = VIDEO_URL_RE.search(url_or_id)
    if match:
        return match.group(1)
    if VIDEO_ID_RE.match(url_or_id):
        return url_or_id
    raise ValueError(f"Could not extract video ID from '{url_or_id}'")


def fetch_transcript(url_or_id: str, language: str) -> dict[str, Any]:
    video_id = extract_video_id(url_or_id)
    transcript = YouTubeTranscriptApi().fetch(video_id, languages=[language])
    text = TextFormatter().format_transcript(transcript)
    return {
        "video_id": video_id,
        "language": transcript.language,
        "language_code": transcript.language_code,
        "word_count": len(text.split()),
        "text": text,
    }


def render_text(data: dict[str, Any], include_header: bool = True) -> str:
    if not include_header:
        return data["text"]
    return (
        f"[Video ID: {data['video_id']} | Language: {data['language']} | "
        f"Words: {data['word_count']}]\n\n{data['text']}"
    )


def write_or_print(content: str, output: Path | None) -> None:
    if output is None:
        print(content)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
    print(f"Wrote {output}")


def cmd_transcript(args: argparse.Namespace) -> int:
    data = fetch_transcript(args.url, args.language)
    if args.format == "json":
        content = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        content = render_text(data, include_header=not args.no_header)
    write_or_print(content, args.output)
    return 0


def cmd_save_source(args: argparse.Namespace) -> int:
    data = fetch_transcript(args.url, args.language)
    title = args.title or f"YouTube Transcript {data['video_id']}"
    url = args.url if args.url.startswith("http") else f"https://www.youtube.com/watch?v={data['video_id']}"
    content = "\n".join(
        [
            "---",
            f"title: {title}",
            f"url: {url}",
            f"fetched: {args.fetched}",
            "type: youtube-transcript",
            "---",
            "",
            render_text(data),
            "",
        ]
    )
    write_or_print(content, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytx",
        description="Fetch YouTube transcripts without loading the YouTube MCP server.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    transcript = subparsers.add_parser("transcript", help="Print or save a transcript.")
    transcript.add_argument("url", help="YouTube URL or 11-character video ID.")
    transcript.add_argument("-l", "--language", default="en", help="Transcript language code.")
    transcript.add_argument(
        "-f",
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    transcript.add_argument("--no-header", action="store_true", help="Only print transcript text.")
    transcript.add_argument("-o", "--output", type=Path, help="Write output to a file.")
    transcript.set_defaults(func=cmd_transcript)

    save = subparsers.add_parser("save-source", help="Save a transcript source note.")
    save.add_argument("url", help="YouTube URL or 11-character video ID.")
    save.add_argument("-l", "--language", default="en", help="Transcript language code.")
    save.add_argument("--title", help="Frontmatter title.")
    save.add_argument("--fetched", default=dt.date.today().isoformat(), help="Frontmatter fetched date.")
    save.add_argument("-o", "--output", type=Path, required=True, help="Markdown file to write.")
    save.set_defaults(func=cmd_save_source)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 - CLI should print clean errors.
        print(f"ytx: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
