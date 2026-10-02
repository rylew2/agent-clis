"""Output must be bounded and machine-readable on every CLI."""

from __future__ import annotations

import json
import sqlite3

import pytest

from agent_clis import browserx, corosx, ytx


def test_ytx_transcript_caps_output_by_default(monkeypatch, capsys):
    """A two-hour transcript must not dump 30k tokens into the agent."""
    monkeypatch.setattr(
        ytx,
        "fetch_transcript",
        lambda url, language: {
            "video_id": "dQw4w9WgXcQ",
            "language": "English",
            "language_code": "en",
            "word_count": 20000,
            "text": "word " * 20000,
        },
    )

    assert ytx.main(["transcript", "dQw4w9WgXcQ", "--no-header"]) == 0
    out = capsys.readouterr().out
    assert len(out) < 25000
    assert "[truncated" in out


def test_ytx_full_flag_restores_the_whole_transcript(monkeypatch, capsys):
    long_text = "word " * 20000
    monkeypatch.setattr(
        ytx,
        "fetch_transcript",
        lambda url, language: {
            "video_id": "dQw4w9WgXcQ",
            "language": "English",
            "language_code": "en",
            "word_count": 20000,
            "text": long_text,
        },
    )

    assert ytx.main(["transcript", "dQw4w9WgXcQ", "--no-header", "--full"]) == 0
    out = capsys.readouterr().out
    assert "[truncated" not in out
    assert len(out.strip()) == len(long_text.strip())


def test_ytx_save_source_is_never_truncated(monkeypatch, tmp_path):
    """save-source writes a file, so the cap would corrupt the archive."""
    long_text = "word " * 20000
    monkeypatch.setattr(
        ytx,
        "fetch_transcript",
        lambda url, language: {
            "video_id": "dQw4w9WgXcQ",
            "language": "English",
            "language_code": "en",
            "word_count": 20000,
            "text": long_text,
        },
    )
    out_file = tmp_path / "note.md"

    assert ytx.main(["save-source", "dQw4w9WgXcQ", "-o", str(out_file)]) == 0
    assert "[truncated" not in out_file.read_text(encoding="utf-8")


def test_browserx_links_emits_one_json_array(monkeypatch, capsys):
    html = '<a href="/a">Alpha</a><a href="https://x.test/b">Beta</a>'
    monkeypatch.setattr(browserx, "request_text", lambda *a, **k: html)

    assert browserx.main(["links", "https://x.test/", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["url"] for item in payload] == ["https://x.test/a", "https://x.test/b"]
    assert payload[0]["text"] == "Alpha"


@pytest.fixture
def coros_db(tmp_path, monkeypatch):
    path = tmp_path / "cache.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE daily_records (date TEXT, data TEXT, synced_at TEXT)")
    con.execute("CREATE TABLE sleep_records (date TEXT, data TEXT, synced_at TEXT)")
    con.execute("CREATE TABLE activities (start_day TEXT, data TEXT, synced_at TEXT)")
    for day in ("20260801", "20260802"):
        con.execute(
            "INSERT INTO daily_records VALUES (?, ?, ?)",
            (day, json.dumps({"date": day, "resting_hr": 52}), "2026-08-06"),
        )
    con.commit()
    con.close()
    monkeypatch.setenv("COROS_CACHE_DB", str(path))
    return path


def test_corosx_daily_json_is_a_single_parseable_document(coros_db, capsys):
    """Concatenated JSON objects cannot be piped to jq."""
    assert corosx.main(["daily", "--start", "20260101", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert payload[0]["day"] == "20260802"


def test_corosx_full_stays_json_because_raw_records_are_nested(coros_db, capsys):
    assert corosx.main(["daily", "--start", "20260101", "--full"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["data"]["resting_hr"] == 52


def test_corosx_defaults_to_readable_text(coros_db, capsys):
    assert corosx.main(["daily", "--start", "20260101"]) == 0
    out = capsys.readouterr().out
    assert "20260802" in out
    assert "resting_hr" in out
