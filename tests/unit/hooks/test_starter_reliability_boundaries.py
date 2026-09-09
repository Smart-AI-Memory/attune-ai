"""Receipts for repository identity, local spec reads, and process deadlines."""

import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from attune.hooks.scripts import starter_reconciler as hook


@pytest.fixture(autouse=True)
def worktree_source():
    """An installed wheel cannot serve as evidence for this branch."""
    assert Path(hook.__file__).resolve() == (
        Path(__file__).resolve().parents[3] / "src/attune/hooks/scripts/starter_reconciler.py"
    )


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.mark.parametrize("host", ["github.com", "github.company.example"])
@pytest.mark.skipif(os.name == "nt", reason="POSIX gh executable fixture")
def test_actual_pr_command_overrides_ambient_repository(tmp_path, monkeypatch, capsys, host):
    """Opposite fixture states make querying the wrong repo observably incorrect."""
    _git(tmp_path, "init", "--quiet")
    _git(tmp_path, "remote", "add", "origin", f"https://{host}/local/project.git")
    starter = tmp_path / "starter.md"
    starter.write_text(
        f"---\nrepo: local/project\nrepo_host: {host}\n---\nMerge local/project#49\n"
    )
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    capture = tmp_path / "gh-args.json"
    gh = fakebin / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        f"with open({str(capture)!r}, 'w') as output: json.dump(sys.argv[1:], output)\n"
        "args = sys.argv[1:]\n"
        "repo = args[args.index('--repo') + 1] if '--repo' in args else os.environ['GH_REPO']\n"
        f"print('OPEN' if repo == '{host}/local/project' else 'MERGED')\n"
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", str(fakebin) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("GH_REPO", "foreign/project")
    monkeypatch.setenv("GH_HOST", "foreign.example")

    assert hook._reconcile_and_emit(starter, "project", tmp_path)
    output = capsys.readouterr().out
    assert "#49 OPEN" in output
    assert "MERGED" not in output
    args = json.loads(capture.read_text())
    assert args[args.index("--repo") + 1] == f"{host}/local/project"


@pytest.mark.parametrize(
    "remote, expected",
    [
        ("git@github.com:Owner/Repo.git", "github.com/owner/repo"),
        ("ssh://git@git.example/Owner/Repo.git", "git.example/owner/repo"),
        ("../foreign/project", None),
        ("file:///foreign/project", None),
        ("https://[bad/owner/repo", None),
        ("https://github.com/owner", None),
    ],
)
def test_repository_target_preserves_host_or_is_unverified(tmp_path, monkeypatch, remote, expected):
    monkeypatch.setattr(hook, "_run", lambda *a: subprocess.CompletedProcess([], 0, remote))
    assert hook.repo_target(tmp_path) == expected


def test_unknown_repository_never_invokes_gh(monkeypatch):
    def unexpected(*args):
        pytest.fail("an unidentified repository must not reach gh")

    monkeypatch.setattr(hook, "_run", unexpected)
    assert hook.check_pr(49, None) == "unverified"


def test_stamped_host_cannot_follow_a_different_origin(tmp_path, monkeypatch, capsys):
    """Same owner/name on a new host is a different repository, using real Git."""
    _git(tmp_path, "init", "--quiet")
    _git(tmp_path, "remote", "add", "origin", "https://github.com/local/project.git")
    starter = tmp_path / "starter.md"
    starter.write_text("Merge local/project#49\n")
    hook.stamp_provenance(starter, tmp_path)
    provenance, _ = hook.parse_provenance(starter.read_text())
    assert provenance["repo_host"] == "github.com"
    _git(tmp_path, "remote", "set-url", "origin", "https://enterprise.example/local/project.git")
    queried = []
    monkeypatch.setattr(hook, "check_pr", lambda *args: queried.append(args) or "MERGED")
    assert hook._reconcile_and_emit(starter, "project", tmp_path)
    output = capsys.readouterr().out
    assert "SKIPPED (cross-repo)" in output
    assert "MERGED" not in output
    assert queried == []


def test_legacy_hostless_stamp_requires_revalidation(tmp_path, monkeypatch, capsys):
    _git(tmp_path, "init", "--quiet")
    _git(tmp_path, "remote", "add", "origin", "https://github.com/local/project.git")
    starter = tmp_path / "starter.md"
    starter.write_text("---\nrepo: local/project\n---\nMerge #49\n")
    queried = []
    monkeypatch.setattr(hook, "check_pr", lambda *args: queried.append(args) or "MERGED")
    assert hook._reconcile_and_emit(starter, "project", tmp_path)
    assert "Repository host unverified" in capsys.readouterr().out
    assert queried == []


