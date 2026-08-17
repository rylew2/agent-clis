"""Secret resolution order: env override wins, else the OS credential store.

Secrets must never fall back to a plaintext .env, so the credential store is the
only non-override source.
"""

from __future__ import annotations

import pytest

from agent_clis import common
from agent_clis.common import AgentCliError, require_env


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    # Neutralize .env loading so tests observe only env + keyring resolution.
    monkeypatch.setattr(common, "_load_dotenv_once", lambda: None)


def test_reads_from_keyring_when_env_unset(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.setattr(common, "_get_from_keyring", lambda name: "from-store" if name == "EXA_API_KEY" else None)

    assert require_env("EXA_API_KEY") == "from-store"


def test_env_overrides_store(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "from-env")
    monkeypatch.setattr(common, "_get_from_keyring", lambda name: "from-store")

    assert require_env("EXA_API_KEY") == "from-env"


def test_missing_everywhere_raises_with_help(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.setattr(common, "_get_from_keyring", lambda name: None)

    with pytest.raises(AgentCliError) as exc:
        require_env("EXA_API_KEY", "do the thing")
    assert "Missing EXA_API_KEY" in str(exc.value)
    assert "do the thing" in str(exc.value)


def test_keyring_backend_failure_degrades_to_missing(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)

    def boom(*_args, **_kwargs):
        raise RuntimeError("backend locked")

    # Simulate a keyring whose get_password raises; _get_from_keyring must swallow it.
    import types

    fake = types.SimpleNamespace(get_password=boom)
    monkeypatch.setitem(__import__("sys").modules, "keyring", fake)

    assert common._get_from_keyring("EXA_API_KEY") is None
    with pytest.raises(AgentCliError):
        require_env("EXA_API_KEY")
