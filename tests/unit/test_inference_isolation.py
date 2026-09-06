"""Failure-sensitive receipts for the default no-inference pytest boundary."""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
from unittest.mock import AsyncMock, Mock

import httpcore
import httpx
import pytest

from tests import _inference_guard as guard


@pytest.fixture(autouse=True)
def intercept_network(monkeypatch):
    """A broken guard must fail these probes without contacting a provider."""
    monkeypatch.setattr(
        httpcore.ConnectionPool,
        "handle_request",
        Mock(side_effect=AssertionError("Unintercepted inference transport")),
    )
    monkeypatch.setattr(
        httpcore.AsyncConnectionPool,
        "handle_async_request",
        AsyncMock(side_effect=AssertionError("Unintercepted inference transport")),
    )
    monkeypatch.setattr(
        http.client.HTTPConnection,
        "send",
        Mock(side_effect=AssertionError("Unintercepted HTTP write")),
    )


@pytest.mark.parametrize(
    "command",
    [
        ["claude", "-p", "test"],
        ["/vendor/claude", "--print", "test"],
        [r"C:\vendor\claude.exe", "-p", "test"],
        ["env", "ANTHROPIC_API_KEY=fake", "claude", "-p", "test"],
        ["node", "/node_modules/@anthropic-ai/claude-code/cli.js", "-p", "test"],
        ["npx", "@anthropic-ai/claude-code", "-p", "test"],
        ["bash", "-lc", "claude -p test"],
        ["cmd.exe", "/c", "claude.exe -p test"],
        ["codex", "exec", "test"],
        ["gemini", "-p", "test"],
        ["ollama", "run", "model"],
        ["curl", "https://api.invalid/v1/messages"],
        b"claude -p test",
        ["/fixture/renamed-cli", "--print", "--output-format", "stream-json"],
    ],
)
def test_inference_command_is_rejected(command) -> None:
    with pytest.raises(guard.InferenceBlocked, match="blocked"):
        guard.check_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["claude", "--version"],
        ["claude", "--help"],
        ["claude", "auth", "status"],
        ["codex", "--version"],
        ["curl", "--version"],
        ["git", "status"],
        ["bash", "-c", "git status"],
    ],
)
def test_non_inference_commands_remain_available(command) -> None:
    guard.check_command(command)


@pytest.mark.parametrize(
    "address", [("api.anthropic.com", 443), ("8.8.8.8", 443), ("2001:db8::1", 443)]
)
def test_external_address_is_rejected(address) -> None:
    with pytest.raises(guard.InferenceBlocked, match="External network"):
        guard.check_address(address)


@pytest.mark.parametrize(
    "address", [("127.0.0.1", 8000), ("::1", 8000), ("localhost", 8000), "/tmp/socket"]
)
def test_local_test_services_remain_available(address) -> None:
    guard.check_address(address)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.invalid/v1/messages",
        "http://localhost:8000/v1/long-term-memory/search",
        "http://127.0.0.1:8000/custom-inference-proxy",
        "http://127.0.0.1:11434/api/generate",
        "https://api.invalid/v1/chat/completions",
        "https://api.invalid/v1/responses?stream=true",
        "https://api.invalid/v1beta/models/example:generateContent",
    ],
)
def test_real_http_inference_endpoint_is_rejected(url) -> None:
    with pytest.raises(guard.InferenceBlocked, match="Inference HTTP"):
        with httpx.Client() as client:
            client.post(url, json={})


@pytest.mark.asyncio
async def test_async_http_inference_endpoint_is_rejected() -> None:
    with pytest.raises(guard.InferenceBlocked, match="Inference HTTP"):
        async with httpx.AsyncClient() as client:
            await client.post("http://127.0.0.1:11434/api/chat", json={})


def test_urllib_transport_cannot_reach_local_inference() -> None:
    with pytest.raises(guard.InferenceBlocked, match="Inference HTTP"):
        http.client.HTTPConnection("127.0.0.1", 11434).request("POST", "/v1/messages")


def test_anthropic_client_is_blocked_before_inference() -> None:
    import anthropic

    with pytest.raises(guard.InferenceBlocked, match="Inference HTTP"):
        anthropic.Anthropic(api_key="fixture", max_retries=0).messages.create(
            model="fixture", max_tokens=1, messages=[{"role": "user", "content": "fixture"}]
        )


