"""The shared failure contract every agent CLI must honour.

Exit codes are the only signal an agent gets without spending context, so they
have to distinguish "you called it wrong" from "it ran and failed".
"""

from __future__ import annotations

import pytest
import requests

from agent_clis import docsx, searchx, ytx
from agent_clis.common import AgentCliError, main_wrapper


def test_expected_error_exits_1(capsys):
    def run() -> int:
        raise AgentCliError("cache not found")

    assert main_wrapper(run) == 1
    assert capsys.readouterr().err.strip() == "error: cache not found"


def test_usage_error_exits_2_so_it_is_distinguishable(capsys):
    with pytest.raises(SystemExit) as exc:
        ytx.build_parser().parse_args(["transcript", "--bogus", "dQw4w9WgXcQ"])
    assert exc.value.code == 2


def test_unexpected_exception_is_reported_without_a_traceback(capsys):
    def run() -> int:
        raise requests.exceptions.ConnectionError("Max retries exceeded with url: /")

    assert main_wrapper(run) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "site-packages" not in err
    assert err.strip() == "error: ConnectionError: Max retries exceeded with url: /"


def test_traceback_is_available_behind_an_env_flag(monkeypatch):
    monkeypatch.setenv("AGENT_CLIS_TRACEBACK", "1")

    def run() -> int:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        main_wrapper(run)


def test_keyboard_interrupt_exits_130(capsys):
    def run() -> int:
        raise KeyboardInterrupt

    assert main_wrapper(run) == 130


def test_http_error_does_not_paste_the_whole_response_body(monkeypatch):
    """A 404 HTML page must not land in the agent's context."""
    body = "<html>" + ("x" * 5000) + "</html>"

    class FakeResponse:
        status_code = 404
        text = body

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse())

    with pytest.raises(AgentCliError) as exc:
        from agent_clis.common import request_text

        request_text("https://example.com/missing")

    message = str(exc.value)
    assert len(message) < 400
    assert "[truncated" in message


def test_ytx_runtime_failure_exits_1_and_keeps_stdout_clean(capsys):
    assert ytx.main(["transcript", "not-a-url"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error: " in captured.err


@pytest.mark.parametrize("module", [docsx, searchx, ytx])
def test_every_cli_routes_through_the_shared_wrapper(module, monkeypatch, capsys):
    """Each entrypoint must convert exceptions, not let them escape."""

    def exploding_parser():
        raise requests.exceptions.Timeout("read timed out")

    monkeypatch.setattr(module, "build_parser", exploding_parser)
    assert module.main([]) == 1
    assert "Traceback" not in capsys.readouterr().err
