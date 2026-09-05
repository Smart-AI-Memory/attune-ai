"""Unit tests for scripts/vercel_probe.py — shapes, never values.

The probe exists because two blank secrets and one silently re-attached
domain each took ten-plus ad-hoc probes on 2026-09-04. These tests pin
that (1) a value is described by length/prefix/digest only, (2) an empty
value is flagged and fails ``--expect``, (3) the env file is parsed the
way ``vercel env pull`` writes it, and (4) the domain report reads the
project-domains endpoint (attachment), not the account domain record.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"
SCRIPT = SCRIPTS / "vercel_probe.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _fake_resolve(token="tok", org="org", pid="prj", name="website"):
    from vercel_common import Link

    return lambda cwd, project_id=None: Link(token, org, project_id or pid, name)


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_vercel_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestShape:
    def test_never_contains_the_value(self, mod):
        s = mod.shape('"re_abcdefghijklmnopqrstuvwxyz0123456789"')
        rendered = repr(s)
        assert "abcdefghijklmnop" not in rendered
        assert s["len"] == 39 and s["prefix"] == "re_" and s["quoted"] is True
        assert len(s["sha12"]) == 12

    def test_empty_value(self, mod):
        s = mod.shape("")
        assert s["len"] == 0 and s["prefix"] == "" and s["sha12"] == "-"

    def test_trailing_newline_is_whitespace(self, mod):
        assert mod.shape("abc\n")["whitespace"] is True
        assert mod.shape("abc")["whitespace"] is False


class TestEnvReport:
    def _fake_pull(self, monkeypatch, mod, values):
        monkeypatch.setattr(mod, "pull_env", lambda env, cwd: values)

    def test_flags_empty_and_fails_expect(self, mod, monkeypatch, tmp_path):
        self._fake_pull(monkeypatch, mod, {"ADMIN_SECRET": "", "CRON_SECRET": "x" * 64})
        lines, rc = mod.env_report("production", tmp_path, ["ADMIN_SECRET"])
        joined = "\n".join(lines)
        assert "ADMIN_SECRET" in joined and "EMPTY" in joined
        assert "MISSING OR EMPTY: ADMIN_SECRET" in joined
        assert rc == 1
        assert "x" * 10 not in joined  # values never rendered

    def test_expect_satisfied_exits_zero(self, mod, monkeypatch, tmp_path):
        self._fake_pull(monkeypatch, mod, {"RESEND_API_KEY": "re_" + "a" * 33})
        lines, rc = mod.env_report("production", tmp_path, ["RESEND_API_KEY"])
        assert rc == 0 and "prefix=re_" in "\n".join(lines)

    def test_missing_variable_fails_expect(self, mod, monkeypatch, tmp_path):
        self._fake_pull(monkeypatch, mod, {})
        _, rc = mod.env_report("production", tmp_path, ["RESEND_API_KEY"])
        assert rc == 1

    def test_sensitive_blank_is_not_flagged_and_expect_is_unverifiable(
        self, mod, monkeypatch, tmp_path
    ):
        # Neon-managed vars are `sensitive`: `env pull` leaves them blank by
        # design, and VERCEL_* system vars are never in the API listing.
        self._fake_pull(monkeypatch, mod, {"PGHOST": "", "VERCEL_URL": "", "ADMIN_SECRET": ""})
        types = {"PGHOST": "sensitive", "ADMIN_SECRET": "encrypted"}
        lines, rc = mod.env_report("production", tmp_path, ["PGHOST", "ADMIN_SECRET"], types)
        joined = "\n".join(lines)
        assert "PGHOST" in joined and "sensitive: not pullable" in joined
        assert "VERCEL_URL" in joined and "(system)" in joined
        assert "ADMIN_SECRET" in joined and "EMPTY" in joined
        assert "UNVERIFIABLE (sensitive): PGHOST" in joined
        assert "MISSING OR EMPTY: ADMIN_SECRET" in joined
        assert rc == 1


class TestPullEnvParsing:
    def test_parses_the_file_vercel_writes(self, mod, monkeypatch, tmp_path):
        def fake_run(cmd, **kw):
            target = Path(cmd[-1])
            target.write_text('# Created by Vercel CLI\nA="1"\nB=""\nnot a var\nC=plain\n')

            class R:
                returncode = 0

            return R()

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        values = mod.pull_env("production", tmp_path)
        assert values == {"A": '"1"', "B": '""', "C": "plain"}

    def test_pull_uses_yes_and_a_fresh_path(self, mod, monkeypatch, tmp_path):
        seen = {}

        def fake_run(cmd, **kw):
            seen["cmd"] = cmd

            class R:
                returncode = 0

            return R()

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        mod.pull_env("preview", tmp_path)
        assert "--yes" in seen["cmd"] and not Path(seen["cmd"][-1]).exists()


class TestDomainsReport:
    def test_reads_attachment_per_project(self, mod, monkeypatch):
        calls = []

        def fake_get(path, token):
            calls.append(path)
            if path.startswith("/v9/projects?"):
                return {
                    "projects": [{"id": "p1", "name": "website"}, {"id": "p2", "name": "shsc-ryan"}]
                }
            if "/p1/domains" in path:
                return {
                    "domains": [
                        {"name": "smartaimemory.com"},
                        {"name": "www.smartaimemory.com", "redirect": "smartaimemory.com"},
                    ]
                }
            return {"domains": []}

        monkeypatch.setattr(mod, "_get", fake_get)
        lines = mod.domains_report("tok", "org")
        joined = "\n".join(lines)
        assert "website" in joined and "(p1)" in joined and "smartaimemory.com [primary]" in joined
        assert "www.smartaimemory.com(->smartaimemory.com)" in joined
        assert "shsc-ryan" in joined
        assert any(
            "/v9/projects/p1/domains" in c for c in calls
        )  # attachment endpoint, not /v4/domains


class TestMain:
    def test_main_prints_env_and_domains_and_exit_code(self, mod, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            mod, "pull_env", lambda env, cwd: {"RESEND_API_KEY": "re_" + "x" * 33, "PGHOST": ""}
        )
        monkeypatch.setattr(mod, "resolve", _fake_resolve())
        monkeypatch.setattr(
            mod, "env_types", lambda t, o, p: {"RESEND_API_KEY": "encrypted", "PGHOST": "sensitive"}
        )
        monkeypatch.setattr(
            mod,
            "domains_report",
            lambda t, o: [
                "domain attachment (project -> domains):",
                "  website (prj) x.com [primary]",
            ],
        )
        rc = mod.main(["x", "--cwd", str(tmp_path), "--expect", "RESEND_API_KEY", "--domains"])
        out = capsys.readouterr().out
        assert (
            rc == 0 and "prefix=re_" in out and "not pullable" in out and "x.com [primary]" in out
        )
        assert "x" * 20 not in out
        assert out.startswith("project [website/prj] team org") and "tok" not in out

    def test_main_unlinked_cwd_exits_two_without_pulling(self, mod, monkeypatch, tmp_path, capsys):
        """The real resolver runs: no ``.vercel/project.json`` in cwd, no parent walk."""
        monkeypatch.setenv("VERCEL_TOKEN", "env-token")
        monkeypatch.setattr(mod, "pull_env", lambda env, cwd: pytest.fail("env pull ran"))
        rc = mod.main(["x", "--cwd", str(tmp_path), "--domains"])
        err = capsys.readouterr().err
        assert rc == 2 and "not linked" in err and "env-token" not in err

    def test_env_types_degrades_to_empty_on_api_error(self, mod, monkeypatch):
        import urllib.error

        def boom(path, token):
            raise urllib.error.URLError("down")

        monkeypatch.setattr(mod, "_get", boom)
        assert mod.env_types("tok", "org", "prj") == {}
        assert mod.env_types("", "org", "prj") == {}

    def test_link_is_cwd_only(self, mod, tmp_path, monkeypatch):
        (tmp_path / ".vercel").mkdir()
        (tmp_path / ".vercel" / "project.json").write_text(
            '{"orgId": "team_1", "projectId": "prj_1", "projectName": "website"}'
        )
        monkeypatch.setenv("VERCEL_TOKEN", "env-token")
        lk = mod.resolve(tmp_path)
        assert (lk.org, lk.project_id, lk.label) == ("team_1", "prj_1", "website/prj_1")
        sub = tmp_path / "website" / "app"
        sub.mkdir(parents=True)
        with pytest.raises(mod.VercelSetupError):  # a parent's link is NOT inherited
            mod.resolve(sub)
