"""Tests for LifecycleMixin (save/close/context-manager protocol).

Drives the mixin with a tiny host carrying _file_session / _short_term,
so save(), close(), and the context-manager methods are exercised
directly.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from attune.memory.mixins.lifecycle_mixin import LifecycleMixin


class _Host(LifecycleMixin):
    """Minimal UnifiedMemory stand-in for the lifecycle mixin."""

    def __init__(self, file_session: Any = None, short_term: Any = None):
        self._file_session = file_session
        self._short_term = short_term


class TestSave:
    def test_save_persists_file_session(self):
        fs = MagicMock()
        _Host(file_session=fs).save()
        fs.save.assert_called_once_with()

    def test_save_without_file_session_is_noop(self):
        # No file session -> no call, no crash.
        _Host(file_session=None).save()


class TestClose:
    def test_close_closes_both_backends(self):
        fs = MagicMock()
        st = MagicMock()
        _Host(file_session=fs, short_term=st).close()

        fs.close.assert_called_once_with()
        st.close.assert_called_once_with()

    def test_close_skips_short_term_without_close_method(self):
        fs = MagicMock()

        class _NoClose:
            pass

        # hasattr guard means an object lacking close() must not raise.
        _Host(file_session=fs, short_term=_NoClose()).close()
        fs.close.assert_called_once_with()


class TestContextManager:
    def test_enter_returns_self_and_exit_closes(self):
        fs = MagicMock()
        st = MagicMock()
        host = _Host(file_session=fs, short_term=st)

        with host as ctx:
            assert ctx is host

        # __exit__ delegates to close().
        fs.close.assert_called_once_with()
        st.close.assert_called_once_with()
