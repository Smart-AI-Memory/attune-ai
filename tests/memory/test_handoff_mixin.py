"""Behavioral tests for HandoffAndExportMixin (mixins/handoff_mixin).

Covers compact-state generation, export to disk, and handoff-context
setting — no prior dedicated test file (75%). Fakes supply the
file-session/config/capabilities the mixin expects; emphasis on the
branches line coverage missed: working-memory and staged-pattern
sections (including the >10 / >5 overflow lines), export path handling,
and set_handoff's no-session and auto-export branches.
"""

from types import SimpleNamespace

from attune.memory.mixins.handoff_mixin import HandoffAndExportMixin


class _FS:
    def __init__(self, working=None, staged=None, context=None):
        self._state = SimpleNamespace(
            session_id="s1",
            user_id="alice",
            working_memory=working or {},
            staged_patterns=staged or {},
        )
        self._context = context or {}
        self.set_calls: list = []

    def get_all_context(self):
        return self._context

    def set_context(self, key, value):
        self._context[key] = value
        self.set_calls.append((key, value))


def _staged(name, ptype="algo", conf=0.5):
    return SimpleNamespace(name=name, pattern_type=ptype, confidence=conf)


class _Host(HandoffAndExportMixin):
    def __init__(self, file_session=None, caps=None, compact_path=None, auto=False):
        self._file_session = file_session
        self.config = SimpleNamespace(
            compact_state_path=compact_path,
            auto_generate_compact_state=auto,
        )
        self._caps = caps or {
            "file_session": True,
            "redis": False,
            "long_term": False,
            "realtime": False,
        }

    def get_capabilities(self):
        return self._caps


# ===========================================================================
# generate_compact_state
# ===========================================================================


def test_generate_without_file_session_uses_defaults():
    out = _Host().generate_compact_state()
    assert "# Compact State - Session Handoff" in out
    assert "Session in progress." in out  # default situation
    assert "**Session ID:**" not in out  # no session block


def test_generate_includes_session_and_context():
    fs = _FS(
        context={
            "situation": "Mid-refactor",
            "background": "Legacy code",
            "assessment": "Halfway",
            "recommendation": "Finish tests",
        }
    )
    out = _Host(file_session=fs).generate_compact_state()
    assert "**Session ID:** s1" in out
    assert "**User ID:** alice" in out
    assert "Mid-refactor" in out
    assert "Finish tests" in out


def test_generate_working_memory_section_with_overflow():
    fs = _FS(working={f"k{i}": i for i in range(12)})
    out = _Host(file_session=fs).generate_compact_state()
    assert "## Working Memory" in out
    assert "**Active keys:** 12" in out
    assert "- `k0`" in out
    assert "- ... and 2 more" in out  # 12 - 10


def test_generate_staged_patterns_section_with_overflow():
    staged = {f"p{i}": _staged(f"Pat{i}") for i in range(7)}
    out = _Host(file_session=_FS(staged=staged)).generate_compact_state()
    assert "## Staged Patterns" in out
    assert "**Pending validation:** 7" in out
    assert "Pat0 (algo, conf: 0.50)" in out
    assert "- ... and 2 more" in out  # 7 - 5


def test_generate_renders_capabilities():
    caps = {"file_session": True, "redis": True, "long_term": False, "realtime": False}
    out = _Host(caps=caps).generate_compact_state()
    assert "- File session: Yes" in out
    assert "- Redis: Yes" in out
    assert "- Long-term memory: No" in out


# ===========================================================================
# export_to_claude_md
# ===========================================================================


def test_export_writes_to_explicit_path(tmp_path):
    target = tmp_path / "nested" / "compact.md"
    host = _Host()
    written = host.export_to_claude_md(str(target))
    assert written == target.resolve()
    assert target.exists()  # parent dir created + file written
    content = target.read_text(encoding="utf-8")
    assert content.startswith("# Compact State - Session Handoff")


def test_export_uses_config_default_path(tmp_path):
    target = tmp_path / "default.md"
    host = _Host(compact_path=str(target))
    written = host.export_to_claude_md()
    assert written == target.resolve()
    assert "# Compact State - Session Handoff" in target.read_text(encoding="utf-8")


# ===========================================================================
# set_handoff
# ===========================================================================


def test_set_handoff_without_file_session_is_noop():
    host = _Host(file_session=None)
    # Should not raise despite no file session.
    host.set_handoff("s", "b", "a", "r")


def test_set_handoff_records_context_fields():
    fs = _FS()
    _Host(file_session=fs).set_handoff("sit", "bg", "assess", "rec", ticket="JIRA-1")
    assert fs._context["situation"] == "sit"
    assert fs._context["background"] == "bg"
    assert fs._context["assessment"] == "assess"
    assert fs._context["recommendation"] == "rec"
    assert fs._context["ticket"] == "JIRA-1"  # extra_context


def test_set_handoff_auto_exports_when_configured(tmp_path):
    target = tmp_path / "auto.md"
    fs = _FS()
    host = _Host(file_session=fs, compact_path=str(target), auto=True)
    host.set_handoff("sit", "bg", "assess", "rec")
    assert target.exists()  # auto-export fired


def test_set_handoff_no_export_when_disabled(tmp_path):
    target = tmp_path / "noauto.md"
    fs = _FS()
    host = _Host(file_session=fs, compact_path=str(target), auto=False)
    host.set_handoff("sit", "bg", "assess", "rec")
    assert not target.exists()  # auto-export disabled
