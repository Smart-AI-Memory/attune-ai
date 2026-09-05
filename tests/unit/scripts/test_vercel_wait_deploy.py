"""Unit tests for scripts/vercel_wait_deploy.py.

Pins: the deployment is matched by commit prefix on the API's state
field (no text parsing), every transition is printed once, outcomes map
to exit codes, and the probe never follows redirects — a 308 must be
reported as 308, because Vercel Cron treats it as final.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"
SCRIPT = SCRIPTS / "vercel_wait_deploy.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _fake_resolve(token="t", org="o", pid="p", name="website"):
    from vercel_common import Link

    return lambda cwd, project_id=None: Link(token, org, project_id or pid, name)


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_vercel_wait_deploy", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _dep(sha: str, state: str, url: str = "x.vercel.app", err: str | None = None) -> dict:
    d = {"meta": {"githubCommitSha": sha}, "readyState": state, "url": url}
    if err:
        d["errorMessage"] = err
    return d


class TestFindDeployment:
    def test_matches_by_commit_prefix_newest_first(self, mod, monkeypatch):
        monkeypatch.setattr(
            mod,
            "_get",
            lambda p, t: {"deployments": [_dep("abc123def", "READY"), _dep("abc999", "BUILDING")]},
        )
        d = mod.find_deployment("t", "o", "p", "abc123")
        assert d and d["readyState"] == "READY"
        assert mod.find_deployment("t", "o", "p", "zzz") is None


class TestWait:
    def _run(self, mod, monkeypatch, states, timeout=100):
        seq = iter(states)
        monkeypatch.setattr(mod, "find_deployment", lambda *a: next(seq))
        lines = []
        t = [0.0]

        def clock():
            return t[0]

        def sleep(s):
            t[0] += s

        return (
            mod.wait(
                "t", "o", "p", "abc123def", timeout, 10, sleep=sleep, clock=clock, out=lines.append
            ),
            lines,
        )

    def test_transitions_printed_once_and_ready_exits_zero(self, mod, monkeypatch):
        states = [
            None,
            _dep("abc123def", "QUEUED"),
            _dep("abc123def", "BUILDING"),
            _dep("abc123def", "BUILDING"),
            _dep("abc123def", "READY"),
        ]
        (rc, dep), lines = self._run(mod, monkeypatch, states)
        assert rc == 0 and dep["readyState"] == "READY"
        joined = "\n".join(lines)
        assert joined.count("BUILDING") == 1  # repeated state is not re-printed
        assert "NOT-FOUND" in joined and "QUEUED" in joined and "READY" in joined

    def test_error_exits_one(self, mod, monkeypatch):
        (rc, dep), _ = self._run(
            mod,
            monkeypatch,
            [_dep("abc123def", "BUILDING"), _dep("abc123def", "ERROR", err="bad env")],
        )
        assert rc == 1 and dep["errorMessage"] == "bad env"

    def test_timeout_exits_two_and_says_the_stalled_state(self, mod, monkeypatch):
        (rc, _), lines = self._run(
            mod, monkeypatch, [_dep("abc123def", "BUILDING")] * 50, timeout=25
        )
        assert rc == 2 and any("timeout" in line and "BUILDING" in line for line in lines)


class TestProbe:
    def test_probe_does_not_follow_redirects(self, mod, monkeypatch):
        import io
        import urllib.error

        class FakeOpener:
            def open(self, url, timeout=30):
                raise urllib.error.HTTPError(url, 308, "Permanent Redirect", {}, io.BytesIO(b""))

        monkeypatch.setattr(mod.urllib.request, "build_opener", lambda *h: FakeOpener())
        assert mod.http_status("https://example.com/api/x") == 308


class TestMain:
    def test_main_ready_then_probe_mismatch_fails(self, mod, monkeypatch, tmp_path):
        monkeypatch.setattr(mod, "resolve", _fake_resolve())
        monkeypatch.setattr(mod, "wait", lambda *a, **k: (0, _dep("abc", "READY")))
        monkeypatch.setattr(mod, "http_status", lambda url: 308)
        assert (
            mod.main(
                [
                    "x",
                    "--commit",
                    "abc",
                    "--cwd",
                    str(tmp_path),
                    "--probe",
                    "https://e/x/",
                    "--expect",
                    "401",
                ]
            )
            == 1
        )
        monkeypatch.setattr(mod, "http_status", lambda url: 401)
        assert (
            mod.main(
                [
                    "x",
                    "--commit",
                    "abc",
                    "--cwd",
                    str(tmp_path),
                    "--probe",
                    "https://e/x/",
                    "--expect",
                    "401",
                ]
            )
            == 0
        )

    def test_main_without_link_exits_two(self, mod, monkeypatch, tmp_path, capsys):
        """The real resolver runs: an unlinked cwd fails before any API call."""
        monkeypatch.setenv("VERCEL_TOKEN", "env-token")
        monkeypatch.setattr(mod, "wait", lambda *a, **k: pytest.fail("API touched"))
        assert mod.main(["x", "--commit", "abc", "--cwd", str(tmp_path)]) == 2
        err = capsys.readouterr().err
        assert "not linked" in err and "env-token" not in err

    def test_main_build_error_prints_message(self, mod, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(mod, "resolve", _fake_resolve())
        monkeypatch.setattr(
            mod, "wait", lambda *a, **k: (1, _dep("abc", "ERROR", err="CRON_SECRET has whitespace"))
        )
        assert mod.main(["x", "--commit", "abc", "--cwd", str(tmp_path)]) == 1
        assert "CRON_SECRET has whitespace" in capsys.readouterr().out
