"""Unit tests for scripts/vercel_common.py — link resolution and token expiry.

Pins the two 2026-09-05 worktree hazards: (1) ``.vercel/project.json`` is
honored in the cwd ONLY — a parent's link (the main checkout's stale,
deleted project) is never picked up, and an unlinked cwd raises; (2) an
expired CLI token triggers one ``vercel whoami`` refresh and raises when
still expired, and the token value never appears in any message.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(scope="module")
def mod():
    # A normal import (scripts/ is on sys.path), not spec_from_file_location:
    # the module's dataclass needs itself registered in sys.modules under
    # ``from __future__ import annotations``.
    return importlib.import_module("vercel_common")


def _write_link(d: Path, project_id="prj_1", name="website", org="team_1") -> Path:
    (d / ".vercel").mkdir(parents=True, exist_ok=True)
    p = d / ".vercel" / "project.json"
    p.write_text(json.dumps({"projectId": project_id, "orgId": org, "projectName": name}))
    return p


class TestLink:
    def test_reads_cwd_link_with_name(self, mod, tmp_path):
        _write_link(tmp_path)
        assert mod.link(tmp_path) == ("team_1", "prj_1", "website")

    def test_no_parent_walk(self, mod, tmp_path):
        """A worktree under a linked main checkout must NOT inherit main's link."""
        _write_link(tmp_path, project_id="prj_STALE", name="attune-ai")
        worktree = tmp_path / ".claude" / "worktrees" / "slug"
        worktree.mkdir(parents=True)
        with pytest.raises(mod.VercelSetupError) as ei:
            mod.link(worktree)
        msg = str(ei.value)
        assert "not linked" in msg and "parents are not searched" in msg
        assert "prj_STALE" not in msg

    def test_unlinked_names_the_fix(self, mod, tmp_path):
        with pytest.raises(mod.VercelSetupError) as ei:
            mod.link(tmp_path)
        assert "vercel link --cwd" in str(ei.value) and ".vercel/project.json" in str(ei.value)

    def test_project_id_override_keeps_team_and_drops_name(self, mod, tmp_path):
        _write_link(tmp_path)
        assert mod.link(tmp_path, "prj_other") == ("team_1", "prj_other", "")
        assert mod.link(tmp_path, "prj_1") == ("team_1", "prj_1", "website")

    def test_malformed_link_raises(self, mod, tmp_path):
        p = _write_link(tmp_path)
        p.write_text("{not json")
        with pytest.raises(mod.VercelSetupError, match="unreadable"):
            mod.link(tmp_path)
        p.write_text(json.dumps({"projectName": "x"}))
        with pytest.raises(mod.VercelSetupError, match="lacks orgId/projectId"):
            mod.link(tmp_path)


class TestToken:
    def _auth(self, tmp_path, expires_at, token="tok_secret_value_123"):
        f = tmp_path / "auth.json"
        f.write_text(
            json.dumps({"token": token, "refreshToken": "rt_secret", "expiresAt": expires_at})
        )
        return f

    def test_env_token_wins_and_skips_expiry(self, mod, monkeypatch, tmp_path):
        monkeypatch.setenv("VERCEL_TOKEN", "env-token")
        assert mod.token(tmp_path / "missing.json") == "env-token"

    def test_valid_token_is_returned_without_refresh(self, mod, monkeypatch, tmp_path):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        calls = []
        monkeypatch.setattr(mod, "refresh_cli_token", lambda **kw: calls.append(1) or True)
        f = self._auth(tmp_path, expires_at=int(mod.time.time()) + 3600)
        assert mod.token(f) == "tok_secret_value_123" and calls == []

    def test_expired_token_refreshes_once_then_uses_new_file(self, mod, monkeypatch, tmp_path):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        f = self._auth(tmp_path, expires_at=int(mod.time.time()) - 10)
        calls = []

        def fake_refresh(**kw):
            calls.append(1)
            self._auth(tmp_path, expires_at=int(mod.time.time()) + 3600, token="tok_fresh")
            return True

        monkeypatch.setattr(mod, "refresh_cli_token", fake_refresh)
        assert mod.token(f) == "tok_fresh" and calls == [1]

    def test_still_expired_after_refresh_raises_without_leaking(self, mod, monkeypatch, tmp_path):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        f = self._auth(tmp_path, expires_at=int(mod.time.time()) - 10)
        monkeypatch.setattr(mod, "refresh_cli_token", lambda **kw: False)
        with pytest.raises(mod.VercelSetupError) as ei:
            mod.token(f)
        msg = str(ei.value)
        assert "expired" in msg and "vercel whoami" in msg
        assert "tok_secret_value_123" not in msg and "rt_secret" not in msg

    def test_skew_counts_as_expired(self, mod, tmp_path):
        assert mod._expired({"expiresAt": 1000 + mod.EXPIRY_SKEW_S - 1}, now=1000)
        assert not mod._expired({"expiresAt": 1000 + mod.EXPIRY_SKEW_S + 1}, now=1000)

    def test_millisecond_expiry_is_normalized_and_missing_means_static(self, mod):
        # 2_000_000_000_000 ms == 2_000_000_000 s: later than now -> valid
        assert not mod._expired({"expiresAt": 2_000_000_000_000}, now=1_000_000_000)
        # 1_500_000_000_000 ms == 1_500_000_000 s: earlier than now -> expired
        assert mod._expired({"expiresAt": 1_500_000_000_000}, now=2_000_000_000)
        assert not mod._expired({"token": "static"}, now=1_000_000_000)

    def test_missing_file_raises_naming_the_path(self, mod, monkeypatch, tmp_path):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        f = tmp_path / "auth.json"
        with pytest.raises(mod.VercelSetupError, match="no Vercel token"):
            mod.token(f)

    def test_refresh_runs_whoami_and_discards_output(self, mod, monkeypatch):
        seen = {}

        def fake_run(cmd, **kw):
            seen["cmd"] = cmd
            seen["capture"] = kw.get("capture_output")

            class R:
                returncode = 0
                stdout = "someone@example.com"

            return R()

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        assert mod.refresh_cli_token() is True
        assert seen["cmd"] == ["vercel", "whoami"] and seen["capture"] is True

    def test_refresh_survives_missing_cli(self, mod, monkeypatch):
        def boom(cmd, **kw):
            raise FileNotFoundError("vercel")

        monkeypatch.setattr(mod.subprocess, "run", boom)
        assert mod.refresh_cli_token() is False


class TestResolve:
    def test_resolve_combines_link_and_token(self, mod, monkeypatch, tmp_path):
        _write_link(tmp_path)
        monkeypatch.setenv("VERCEL_TOKEN", "env-token")
        lk = mod.resolve(tmp_path)
        assert (lk.token, lk.org, lk.project_id, lk.project_name) == (
            "env-token",
            "team_1",
            "prj_1",
            "website",
        )
        assert lk.label == "website/prj_1" and "env-token" not in lk.label
