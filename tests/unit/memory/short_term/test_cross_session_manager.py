"""Tests for CrossSessionManager — the short-term cross-session wrapper.

`CrossSessionManager` is a thin dependency-injection wrapper around a
`BaseOperations` instance. It owns two behaviors: the mock-mode guard in
`enable()` (Redis is required for real cross-session coordination) and the
`available()` availability check. Both are pure logic over the injected
base, so this suite uses a fake base — no Redis — and patches the lazily
imported `CrossSessionCoordinator` so `enable()` can be exercised without
a live coordinator.

The assertions pin the exact `available()` boolean (every combination of
`use_mock` × `_client`) and the exact kwargs passed to the coordinator, so
that boolean-operator and argument mutations are caught.

Coverage: takes `cross_session.py` from 62.5% to 100% (16/16 stmts).

Mutation status (mutmut 2.4.4, this suite as runner): ``9 mutants ->
6 killed, 3 survived``. All 3 survivors are documented equivalents:
the unused module-level ``logger`` (`= None` has no effect — the module
makes no ``logger`` calls) and the two `ValueError` message-string
fragments (a substring ``match=`` can't kill an ``XX``-wrapped string;
repo policy is not to over-fit assertions to message text). Killable
kill-rate is 6/6 = 100%.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from attune.memory.cross_session import SessionType
from attune.memory.short_term.cross_session import CrossSessionManager
from attune.memory.types import AccessTier

pytestmark = pytest.mark.unit

# Patch target: enable() lazily does `from attune.memory.cross_session
# import CrossSessionCoordinator`, which resolves the name from that
# module at call time — so patch it on the source module.
COORDINATOR = "attune.memory.cross_session.CrossSessionCoordinator"


def make_base(*, use_mock: bool = False, client: object | None = object()):
    """A fake BaseOperations exposing just the attributes the wrapper reads."""
    return SimpleNamespace(use_mock=use_mock, _client=client)


class TestInit:
    def test_stores_base(self):
        base = make_base()
        mgr = CrossSessionManager(base)
        assert mgr._base is base


class TestAvailable:
    """`available()` == (not use_mock) and (client is not None)."""

    def test_true_when_connected_and_not_mock(self):
        mgr = CrossSessionManager(make_base(use_mock=False, client=object()))
        assert mgr.available() is True

    def test_false_when_mock_even_with_client(self):
        mgr = CrossSessionManager(make_base(use_mock=True, client=object()))
        assert mgr.available() is False

    def test_false_when_no_client_even_if_not_mock(self):
        mgr = CrossSessionManager(make_base(use_mock=False, client=None))
        assert mgr.available() is False

    def test_false_when_mock_and_no_client(self):
        mgr = CrossSessionManager(make_base(use_mock=True, client=None))
        assert mgr.available() is False


class TestEnableMockMode:
    def test_raises_in_mock_mode(self):
        mgr = CrossSessionManager(make_base(use_mock=True))
        with pytest.raises(ValueError, match="requires Redis"):
            mgr.enable()

    def test_mock_mode_does_not_construct_coordinator(self):
        mgr = CrossSessionManager(make_base(use_mock=True))
        with patch(COORDINATOR) as coord:
            with pytest.raises(ValueError):
                mgr.enable()
        coord.assert_not_called()


class TestEnable:
    """Non-mock enable() builds a coordinator with the right kwargs."""

    def test_returns_constructed_coordinator(self):
        base = make_base(use_mock=False)
        mgr = CrossSessionManager(base)
        with patch(COORDINATOR) as coord:
            result = mgr.enable()
        assert result is coord.return_value

    def test_passes_defaults(self):
        base = make_base(use_mock=False)
        mgr = CrossSessionManager(base)
        with patch(COORDINATOR) as coord:
            mgr.enable()
        coord.assert_called_once_with(
            memory=base,
            session_type=SessionType.CLAUDE,
            access_tier=AccessTier.CONTRIBUTOR,
            auto_announce=True,
        )

    def test_passes_custom_tier_and_auto_announce(self):
        base = make_base(use_mock=False)
        mgr = CrossSessionManager(base)
        with patch(COORDINATOR) as coord:
            mgr.enable(access_tier=AccessTier.OBSERVER, auto_announce=False)
        coord.assert_called_once_with(
            memory=base,
            session_type=SessionType.CLAUDE,
            access_tier=AccessTier.OBSERVER,
            auto_announce=False,
        )

    def test_default_access_tier_is_contributor(self):
        """The default arg itself must be CONTRIBUTOR (pins the default)."""
        base = make_base(use_mock=False)
        mgr = CrossSessionManager(base)
        with patch(COORDINATOR) as coord:
            mgr.enable(auto_announce=True)
        _, kwargs = coord.call_args
        assert kwargs["access_tier"] is AccessTier.CONTRIBUTOR
