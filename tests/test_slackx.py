"""Offline checks for slackx parsing, channel resolution, and pagination."""

import pytest

from agent_clis import slackx
from agent_clis.common import AgentCliError


class FakeSlack:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, method, params):
        self.calls.append((method, params))
        return self.pages[len(self.calls) - 1]


def test_parse_permalink_converts_ts():
    assert slackx.parse_permalink("https://x.slack.com/archives/C04PGR4K16D/p1790947232181979") == (
        "C04PGR4K16D",
        "1790947232.181979",
    )


@pytest.mark.parametrize(
    "value",
    ["C04PGR4K16D", "https://x.slack.com/archives/C04PGR4K16D", "https://x.slack.com/archives/C04PGR4K16D/p1790947232181979"],
)
def test_resolve_channel_skips_api_for_ids_and_urls(monkeypatch, value):
    monkeypatch.setattr(slackx, "slack_api", FakeSlack([]))
    assert slackx.resolve_channel(value) == "C04PGR4K16D"


def test_resolve_channel_by_name_follows_cursor(monkeypatch):
    fake = FakeSlack(
        [
            {"channels": [{"id": "C1", "name": "general"}], "response_metadata": {"next_cursor": "next"}},
            {"channels": [{"id": "C2", "name": "ai"}], "response_metadata": {"next_cursor": ""}},
        ]
    )
    monkeypatch.setattr(slackx, "slack_api", fake)
    assert slackx.resolve_channel("#AI") == "C2"
    assert fake.calls[1][1]["cursor"] == "next"


def test_resolve_channel_unknown_name_raises(monkeypatch):
    monkeypatch.setattr(slackx, "slack_api", FakeSlack([{"channels": []}]))
    with pytest.raises(AgentCliError):
        slackx.resolve_channel("missing")


def test_history_prints_oldest_first(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(slackx, "cache_json", lambda *args: tmp_path / "cache.json")
    monkeypatch.setattr(
        slackx,
        "slack_api",
        FakeSlack([{"messages": [{"user": "U2", "ts": "2.0", "text": "newer"}, {"user": "U1", "ts": "1.0", "text": "older"}]}]),
    )
    args = slackx.build_parser().parse_args(["history", "C04PGR4K16D"])
    args.func(args)
    out = capsys.readouterr().out
    assert out.index("older") < out.index("newer")


def test_search_labels_dms(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(slackx, "cache_json", lambda *args: tmp_path / "cache.json")
    match = {"channel": {"id": "D1", "name": "U9", "is_im": True}, "username": "pat", "ts": "1.0", "text": "hi"}
    monkeypatch.setattr(slackx, "slack_api", FakeSlack([{"messages": {"matches": [match], "total": 1}}]))
    args = slackx.build_parser().parse_args(["search", "hi"])
    args.func(args)
    assert "## 1. DM U9 | pat | 1.0" in capsys.readouterr().out
