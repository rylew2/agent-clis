"""Security boundaries and offline exports using the installed gallery-dl backend."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_clis import twitterx
from agent_clis.common import AgentCliError


@pytest.mark.parametrize("value", ["https://x.com.evil.test/a/status/123", "https://evil.test/a/status/123", "file:///a/status/123", "https://x.com@evil.test/a/status/123", "https://x.com/a/status/123;cmd", "https://x.com/home"])
def test_rejects_non_tweet_inputs(value):
    with pytest.raises(AgentCliError):
        twitterx.normalize_url(value)


def test_normalizes_only_status_url():
    assert twitterx.normalize_url("https://twitter.com/person/status/123/photo/1?s=20") == ("https://x.com/i/web/status/123", "123")


def test_no_ambient_config_or_unrequested_cookie_access(tmp_path):
    args = twitterx.build_parser().parse_args(["thread", "123"])
    command = twitterx.build_command(args, "https://x.com/i/web/status/123", tmp_path / "config.json")
    assert "--config-ignore" in command
    assert "-I" in command
    assert "--cookies" not in command and "--cookies-from-browser" not in command
    args.browser = "firefox"
    assert "firefox/x.com" in twitterx.build_command(args, "https://x.com/i/web/status/123", tmp_path / "config.json")


def test_cookie_file_filters_domains_names_and_keeps_original(tmp_path):
    source = tmp_path / "original.txt"
    content = "# Netscape HTTP Cookie File\n.x.com\tTRUE\t/\tTRUE\t2147483647\tauth_token\tfake-token\n.x.com\tTRUE\t/\tTRUE\t2147483647\tct0\tfake-csrf\n.evil.test\tTRUE\t/\tTRUE\t2147483647\tauth_token\tunrelated\n.x.com\tTRUE\t/\tTRUE\t2147483647\tother\tunneeded\n"
    source.write_text(content)
    destination = tmp_path / "filtered.txt"
    twitterx.filter_cookie_file(source, destination)
    filtered = destination.read_text()
    assert "fake-token" in filtered and "fake-csrf" in filtered
    assert "unrelated" not in filtered and "unneeded" not in filtered
    assert source.read_text() == content


@pytest.mark.parametrize("media", [True, False])
def test_real_backend_exports_text_only_posts_and_downloads_media(tmp_path, media):
    if not twitterx.backend_python().exists():
        pytest.skip("Install isolated gallery-dl backend for integration check")
    config = tmp_path / "config.json"
    config.write_text(json.dumps(twitterx.make_config(tmp_path, True, media)))
    script = r'''
import json,re,sys,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from gallery_dl import config,job
from gallery_dl.extractor.common import Extractor
from gallery_dl.extractor.message import Message
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"test-media-bytes")
    def log_message(self,*args): pass
server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
class Fixture(Extractor):
    category="twitter"
    subcategory="tweet"
    def items(self):
        base={"author":{"name":"fixture","nick":"Fixture"},"date":"2026-09-26","reply_id":0,"conversation_id":123,"content":"text-only unicode café", "count":0,"tweet_id":123}
        yield Message.Directory,"",base
        second=dict(base,tweet_id=124,content="post with media",count=1,reply_id=123)
        yield Message.Directory,"",second
        yield Message.Url,f"http://127.0.0.1:{server.server_port}/fixture.jpg",dict(second,num=1,extension="jpg")
config.load((sys.argv[1],),strict=True)
download=job.DownloadJob(Fixture(re.match(".*","fixture")))
download.run()
server.shutdown()
sys.exit(download.status)
'''
    result = subprocess.run([str(twitterx.backend_python()), "-I", "-c", script, str(config)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    posts = twitterx.collect_posts(tmp_path)
    assert [p["id"] for p in posts] == ["123", "124"]
    assert posts[0]["text"] == "text-only unicode café"
    assert posts[1]["media"] == (["media/124_1.jpg"] if media else [])
    if media:
        assert (tmp_path / "media/124_1.jpg").read_bytes() == b"test-media-bytes"


def test_backend_failure_preserves_partial_export(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(twitterx, "backend_python", lambda: Path(sys.executable))
    args = twitterx.build_parser().parse_args(["thread", "123", "-o", str(tmp_path), "--json"])
    def run(command, **kwargs):
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "1.32.13\n", "")
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw/123.json").write_text(json.dumps({"tweet_id":123, "content":"partial post", "count":0}))
        return subprocess.CompletedProcess(command, 1, b"", b"private upstream error")
    monkeypatch.setattr(twitterx.subprocess, "run", run)
    assert twitterx.export(args) == 1
    data = json.loads((tmp_path / "thread.json").read_text())
    assert data["status"] == "partial" and len(data["posts"]) == 1
    assert "private upstream error" not in capsys.readouterr().out
