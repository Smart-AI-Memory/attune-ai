"""Process-local pytest barriers against accidental live inference.

Installed before application imports, inherited by ordinary Python children,
and never installed by production code. This is not a sandbox for hostile tests.
"""

from __future__ import annotations

import atexit
import functools
import http.client
import ipaddress
import os
import shlex
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class InferenceBlocked(BaseException):
    """Escape application error/fallback handlers when a test attempts inference."""


_CREDENTIALS = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_ADMIN_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "COHERE_API_KEY",
        "MISTRAL_API_KEY",
        "GROQ_API_KEY",
        "HF_TOKEN",
        "HUGGINGFACEHUB_API_TOKEN",
        "ANTHROPIC_PROFILE",
        "ANTHROPIC_IDENTITY_TOKEN_FILE",
        "ANTHROPIC_FEDERATION_RULE_ID",
        "ANTHROPIC_ORGANIZATION_ID",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "AZURE_CLIENT_SECRET",
    }
)
_INFERENCE_CLI = frozenset(
    {
        "claude",
        "claude.exe",
        "claude-code",
        "codex",
        "codex.exe",
        "gemini",
        "ollama",
        "llm",
        "agy",
        "antigravity",
    }
)
_HTTP_TOOLS = frozenset({"curl", "curl.exe", "wget", "wget.exe", "http", "https"})
_READ_ONLY = {("--version",), ("-v",), ("--help",), ("-h",), ("auth", "status"), ("plugin", "list")}
_state: dict[str, Any] | None = None
_http_fixtures: set[tuple[str, int]] = set()


@contextmanager
def loopback_http_fixture(sock: Any):
    """Permit HTTP only to a loopback socket bound and owned by this test.

    Keep the socket open for the entire context, even for refusal tests.
    This cannot authorize an already-running model's occupied port.
    """
    address = sock.getsockname()[:2]
    check_address(address)
    if not address[1]:
        raise ValueError("Fixture socket must already be bound")
    _http_fixtures.add(address)
    try:
        yield
    finally:
        _http_fixtures.remove(address)


def check_command(command: Any) -> None:
    """Reject inference executables, including shell/env/node/SDK wrappers."""
    if isinstance(command, str | bytes):
        parts = shlex.split(os.fsdecode(command), posix=os.name != "nt")
        # Non-POSIX splitting retains Windows command-line quotes.
        parts = [p[1:-1] if len(p) > 1 and p[0] == p[-1] and p[0] in "\"'" else p for p in parts]
    else:
        parts = [os.fsdecode(p) for p in command]
    if "--print" in parts and "stream-json" in parts:
        raise InferenceBlocked("Live inference blocked: mock the Agent SDK transport")
    for index, part in enumerate(parts):
        name = part.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if name.startswith("python"):
            for flag in parts[index + 1 :]:
                if not flag.startswith("-") or flag in {"-c", "-m"}:
                    break
                if not flag.startswith("--") and set(flag[1:]) & {"I", "S", "E"}:
                    raise InferenceBlocked("Unguarded Python child blocked: retain test isolation")
        if (
            name in _INFERENCE_CLI
            or "@anthropic-ai/claude-code" in part
            or (name == "cli.js" and "claude" in part.lower())
        ):
            if tuple(parts[index + 1 :]) not in _READ_ONLY:
                raise InferenceBlocked(
                    "Live inference blocked: mock the LLM/CLI boundary in this test"
                )
        if name in _HTTP_TOOLS:
            if tuple(parts[index + 1 :]) not in {("--version",), ("--help",)}:
                raise InferenceBlocked(
                    "Network CLI blocked: use an intercepted HTTP client in tests"
                )
        if name == "env" and "-S" in parts[index + 1 :]:
            check_command(parts[parts.index("-S", index + 1) + 1])
        # A shell's command string is one argv item; inspect its contents too.
        if name in {"sh", "bash", "zsh", "cmd", "cmd.exe", "powershell", "pwsh"}:
            tail = parts[index + 1 :]
            for flag in ("-c", "-lc", "/c", "-Command"):
                if flag in tail and tail.index(flag) + 1 < len(tail):
                    check_command(tail[tail.index(flag) + 1])


def check_address(address: Any) -> None:
    """Permit local test services; block real external sockets before connection."""
    if not isinstance(address, tuple):
        return  # Unix-domain sockets, including subprocess/xdist pipes.
    host = os.fsdecode(address[0])
    if host.lower() == "localhost":
        return
    try:
        allowed = ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        allowed = False
    if not allowed:
        raise InferenceBlocked("External network blocked: mock the provider transport in this test")


def check_http_url(url: str) -> None:
    """Deny unregistered real HTTP: a local proxy can invoke remote inference."""
    parsed = urlsplit(str(url))
    if (parsed.hostname, parsed.port) in _http_fixtures:
        return
    raise InferenceBlocked(
        "Inference HTTP endpoint blocked: use a mock transport or owned HTTP fixture"
    )


def _audit(event: str, args: tuple) -> None:
    if _state is None:
        return
    if event in {"subprocess.Popen", "os.posix_spawn", "os.exec"}:
        check_command(args[1])
        if args[0] is not None:  # Windows Popen can omit the executable override.
            command = args[1]
            tail = [command] if isinstance(command, str | bytes) else command[1:]
            check_command([args[0], *tail])
    elif event == "os.spawn":
        check_command(args[2])
    elif event == "os.system":
        check_command(args[0])
    elif event in {"socket.connect", "socket.sendto"}:
        check_address(args[-1])
    elif event == "socket.getaddrinfo":
        if args[0] is not None:  # Passive bind lookup does not connect anywhere.
            check_address((args[0], args[1]))


