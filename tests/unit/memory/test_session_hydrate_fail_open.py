"""Fail-open guard for the SessionStart memory-hydrate hook (principle 15).

The hydrate hook contracts to NEVER block session start: when Redis or the
memory index is unreachable it logs to its own hydrate.log, prints a
one-line ``[memory-hydrate] skipped:`` notice, and exits 0. Principle 15 of
the collaboration-contract Principles section
(docs/specs/feature-lead-governance/principles-section-draft.md; moves to
content/collaboration/contract.md on ratification) named this fail-open
path as its remaining untested half — this module pins it.

Scope note: the hook script is personal infra, not tracked in this repo —
it lives in the attune-agent-memory checkout at ``~/.attune/memory/
session_hydrate.py``, wired as a SessionStart hook via
``~/.claude/settings.json``. These tests therefore run the REAL script
where that checkout exists and skip elsewhere (CI skips): the enforcement
is machine-local, matching where the hook actually runs.

Hermetic setup: the script is copied into ``tmp_path`` so its
ROOT-relative side effects (hydrate.log, the memory-repo ``git pull``)
land in the temp dir — the pull fails fast because tmp is not a git repo,
so no network is touched — and a stub ``redis`` module injected via
PYTHONPATH simulates each failure mode without a real Redis.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

HYDRATE_HOOK = Path.home() / ".attune" / "memory" / "session_hydrate.py"

pytestmark = pytest.mark.skipif(
    not HYDRATE_HOOK.exists(),
    reason="personal-infra hydrate hook not present on this machine "
    "(~/.attune/memory/session_hydrate.py — attune-agent-memory checkout)",
)

_STUB_CONNECTION_REFUSED = '''\
"""Stub redis: importable, but every connection attempt is refused."""


class Redis:
    def __init__(self, *args, **kwargs):
        pass

    def ping(self):
        raise ConnectionError("connection refused (test stub)")
'''

_STUB_IMPORT_FAILURE = '''\
"""Stub redis that fails at import time (missing/broken dependency)."""

raise ImportError("redis is not importable (test stub)")
'''


def _run_hook_with_stub(
    tmp_path: Path, stub_source: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run a temp copy of the hydrate hook against a stubbed redis module.

    Returns the completed process and the temp copy's hydrate.log path.
    """
    script = tmp_path / "session_hydrate.py"
    script.write_text(HYDRATE_HOOK.read_text(encoding="utf-8"), encoding="utf-8")

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "redis.py").write_text(stub_source, encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(stubs)  # stub shadows any installed redis

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc, tmp_path / "hydrate.log"


@pytest.mark.parametrize(
    ("stub_source", "expected_cause"),
    [
        pytest.param(_STUB_CONNECTION_REFUSED, "ConnectionError", id="connection-refused"),
        pytest.param(_STUB_IMPORT_FAILURE, "ImportError", id="import-failure"),
    ],
)
def test_unreachable_backend_fails_open(
    tmp_path: Path, stub_source: str, expected_cause: str
) -> None:
    """An unreachable backend never blocks session start.

    The hook must exit 0, surface the one-line skip notice (naming the
    failure class) on stdout, log the degradation, and never raise.
    """
    proc, log = _run_hook_with_stub(tmp_path, stub_source)

    assert proc.returncode == 0, f"hook must exit 0 on backend failure; stderr:\n{proc.stderr}"
    assert "[memory-hydrate] skipped:" in proc.stdout
    assert expected_cause in proc.stdout
    assert (
        "Traceback" not in proc.stderr
    ), "fail-open must swallow the failure, not print a traceback"

    # Degraded, not succeeded: the success line must be absent, and the
    # no-op must be recorded in the hook's own log (temp copy, not the
    # real ~/.attune/memory/hydrate.log).
    assert "curated nodes warm" not in proc.stdout
    assert log.exists()
    assert "redis unavailable, no-op" in log.read_text(encoding="utf-8")
