"""Tests for ``attune memory-agent`` (cmd_memory_agent).

The agent loop runs the raw ``anthropic`` SDK ``tool_runner`` with attune's
Memory-tool bridge. These tests mock the anthropic client + the bridge, so
no API key or network is needed for the unit path; a guarded live
round-trip is provided separately and auto-skips without a key.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from attune.cli_commands import memory_agent as ma


def _args(**kw):
    base = {
        "prompt": "remember that the sky is blue",
        "path": None,
        "model": None,
        "user_id": None,
        "max_tokens": None,
    }
    base.update(kw)
    return SimpleNamespace(**base)


class _Block(SimpleNamespace):
    pass


class _Msg(SimpleNamespace):
    pass


class _FakeRunner:
    def __init__(self, messages):
        self._messages = messages

    def __iter__(self):
        return iter(self._messages)


class _RaisingRunner:
    def __iter__(self):
        raise RuntimeError("api blew up mid-run")


def _install_fake_anthropic(
    monkeypatch, *, runner=None, raise_on_construct=False, has_tool_runner=True
):
    import anthropic

    captured = {}

    def tool_runner(**kwargs):
        captured["kwargs"] = kwargs
        if raise_on_construct:
            raise RuntimeError("invalid x-api-key")
        return runner if runner is not None else _FakeRunner([])

    messages = SimpleNamespace(tool_runner=tool_runner) if has_tool_runner else SimpleNamespace()
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: client)
    return captured


@pytest.fixture
def _key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")


@pytest.fixture
def _tool(monkeypatch):
    """Stub make_memory_tool so no real backend/anthropic-base is needed."""
    import attune.memory as m

    monkeypatch.setattr(m, "make_memory_tool", lambda **kw: object())


class TestPreconditions:
    def test_missing_prompt_returns_2(self):
        assert ma.cmd_memory_agent(_args(prompt=None)) == 2

    def test_missing_api_key_returns_2(self, monkeypatch, capsys):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        rc = ma.cmd_memory_agent(_args())
        assert rc == 2
        assert "ANTHROPIC_API_KEY" in capsys.readouterr().out

    def test_no_tool_runner_on_sdk_returns_2(self, monkeypatch, capsys, _key, _tool):
        _install_fake_anthropic(monkeypatch, has_tool_runner=False)
        rc = ma.cmd_memory_agent(_args())
        assert rc == 2
        assert "tool_runner" in capsys.readouterr().out


class TestRun:
    def test_happy_path_prints_text_and_memory_ops(self, monkeypatch, capsys, _key, _tool):
        msgs = [
            _Msg(content=[_Block(type="text", text="Noted. ")]),
            _Msg(
                content=[
                    _Block(
                        type="tool_use",
                        name="memory",
                        input={"command": "create", "path": "/memories/sky.md"},
                    ),
                    _Block(type="text", text="Saved to /memories/sky.md"),
                ]
            ),
        ]
        captured = _install_fake_anthropic(monkeypatch, runner=_FakeRunner(msgs))
        rc = ma.cmd_memory_agent(_args())
        out = capsys.readouterr().out
        assert rc == 0
        assert "Noted." in out
        assert "memory.create /memories/sky.md" in out
        assert "Saved to /memories/sky.md" in out
        # the memory tool + beta header reach the runner
        assert captured["kwargs"]["betas"] == [ma._MEMORY_BETA]
        assert captured["kwargs"]["model"] == ma._DEFAULT_MODEL
        assert len(captured["kwargs"]["tools"]) == 1

    def test_custom_model_and_max_tokens_forwarded(self, monkeypatch, _key, _tool):
        captured = _install_fake_anthropic(monkeypatch, runner=_FakeRunner([]))
        ma.cmd_memory_agent(_args(model="claude-opus-4-8", max_tokens=1234))
        assert captured["kwargs"]["model"] == "claude-opus-4-8"
        assert captured["kwargs"]["max_tokens"] == 1234

    def test_tool_runner_construction_error_returns_1(self, monkeypatch, capsys, _key, _tool):
        _install_fake_anthropic(monkeypatch, raise_on_construct=True)
        rc = ma.cmd_memory_agent(_args())
        assert rc == 1
        assert "failed to start" in capsys.readouterr().out

    def test_run_loop_error_returns_1(self, monkeypatch, capsys, _key, _tool):
        _install_fake_anthropic(monkeypatch, runner=_RaisingRunner())
        rc = ma.cmd_memory_agent(_args())
        assert rc == 1
        assert "Error during agent run" in capsys.readouterr().out

    def test_backend_unavailable_returns_1(self, monkeypatch, capsys, _key):
        import attune.memory as m

        def _boom(**kw):
            raise RuntimeError("no memory backend available")

        monkeypatch.setattr(m, "make_memory_tool", _boom)
        _install_fake_anthropic(monkeypatch)
        rc = ma.cmd_memory_agent(_args())
        assert rc == 1
        assert "could not build the memory tool" in capsys.readouterr().out