# CPython otherwise hides audit callback bodies from coverage's tracing hook.
_audit.__cantrace__ = True


def _child_env(env: Any, state: dict) -> dict:
    result = {
        os.fsdecode(k): os.fsdecode(v) for k, v in (os.environ if env is None else env).items()
    }
    for name in list(result):
        if name.upper() in _CREDENTIALS:
            del result[name]
    result["ANTHROPIC_API_KEY"] = ""
    result["OPENAI_API_KEY"] = ""
    result["CLAUDE_CONFIG_DIR"] = state["profile"]
    existing = result.get("PYTHONPATH", "")
    result["PYTHONPATH"] = os.pathsep.join(filter(None, [state["bootstrap"], existing]))
    return result


def install() -> None:
    """Install barriers in this test interpreter without editing user auth files."""
    global _state
    if _state is not None:
        return
    scratch = tempfile.TemporaryDirectory(prefix="attune-inference-guard-")
    root = Path(scratch.name).resolve()
    bootstrap = root / "sitecustomize.py"
    if bootstrap.resolve().parent != root:
        raise RuntimeError("Unsafe test bootstrap path")
    source = Path(__file__).resolve()
    bootstrap.write_text(
        "import importlib.util, os, sys\n"
        "try:\n"
        f"    s = importlib.util.spec_from_file_location('tests._inference_guard', {str(source)!r})\n"
        "    m = importlib.util.module_from_spec(s)\n"
        "    sys.modules[s.name] = m\n"
        "    s.loader.exec_module(m)\n"
        "    m.install()\n"
        "except BaseException:\n"
        "    sys.stderr.write('Test inference isolation bootstrap failed\\n')\n"
        "    os._exit(86)\n",
        encoding="utf-8",
    )
    managed = _CREDENTIALS | {"CLAUDE_CONFIG_DIR", "PYTHONPATH"}
    state = {
        "scratch": scratch,
        "bootstrap": str(root),
        "profile": str(root / "claude"),
        "environment": {k: os.environ.get(k) for k in managed},
        "patches": [],
    }
    _state = state
    os.environ.update(_child_env(None, state))
    for key in _CREDENTIALS - {"ANTHROPIC_API_KEY", "OPENAI_API_KEY"}:
        os.environ.pop(key, None)
    sys.addaudithook(_audit)

    def patch(owner: Any, name: str, replacement: Any) -> None:
        state["patches"].append((owner, name, getattr(owner, name)))
        setattr(owner, name, replacement)

    original_init = subprocess.Popen.__init__

    @functools.wraps(original_init)
    def guarded_init(self: Any, args: Any, *pos: Any, **kwargs: Any) -> None:
        check_command(args)
        executable = kwargs.get("executable") or (pos[1] if len(pos) > 1 else None)
        if executable:
            check_command([executable, *([args] if isinstance(args, str) else args[1:])])
        # env is positional argument 10 in Popen; preserve both calling styles.
        if len(pos) > 9:
            mutable = list(pos)
            mutable[9] = _child_env(mutable[9], state)
            pos = tuple(mutable)
        else:
            kwargs["env"] = _child_env(kwargs.get("env"), state)
        original_init(self, args, *pos, **kwargs)

    patch(subprocess.Popen, "__init__", guarded_init)
    original_request = http.client.HTTPConnection.request

    @functools.wraps(original_request)
    def guarded_request(self: Any, method: str, url: str, *args: Any, **kwargs: Any) -> Any:
        check_http_url(f"http://{self.host}:{self.port}{url}" if url.startswith("/") else url)
        return original_request(self, method, url, *args, **kwargs)

    patch(http.client.HTTPConnection, "request", guarded_request)
    import urllib3

    original_urlopen = urllib3.HTTPConnectionPool.urlopen

    @functools.wraps(original_urlopen)
    def guarded_urlopen(self: Any, method: str, url: str, *args: Any, **kwargs: Any) -> Any:
        check_http_url(f"http://{self.host}:{self.port}{url}" if url.startswith("/") else url)
        return original_urlopen(self, method, url, *args, **kwargs)

    patch(urllib3.HTTPConnectionPool, "urlopen", guarded_urlopen)
    # MockTransport stays untouched. Both real httpx transports are blocked at
    # dispatch, before even a loopback model or API proxy can receive a request.
    import httpx

    original_sync = httpx.HTTPTransport.handle_request
    original_async = httpx.AsyncHTTPTransport.handle_async_request

    def guarded_sync(self: Any, request: Any) -> Any:
        check_http_url(str(request.url))
        return original_sync(self, request)

    async def guarded_async(self: Any, request: Any) -> Any:
        check_http_url(str(request.url))
        return await original_async(self, request)

    patch(httpx.HTTPTransport, "handle_request", guarded_sync)
    patch(httpx.AsyncHTTPTransport, "handle_async_request", guarded_async)
    atexit.register(uninstall)


def uninstall() -> None:
    """Restore only this interpreter's settings after pytest finishes."""
    global _state
    state, _state = _state, None
    if state is None:
        return
    for owner, name, original in reversed(state["patches"]):
        setattr(owner, name, original)
    for key, value in state["environment"].items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    state["scratch"].cleanup()