def test_verified_target_is_carried_to_query_without_rediscovery(tmp_path, monkeypatch, capsys):
    starter = tmp_path / "starter.md"
    starter.write_text("---\nrepo: local/project\nrepo_host: github.com\n---\nMerge #49\n")
    identities = iter(["github.com/local/project", "enterprise.example/local/project"])
    monkeypatch.setattr(hook, "repo_target", lambda root: next(identities))
    monkeypatch.setattr(hook, "merged_prs_on_main", lambda cwd: [])
    queried = []
    monkeypatch.setattr(hook, "check_pr", lambda num, cwd, target: queried.append(target) or "OPEN")
    assert hook._reconcile_and_emit(starter, "project", tmp_path)
    assert "#49 OPEN" in capsys.readouterr().out
    assert queried == ["github.com/local/project"]


def test_github_url_cannot_become_enterprise_pr(monkeypatch, tmp_path):
    monkeypatch.setattr(hook, "repo_target", lambda root: "enterprise.example/local/project")
    calls = []
    monkeypatch.setattr(hook, "check_pr", lambda *args: calls.append(args) or "MERGED")
    results = hook.reconcile("https://github.com/local/project/pull/49", None, tmp_path)
    assert calls == []
    assert results["unverified_refs"] == ["local/project#49"]


@pytest.mark.parametrize("prefix", ["../foreign/", "/other/", "https://example.com/"])
def test_foreign_spec_cannot_read_opposite_local_status(tmp_path, prefix):
    local = tmp_path / "local"
    foreign = tmp_path / "foreign"
    for root, status in [(local, "shipped"), (foreign, "active")]:
        spec = root / "docs/specs/shared-feature"
        spec.mkdir(parents=True)
        (spec / "tasks.md").write_text(f"**Status:** {status}\n")
    reference = prefix + "docs/specs/shared-feature/tasks.md"
    assert hook.check_specs(reference, local) == {reference: "unverified (nonlocal path)"}
    assert hook.check_specs("./docs/specs/shared-feature/tasks.md", local) == {
        "shared-feature": "terminal:shipped"
    }


@pytest.mark.parametrize("symlink_phase", [False, True])
def test_symlinked_spec_cannot_read_outside_repository(tmp_path, symlink_phase):
    root = tmp_path / "repo"
    specs = root / "docs/specs"
    specs.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "tasks.md").write_text("**Status:** shipped\n")
    try:
        if symlink_phase:
            (specs / "shared").mkdir()
            (specs / "shared/tasks.md").symlink_to(outside / "tasks.md")
        else:
            (specs / "shared").symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name == "nt":
            pytest.skip("symlink creation unavailable")
        raise
    assert hook.check_specs("docs/specs/shared", root) == {"shared": "unverified (nonlocal path)"}


def test_spec_resolve_failure_preserves_other_findings(tmp_path, monkeypatch):
    specs = tmp_path / "docs/specs"
    specs.mkdir(parents=True)
    try:
        (specs / "loop").symlink_to("loop", target_is_directory=True)
    except OSError:
        if os.name == "nt":
            pytest.skip("symlink creation unavailable")
        raise
    monkeypatch.setattr(hook, "pypi_latest", lambda pkg: "1.2.3")
    results = hook.reconcile("docs/specs/loop and docs/specs/missing", "fixture-package", tmp_path)
    assert results["specs"] == {"loop": "unverified (read failed)", "missing": "missing"}
    assert results["pypi"] == "1.2.3"


def test_failed_version_lookup_remains_visible(tmp_path, monkeypatch, capsys):
    starter = tmp_path / "starter.md"
    starter.write_text("---\nrepo: local/project\nrepo_host: github.com\n---\nShip 1.2.3\n")
    monkeypatch.setattr(hook, "repo_slug", lambda root: "local/project")
    monkeypatch.setattr(hook, "repo_target", lambda root: "github.com/local/project")
    monkeypatch.setattr(hook, "_package_name", lambda root: "fixture-package")
    monkeypatch.setattr(hook, "pypi_latest", lambda pkg: None)
    assert hook._reconcile_and_emit(starter, "project", tmp_path)
    assert "PyPI fixture-package: unverified (lookup failed)" in capsys.readouterr().out


def test_expired_budget_stays_visible_and_starts_no_process(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "_DEADLINE", time.monotonic() - 1)
    calls = []
    monkeypatch.setattr(hook.subprocess, "run", lambda *a, **k: calls.append(a))
    result = hook.reconcile("Ship 1.2.3", "fixture-package", tmp_path)
    assert "unverified (budget exhausted)" in hook.format_banner(result, "project", tmp_path)
    assert calls == []


