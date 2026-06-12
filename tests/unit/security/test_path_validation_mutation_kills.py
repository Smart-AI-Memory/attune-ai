"""Mutation-driven tests for ``_validate_file_path``.

A mutmut run on ``src/attune/security/path_validation.py`` showed 17 survivors
(33%) despite 60 passing tests. The real gaps these close:

1. **The entire Windows branch** (``sys.platform == "win32"``) never ran on
   the Unix CI runners, so its system-dir + unix-marker defenses — including a
   genuine ``.strip()`` logic mutation — were unverified. We force the branch
   so it is exercised on any platform.
2. **Unix dangerous-dir entries** (``/private/etc``, ``/private/var/root``,
   ``/sbin`` …) were in the blocklist but never asserted, so a regression
   dropping one would pass CI.
3. **Exception messages** were never asserted (tests checked the type only).

Equivalent mutants remain by design: a few Windows blocklist entries are
substring-subsumed by broader entries (e.g. ``\\windows\\system32`` by
``\\windows\\system``), so mutating them cannot change behavior.
"""

from __future__ import annotations

import sys

import pytest

from attune.security import path_validation
from attune.security.path_validation import _validate_file_path

# ---- exception messages (kill the message-text survivors) ----------------


def test_empty_path_message_is_exact():
    with pytest.raises(ValueError) as ei:
        _validate_file_path("")
    assert str(ei.value) == "path must be a non-empty string"


def test_null_byte_message_is_exact():
    with pytest.raises(ValueError) as ei:
        _validate_file_path("foo\x00bar")
    assert str(ei.value) == "path contains null bytes"


def test_allowed_dir_violation_message(tmp_path):
    outside = tmp_path / "outside.txt"
    with pytest.raises(ValueError, match=r"Operations are restricted to the workspace"):
        _validate_file_path(str(outside), allowed_dir=str(tmp_path / "allowed"))


def test_unresolvable_path_message(monkeypatch):
    # Force the resolve-failure branch (OSError/RuntimeError) and assert it is
    # re-raised as the "Invalid path:" ValueError — the branch was unasserted.
    def _raise(self):
        raise OSError("boom")

    monkeypatch.setattr(path_validation.Path, "resolve", _raise)
    with pytest.raises(ValueError) as ei:
        _validate_file_path("some/relative/path")
    assert str(ei.value).startswith("Invalid path:")


# ---- Unix dangerous dirs that were never individually asserted ------------


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX branch: these absolute paths only resolve/match on Unix",
)
@pytest.mark.parametrize(
    "danger",
    ["/private/etc", "/private/var/root", "/sbin", "/usr/sbin", "/usr/bin", "/bin"],
)
def test_unix_dangerous_dirs_blocked(danger):
    with pytest.raises(ValueError, match=r"^Cannot write to system directory"):
        _validate_file_path(f"{danger}/x")


# ---- Windows branch (forced so it runs on any platform) ------------------


@pytest.fixture
def force_windows(monkeypatch):
    monkeypatch.setattr(path_validation.sys, "platform", "win32")


@pytest.mark.parametrize(
    "danger",
    [
        "C:\\Windows\\System32\\cmd.exe",
        "C:\\Windows\\System\\x",
        "C:\\Program Files\\app\\x",
    ],
)
def test_windows_system_dirs_blocked(force_windows, danger):
    with pytest.raises(ValueError, match=r"^Cannot write to system directory"):
        _validate_file_path(danger)


@pytest.mark.parametrize("marker", ["etc", "sys", "proc", "dev"])
def test_windows_blocks_unix_marker_inside_path(force_windows, marker):
    # A /etc/passwd that resolved to D:\etc\passwd on Windows must still block.
    with pytest.raises(ValueError, match=rf"Cannot write to system directory: {marker}$"):
        _validate_file_path(f"C:\\{marker}\\passwd")


@pytest.mark.parametrize("marker", ["etc", "sys", "proc", "dev"])
def test_windows_blocks_unix_marker_at_path_end(force_windows, marker):
    # Exercises the endswith() clause: the path ENDS with the marker, with no
    # trailing separator, so the plain `in` check would miss it.
    with pytest.raises(ValueError, match=rf"Cannot write to system directory: {marker}$"):
        _validate_file_path(f"C:\\some\\{marker}")
