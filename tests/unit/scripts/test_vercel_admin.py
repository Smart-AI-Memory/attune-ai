"""Unit tests for scripts/vercel_admin.py — one mutation per call, no leaks.

Pins: each subcommand maps to exactly one API call with the right
method/path/body; dry-run performs nothing; an empty value is refused;
generate+store writes a 0600 file and prints only length/digest; API
errors surface as exit 1 with the message.
"""

from __future__ import annotations

import importlib.util
import os
import stat
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "vercel_admin.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_vercel_admin", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def linked(mod, monkeypatch, tmp_path):
    """A linked cwd, a token, and a recorder in place of the network."""
    monkeypatch.setattr(mod, "_token", lambda: "tok")
    monkeypatch.setattr(mod, "_link", lambda cwd: ("org_1", "prj_1"))
    calls = []

    def fake_request(method, path, token, body=None):
        calls.append((method, path, body))
        assert token == "tok"
        if method == "GET" and "/env?" in path:
            return {"envs": [{"id": "env_9", "key": "ADMIN_SECRET", "target": ["production"]}]}
        return {"ok": True}

    monkeypatch.setattr(mod, "_request", fake_request)
    return calls, tmp_path


class TestOps:
    def test_env_set_upserts_encrypted_for_target(self, mod):
        desc, method, path, body = mod.op_env_set("o", "p", "K", "v" * 10, "production")
        assert method == "POST" and "/v10/projects/p/env?" in path and "upsert=true" in path
        assert body == {
            "key": "K",
            "value": "v" * 10,
            "type": "encrypted",
            "target": ["production"],
        }
        assert "v" * 10 not in desc and "len=10" in desc

    def test_domain_attach_with_redirect(self, mod):
        _, method, path, body = mod.op_domain_attach("o", "p", "www.x.com", "x.com")
        assert method == "POST" and path.startswith("/v10/projects/p/domains")
        assert body == {"name": "www.x.com", "redirect": "x.com", "redirectStatusCode": 308}

    def test_domain_redirect_clear_makes_primary(self, mod):
        _, method, _, body = mod.op_domain_redirect("o", "p", "x.com", None)
        assert method == "PATCH" and body == {"redirect": None}


class TestMain:
    def test_dry_run_performs_nothing(self, mod, linked, capsys):
        calls, tmp = linked
        rc = mod.main(["x", "--cwd", str(tmp), "--dry-run", "domain-detach", "x.com"])
        assert rc == 0 and calls == []
        assert "DRY-RUN domain-detach x.com" in capsys.readouterr().out

    def test_domain_detach_is_one_delete(self, mod, linked):
        calls, tmp = linked
        assert mod.main(["x", "--cwd", str(tmp), "domain-detach", "x.com"]) == 0
        assert calls == [("DELETE", "/v9/projects/prj_1/domains/x.com?teamId=org_1", None)]

    def test_env_rm_resolves_id_then_deletes(self, mod, linked):
        calls, tmp = linked
        assert mod.main(["x", "--cwd", str(tmp), "env-rm", "ADMIN_SECRET"]) == 0
        assert [c[0] for c in calls] == ["GET", "DELETE"]
        assert calls[1][1] == "/v9/projects/prj_1/env/env_9?teamId=org_1"

    def test_env_rm_missing_name_fails_without_mutation(self, mod, linked, capsys):
        calls, tmp = linked
        assert mod.main(["x", "--cwd", str(tmp), "env-rm", "NOPE"]) == 1
        assert [c[0] for c in calls] == ["GET"]
        assert "no NOPE" in capsys.readouterr().err

    def test_env_set_refuses_empty(self, mod, linked, capsys):
        calls, tmp = linked
        f = tmp / "empty"
        f.write_text("\n")
        assert mod.main(["x", "--cwd", str(tmp), "env-set", "K", "--from-file", str(f)]) == 1
        assert calls == [] and "EMPTY" in capsys.readouterr().err

    def test_env_set_generate_and_store_never_prints_value(self, mod, linked, capsys):
        calls, tmp = linked
        store = tmp / "secrets" / "site.env"
        assert (
            mod.main(["x", "--cwd", str(tmp), "env-set", "K", "--generate", "--store", str(store)])
            == 0
        )
        body = calls[0][2]
        value = body["value"]
        assert len(value) == 64 and body["type"] == "encrypted"
        out = capsys.readouterr().out
        assert value not in out and "len=64" in out and "sha=" in out
        assert store.read_text() == f"K={value}\n"
        if os.name != "nt":  # Windows has no POSIX mode bits (reports 0o666)
            assert stat.S_IMODE(os.stat(store).st_mode) == 0o600

    def test_store_replaces_existing_line(self, mod, tmp_path):
        p = tmp_path / "x.env"
        p.write_text("A=1\nK=old\n")
        mod.store_locally(p, "K", "new")
        assert p.read_text() == "A=1\nK=new\n"

    def test_api_error_exits_one_with_message(self, mod, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(mod, "_token", lambda: "tok")
        monkeypatch.setattr(mod, "_link", lambda cwd: ("o", "p"))
        monkeypatch.setattr(
            mod,
            "_request",
            lambda *a, **k: {"error": {"message": "domain is in use"}, "status": 409},
        )
        assert mod.main(["x", "--cwd", str(tmp_path), "domain-attach", "x.com"]) == 1
        assert "domain is in use" in capsys.readouterr().err

    def test_no_link_exits_two(self, mod, monkeypatch, tmp_path):
        monkeypatch.setattr(mod, "_token", lambda: "")
        monkeypatch.setattr(mod, "_link", lambda cwd: ("", ""))
        assert mod.main(["x", "--cwd", str(tmp_path), "domain-detach", "x.com"]) == 2