@pytest.mark.parametrize("payload", ["broken", "null", "{}", '""'])
def test_worker_output_must_be_a_nonempty_version(monkeypatch, payload):
    monkeypatch.setattr(hook, "_run", lambda *a: subprocess.CompletedProcess([], 0, payload))
    assert hook.pypi_latest("fixture-package") is None


def test_worker_result_and_failure(monkeypatch):
    monkeypatch.setattr(hook, "_run", lambda *a: subprocess.CompletedProcess([], 0, '"1.2.3"'))
    assert hook.pypi_latest("fixture-package") == "1.2.3"
    monkeypatch.setattr(hook, "_run", lambda *a: subprocess.CompletedProcess([], 1, ""))
    assert hook.pypi_latest("fixture-package") is None


@pytest.mark.parametrize("payload", [b"{}", b"[]", b"broken", b'{"info":{"version":null}}'])
def test_invalid_pypi_response_is_unverified(monkeypatch, payload):
    monkeypatch.setattr(hook.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(payload))
    assert hook._fetch_pypi_latest("fixture-package") is None
    assert hook._fetch_pypi_latest("../bad-package") is None


@pytest.mark.parametrize("delay", [0.0, 0.15])
def test_real_hook_exits_before_timeout_with_slow_response_body(tmp_path, record_property, delay):
    """Exercise real HTTP, worker termination, and interpreter exit together.

    The worker owns its HTTP fixture so the inherited inference guard can
    authorize exactly that socket. Only worker launch and URL routing are
    adapted; reconciliation, HTTP parsing, and the worker entrypoint are real.
    """
    script = Path(hook.__file__).resolve()
    marker = tmp_path / "response-started"
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import importlib.util, json, runpy, sys, threading, time, urllib.request\n"
        "from pathlib import Path\n"
        "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\n"
        f"script = Path({str(script)!r})\n"
        "sys.path.insert(0, str(script.parent))\n"
        "if '--pypi-query' in sys.argv:\n"
        "    from tests._inference_guard import loopback_http_fixture\n"
        "    class SlowResponse(BaseHTTPRequestHandler):\n"
        "        def do_GET(self):\n"
        f"            Path({str(marker)!r}).write_text('received')\n"
        '            payload = b\'{"info":{"version":"1.2.3"}}\' + b\' \' * 100\n'
        "            self.send_response(200)\n"
        "            self.send_header('Content-Length', str(len(payload)))\n"
        "            self.end_headers()\n"
        "            for byte in payload:\n"
        "                self.wfile.write(bytes([byte]))\n"
        "                self.wfile.flush()\n"
        f"                time.sleep({delay})\n"
        "        def log_message(self, *args): pass\n"
        "    server = ThreadingHTTPServer(('127.0.0.1', 0), SlowResponse)\n"
        "    threading.Thread(target=server.serve_forever, daemon=True).start()\n"
        "    original = urllib.request.urlopen\n"
        "    def fixture_urlopen(url, *args, **kwargs):\n"
        "        return original(f'http://127.0.0.1:{server.server_port}/json', *args, **kwargs)\n"
        "    urllib.request.urlopen = fixture_urlopen\n"
        "    with loopback_http_fixture(server.socket):\n"
        "        runpy.run_path(str(script), run_name='__main__')\n"
        "else:\n"
        "    spec = importlib.util.spec_from_file_location('starter_reconciler', script)\n"
        "    hook = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(hook)\n"
        "    hook.__file__ = __file__  # Route its worker through the HTTP fixture.\n"
        "    sys.exit(hook.main())\n"
    )
    root = tmp_path / "repo"
    (root / ".attune").mkdir(parents=True)
    _git(root, "init", "--quiet")
    (root / "pyproject.toml").write_text('[project]\nname = "fixture-package"\n')
    (root / ".attune/next_session_starter.md").write_text("Ship 1.2.3\n")
    env = dict(os.environ, ATTUNE_SDK_GATE_OVERRIDE="1")
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(probe)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    elapsed = time.monotonic() - started
    record_property("hook_process_elapsed_seconds", round(elapsed, 3))
    assert marker.is_file(), f"worker missed HTTP fixture: {result.stdout!r} {result.stderr!r}"
    assert result.returncode == 0
    if delay:
        assert "PyPI fixture-package: unverified" in result.stdout
        assert "latest=1.2.3" not in result.stdout
    else:
        assert "PyPI fixture-package latest=1.2.3" in result.stdout
    assert elapsed < 8, f"interpreter exit took {elapsed:.3f}s: {result.stderr}"
