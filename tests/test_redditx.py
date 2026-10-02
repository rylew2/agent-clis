"""Offline checks for redditx's RSS fallback when old.reddit.com is blocked."""

from __future__ import annotations

import pytest

from agent_clis import redditx

SEARCH_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>t3_abc</id>
    <title>Agent  credentials</title>
    <link href="https://www.reddit.com/r/devops/comments/abc/agent_credentials/"/>
    <category term="devops"/>
    <author><name>/u/poster</name></author>
    <content type="html">&lt;p&gt;How do you scope tokens?&lt;/p&gt;</content>
  </entry>
  <entry>
    <id>t5_sub</id>
    <title>r/devops</title>
  </entry>
</feed>"""

THREAD_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>t3_abc</id>
    <title>Agent credentials</title>
    <category term="devops"/>
    <content type="html">&lt;p&gt;Post body&lt;/p&gt;</content>
  </entry>
  <entry>
    <id>t1_def</id>
    <title>/u/replier on Agent credentials</title>
    <link href="https://www.reddit.com/r/devops/comments/abc/_/def/"/>
    <author><name>/u/replier</name></author>
    <content type="html">&lt;p&gt;Use a broker&lt;/p&gt;</content>
  </entry>
</feed>"""


def blocked(*args, **kwargs):
    raise redditx.RedditBlockedError("HTTP 403")


def no_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(redditx, "cache_json", lambda *args: tmp_path / "cache.json")


def test_parse_rss_entries_strips_html_and_author_prefix():
    post, subreddit = redditx.parse_rss_entries(SEARCH_FEED)
    assert post["title"] == "Agent credentials"
    assert post["author"] == "poster"
    assert post["subreddit"] == "devops"
    assert post["text"] == "How do you scope tokens?"
    assert subreddit["id"] == "t5_sub"


def test_search_falls_back_to_rss_posts_only(monkeypatch, tmp_path, capsys):
    no_cache(monkeypatch, tmp_path)
    monkeypatch.setattr(redditx, "fetch_html", blocked)
    monkeypatch.setattr(redditx, "fetch_rss", lambda url, params=None: SEARCH_FEED)
    assert redditx.main(["search", "agent credentials"]) == 0
    out = capsys.readouterr().out
    assert "[rss fallback" in out
    assert out.count("## ") == 1
    assert "Agent credentials" in out


def test_thread_falls_back_to_rss(monkeypatch, tmp_path, capsys):
    no_cache(monkeypatch, tmp_path)
    monkeypatch.setattr(redditx, "fetch_html", blocked)
    requested = []

    def fake_rss(url, params=None):
        requested.append(url)
        return THREAD_FEED

    monkeypatch.setattr(redditx, "fetch_rss", fake_rss)
    assert redditx.main(["thread", "https://www.reddit.com/r/devops/comments/abc/agent_credentials/"]) == 0
    out = capsys.readouterr().out
    assert requested[0].startswith("https://www.reddit.com/") and requested[0].endswith(".rss")
    assert "# Agent credentials" in out
    assert "Use a broker" in out


def test_login_redirect_counts_as_blocked(monkeypatch):
    class Response:
        status_code = 200
        url = "https://www.reddit.com/login/?dest=x"
        text = "<html></html>"

    monkeypatch.setattr(redditx, "get_with_retries", lambda *args, **kwargs: Response())
    with pytest.raises(redditx.RedditBlockedError):
        redditx.fetch_html("https://old.reddit.com/search")
