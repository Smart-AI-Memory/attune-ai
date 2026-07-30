"""Contract tests for the ``attune.coordination`` deprecation shim.

The module was removed in v6.8.0 (redis-decoupling P1); what ships
is a PEP 562 shim whose whole job is a helpful ImportError. The
contract: every removed name raises ImportError with the pinned
guidance, anything else raises plain AttributeError, and importing
the shim itself stays side-effect free.
"""

from __future__ import annotations

import pytest

import attune.coordination as coordination


def test_every_removed_name_raises_helpful_import_error() -> None:
    assert coordination._REMOVED_NAMES  # non-empty by contract
    for name in coordination._REMOVED_NAMES:
        with pytest.raises(ImportError, match="removed in v6.8.0") as excinfo:
            getattr(coordination, name)
        message = str(excinfo.value)
        assert name in message
        assert "attune-ai<6.8.0" in message
        assert "docs/specs/redis-decoupling/" in message


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="no attribute 'NotAThing'"):
        coordination.NotAThing  # noqa: B018 — attribute access IS the test