@pytest.mark.asyncio
async def test_async_anthropic_client_is_blocked_before_inference() -> None:
    import anthropic

    async with anthropic.AsyncAnthropic(api_key="fixture", max_retries=0) as client:
        with pytest.raises(guard.InferenceBlocked, match="Inference HTTP"):
            await client.messages.create(
                model="fixture", max_tokens=1, messages=[{"role": "user", "content": "fixture"}]
            )


def test_mock_http_transport_still_exercises_real_client() -> None:
    import anthropic

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "msg_fixture",
                "type": "message",
                "role": "assistant",
                "model": "fixture",
                "content": [{"type": "text", "text": "safe"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client = anthropic.Anthropic(api_key="fixture", http_client=transport)
        response = client.messages.create(
            model="fixture", max_tokens=1, messages=[{"role": "user", "content": "fixture"}]
        )
    assert response.content[0].text == "safe"
    assert len(requests) == 1


def test_popen_block_runs_before_process_creation(monkeypatch) -> None:
    execute = Mock()
    monkeypatch.setattr(subprocess.Popen, "_execute_child", execute)
    with pytest.raises(guard.InferenceBlocked, match="Live inference"):
        subprocess.Popen(["claude", "-p", "fixture"])
    execute.assert_not_called()


def test_executable_override_cannot_hide_inference(monkeypatch) -> None:
    execute = Mock()
    monkeypatch.setattr(subprocess.Popen, "_execute_child", execute)
    with pytest.raises(guard.InferenceBlocked, match="Live inference"):
        subprocess.Popen(["alias", "-p", "fixture"], executable="claude")
    execute.assert_not_called()


@pytest.mark.parametrize("flag", ["-I", "-S", "-E"])
def test_python_cannot_disable_child_bootstrap(flag, monkeypatch) -> None:
    execute = Mock()
    monkeypatch.setattr(subprocess.Popen, "_execute_child", execute)
    with pytest.raises(guard.InferenceBlocked, match="Unguarded Python"):
        subprocess.Popen([sys.executable, flag, "-c", "pass"])
    execute.assert_not_called()


@pytest.mark.asyncio
async def test_agent_sdk_cannot_start_a_cli_with_saved_auth(tmp_path, monkeypatch) -> None:
    import claude_agent_sdk
    from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

    # Version discovery is a separate non-inference boundary; avoid executing
    # a platform-specific fixture while retaining the real inference launch.
    monkeypatch.setattr(SubprocessCLITransport, "_check_claude_version", AsyncMock())
    cli = tmp_path / "claude"
    cli.write_text("#!/bin/sh\nprintf '2.1.260 (Claude Code)\\n'\n", encoding="utf-8")
    cli.chmod(0o755)
    saved_auth = tmp_path / ".credentials.json"
    saved_auth.write_text('{"claudeAiOauth":{"accessToken":"fixture"}}', encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fixture")
    # The executable is an inert fixture even if a regression lets it start.
    with pytest.raises(guard.InferenceBlocked, match="Live inference"):
        async for _ in claude_agent_sdk.query(
            prompt="fixture", options=claude_agent_sdk.ClaudeAgentOptions(cli_path=str(cli))
        ):
            pytest.fail("SDK returned a message")
    assert json.loads(saved_auth.read_text())["claudeAiOauth"]["accessToken"] == "fixture"


def _python(script: str, *, env: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ if env is None else env)
    # These cold-interpreter probes declare their own pytest configuration.
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_PLUGINS", None)
    return subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_children_scrub_inherited_and_explicit_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "inherited-fixture")
    old_profile = tmp_path / "saved-profile"
    old_profile.mkdir()
    saved = old_profile / ".credentials.json"
    saved.write_text('{"fixture":"unchanged"}', encoding="utf-8")
    env = {
        **os.environ,
        "ANTHROPIC_AUTH_TOKEN": "explicit-fixture",
        "CLAUDE_CONFIG_DIR": str(old_profile),
        "PYTHONPATH": "",
    }
    result = _python(
        "import os,json; print(json.dumps({k:os.getenv(k) for k in ['ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN','CLAUDE_CONFIG_DIR']}))",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["ANTHROPIC_API_KEY"] == ""
    assert observed["ANTHROPIC_AUTH_TOKEN"] is None
    assert observed["CLAUDE_CONFIG_DIR"] != str(old_profile)
    assert saved.read_text() == '{"fixture":"unchanged"}'
    assert os.environ["ANTHROPIC_API_KEY"] == "inherited-fixture"


def test_python_child_retains_inference_guard_with_replaced_environment() -> None:
    result = _python(
        "import subprocess; subprocess.run(['claude','-p','fixture'])",
        env={"PATH": os.environ["PATH"]},
    )
    assert result.returncode != 0
    assert "Live inference blocked" in result.stderr


def test_python_child_direct_http_is_guarded() -> None:
    result = _python("import httpx; httpx.post('http://127.0.0.1:11434/api/generate',json={})")
    assert result.returncode != 0
    assert "Inference HTTP endpoint blocked" in result.stderr


def test_environment_and_patches_restore_in_child() -> None:
    result = _python(
        "import os; from tests import _inference_guard as g; g.uninstall(); g.uninstall(); g.install(); g.install(); print('restored')"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "restored"


@pytest.mark.parametrize(
    "event,args",
    [
        ("subprocess.Popen", ("claude", ["claude", "-p", "fixture"], None, {})),
        ("os.posix_spawn", ("claude", ["claude", "-p", "fixture"], {})),
        ("os.exec", ("claude", ["claude", "-p", "fixture"], {})),
        ("os.system", (b"claude -p fixture",)),
        ("socket.connect", (None, ("provider.invalid", 443))),
        ("socket.sendto", (None, ("192.0.2.1", 443))),
        ("socket.getaddrinfo", ("provider.invalid", 443, 0, 0, 0)),
    ],
)
def test_audit_barrier_cannot_be_bypassed_by_low_level_calls(event, args) -> None:
    # Emit real CPython audit events without performing the operation itself.
    with pytest.raises(guard.InferenceBlocked, match="blocked"):
        sys.audit(event, *args)


def test_passive_dns_lookup_does_not_count_as_a_connection() -> None:
    sys.audit("socket.getaddrinfo", None, 0, 0, 0, 0)


def test_http_fixtures_require_an_owned_bound_loopback_socket(monkeypatch) -> None:
    # Socket ownership is established by callers binding the server themselves;
    # these unit values exercise rejection and revocation without network I/O.
    sock = Mock()
    sock.getsockname.return_value = ("192.0.2.1", 8999)
    with pytest.raises(guard.InferenceBlocked):
        with guard.loopback_http_fixture(sock):
            pytest.fail("external fixture accepted")
    sock.getsockname.return_value = ("127.0.0.1", 0)
    with pytest.raises(ValueError, match="bound"):
        with guard.loopback_http_fixture(sock):
            pytest.fail("unbound fixture accepted")
    sock.getsockname.return_value = ("127.0.0.1", 8999)
    with guard.loopback_http_fixture(sock):
        guard.check_http_url("http://127.0.0.1:8999/api/generate")
        with pytest.raises(guard.InferenceBlocked):
            guard.check_http_url("http://127.0.0.1:8998/api/generate")
    with pytest.raises(guard.InferenceBlocked):
        guard.check_http_url("http://127.0.0.1:8999/api/generate")


def test_non_inference_http_reaches_intercepted_transport() -> None:
    sock = Mock()
    sock.getsockname.return_value = ("127.0.0.1", 9999)
    with guard.loopback_http_fixture(sock):
        with pytest.raises(AssertionError, match="Unintercepted inference transport"):
            httpx.get("http://127.0.0.1:9999/health")
        with pytest.raises(AssertionError, match="Unintercepted HTTP write"):
            http.client.HTTPConnection("127.0.0.1", 9999).request("GET", "/health")


@pytest.mark.asyncio
async def test_non_inference_async_http_reaches_intercepted_transport() -> None:
    sock = Mock()
    sock.getsockname.return_value = ("127.0.0.1", 9999)
    with guard.loopback_http_fixture(sock):
        with pytest.raises(AssertionError, match="Unintercepted inference transport"):
            async with httpx.AsyncClient() as client:
                await client.get("http://127.0.0.1:9999/health")


def test_positional_popen_environment_is_scrubbed() -> None:
    # Popen's env argument may be positional; exercise a real harmless child.
    with subprocess.Popen(
        [sys.executable, "-c", "import os; print(repr(os.getenv('ANTHROPIC_AUTH_TOKEN')))"],
        -1,
        None,
        None,
        subprocess.PIPE,
        subprocess.PIPE,
        None,
        True,
        False,
        None,
        {"ANTHROPIC_AUTH_TOKEN": "fixture"},
    ) as child:
        stdout, stderr = child.communicate(timeout=15)
    assert child.returncode == 0, stderr
    assert stdout.strip() == b"None"


def test_install_is_idempotent_and_cleanup_restores_saved_values(monkeypatch) -> None:
    original_state = guard._state
    guard.install()
    assert guard._state is original_state
    # A synthetic saved state lets cleanup run without dropping the real
    # suite's transport patches or touching any user file.
    owner, scratch = Mock(), Mock()
    owner.value = "patched"
    monkeypatch.setenv("GUARD_FIXTURE_EXISTING", "changed")
    monkeypatch.setenv("GUARD_FIXTURE_NEW", "new")
    with monkeypatch.context() as local:
        local.setattr(
            guard,
            "_state",
            {
                "patches": [(owner, "value", "original")],
                "environment": {"GUARD_FIXTURE_EXISTING": "saved", "GUARD_FIXTURE_NEW": None},
                "scratch": scratch,
            },
        )
        guard.uninstall()
        guard.uninstall()
        guard._audit("socket.connect", (None, ("provider.invalid", 443)))
        assert owner.value == "original"
        assert os.environ["GUARD_FIXTURE_EXISTING"] == "saved"
        assert "GUARD_FIXTURE_NEW" not in os.environ
        scratch.cleanup.assert_called_once()
    assert guard._state is original_state


@pytest.mark.parametrize("workers,collection", [("0", True), ("0", False), ("2", False)])
def test_real_pytest_installs_guard_before_collection_and_in_workers(tmp_path, workers, collection):
    # Use the actual repository conftest in a cold pytest invocation. First
    # uninstall the inherited bootstrap, so controller coverage is not vacuous.
    fixture = tmp_path / "test_attempt.py"
    attempt = (
        "from unittest.mock import patch\nimport subprocess\n"
        "with patch.object(subprocess.Popen, '_execute_child', "
        "side_effect=AssertionError('process creation reached')):\n"
        "    subprocess.run(['claude', '-p', 'fixture'])\n"
    )
    if not collection:
        attempt = "def test_attempt():\n" + "".join(
            "    " + line for line in attempt.splitlines(True)
        )
    fixture.write_text(attempt, encoding="utf-8")
    args = ["-p", "tests.conftest", str(fixture), "-n", workers, "-q", "-o", "addopts="]
    result = _python(
        "from tests import _inference_guard as g; g.uninstall(); "
        f"import pytest; raise SystemExit(pytest.main({args!r}))"
    )
    assert result.returncode != 0
    assert "InferenceBlocked" in result.stdout, result.stdout + result.stderr
    assert "E   AssertionError: process creation reached" not in result.stdout


def test_requests_cannot_reach_loopback_inference(monkeypatch):
    import requests
    import urllib3

    write = Mock(side_effect=AssertionError("unexpected request"))
    monkeypatch.setattr(urllib3.HTTPConnectionPool, "_make_request", write)
    with pytest.raises(guard.InferenceBlocked, match="Inference HTTP"):
        requests.post("http://127.0.0.1:11434/api/generate", json={})
    write.assert_not_called()
    sock = Mock()
    sock.getsockname.return_value = ("127.0.0.1", 9999)
    with guard.loopback_http_fixture(sock):
        with pytest.raises(AssertionError, match="unexpected request"):
            requests.get("http://127.0.0.1:9999/health")


def test_combined_python_flags_cannot_disable_bootstrap():
    with pytest.raises(guard.InferenceBlocked, match="Unguarded Python"):
        guard.check_command([sys.executable, "-IS", "-c", "pass"])
    guard.check_command([sys.executable, "-u", "-m", "pytest"])
    guard.check_command([sys.executable, "--version"])


def test_low_level_spawn_audit_is_blocked():
    with pytest.raises(guard.InferenceBlocked, match="Live inference"):
        sys.audit("os.spawn", 0, "claude", ["claude", "-p", "fixture"], {})


def test_child_environment_handles_bytes_and_case_variants():
    env = guard._child_env(
        {b"ANTHROPIC_AUTH_TOKEN": b"fixture", "openai_api_key": "fixture"}, guard._state
    )
    assert env["ANTHROPIC_API_KEY"] == env["OPENAI_API_KEY"] == ""
    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert "openai_api_key" not in env


def test_env_split_wrapper_cannot_hide_inference():
    with pytest.raises(guard.InferenceBlocked):
        guard.check_command(["env", "-S", "claude -p fixture"])


def test_native_exec_alias_cannot_hide_inference():
    with pytest.raises(guard.InferenceBlocked):
        sys.audit("os.exec", "/vendor/claude", ["alias", "-p", "fixture"], {})


@pytest.mark.parametrize("command", [["python", "-c", "pass"], '"python" -c "pass"'])
def test_windows_popen_audit_allows_absent_executable_for_non_inference(command):
    guard._audit("subprocess.Popen", (None, command, None, {}))


@pytest.mark.parametrize("command", [["claude", "-p", "fixture"], '"claude" -p "fixture"'])
def test_windows_popen_audit_still_blocks_inference_without_executable(command):
    with pytest.raises(guard.InferenceBlocked, match="Live inference"):
        guard._audit("subprocess.Popen", (None, command, None, {}))


def test_windows_quoted_executable_is_checked_with_non_posix_splitting(monkeypatch):
    split = guard.shlex.split
    monkeypatch.setattr(guard.shlex, "split", lambda command, **kwargs: split(command, posix=False))
    with pytest.raises(guard.InferenceBlocked, match="Live inference"):
        guard._audit(
            "subprocess.Popen", (None, r'"C:\Program Files\Claude\claude.exe" -p fixture', None, {})
        )
    with pytest.raises(guard.InferenceBlocked, match="Unguarded Python"):
        guard._audit(
            "subprocess.Popen", (None, r'"C:\Program Files\Python\python.exe" -I -c pass', None, {})
        )


def test_cold_child_does_not_inherit_parent_pytest_configuration(monkeypatch):
    monkeypatch.setenv("PYTEST_ADDOPTS", "--deliberately-invalid-parent-option")
    monkeypatch.setenv("PYTEST_PLUGINS", "missing_parent_plugin")
    result = _python(
        "import os; assert 'PYTEST_ADDOPTS' not in os.environ; "
        "assert 'PYTEST_PLUGINS' not in os.environ"
    )
    assert result.returncode == 0, result.stderr


def test_live_ams_is_deselected_without_a_collection_network_probe():
    result = _python(
        "import pytest; raise SystemExit(pytest.main(["
        "'tests/memory/test_ams_backend_integration.py','--collect-only','-q','-n','0']))"
    )
    assert result.returncode == 5, result.stdout + result.stderr
    assert "6 deselected" in result.stdout
    assert "InferenceBlocked" not in result.stdout + result.stderr


def test_bootstrap_failure_exits_before_child_code(tmp_path, monkeypatch):
    from pathlib import Path

    bootstrap = Path(guard._state["bootstrap"]) / "sitecustomize.py"
    broken = bootstrap.read_text(encoding="utf-8").replace(
        repr(str(Path(guard.__file__).resolve())), repr(str(tmp_path / "missing_guard.py"))
    )
    assert broken != bootstrap.read_text(encoding="utf-8")
    (tmp_path / "sitecustomize.py").write_text(broken, encoding="utf-8")
    monkeypatch.setitem(guard._state, "bootstrap", str(tmp_path))
    result = _python("print('unguarded child ran')")
    assert result.returncode == 86
    assert "isolation bootstrap failed" in result.stderr
    assert "unguarded child ran" not in result.stdout
