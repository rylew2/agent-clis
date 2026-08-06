"""Regression guard for the UTF-8 stdio fix (PR #2).

ytx no longer calls configure_stdio() itself -- it inherits the import-time call
in agent_clis.common. If that call is ever removed, non-Latin-1 transcript text
crashes again on the Windows console.
"""

from __future__ import annotations

import os
import subprocess
import sys


def test_importing_a_cli_forces_utf8_stdout():
    """Simulates a cp1252 console: printing CJK text must not raise."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    completed = subprocess.run(
        [sys.executable, "-c", "import agent_clis.ytx; print('你好 — café')"],
        capture_output=True,
        env=env,
    )
    stderr = completed.stderr.decode("utf-8", errors="replace")
    assert completed.returncode == 0, stderr
    assert "UnicodeEncodeError" not in stderr
    assert "你好" in completed.stdout.decode("utf-8", errors="replace")
