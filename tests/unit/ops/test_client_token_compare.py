"""The client-token check must be constant-time and never 500.

``!=`` short-circuits on the first differing byte, so response latency
leaks a matching prefix and the session token can be recovered byte by
byte. These pin the two properties that fix depends on: the comparison
goes through ``secrets.compare_digest``, and a caller-controlled header
that ``compare_digest`` cannot accept as ``str`` (non-ASCII) still
yields a clean 403 rather than an unhandled TypeError.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from attune.ops import security

_TOKEN = "fixed-token-for-compare-tests"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def _bypass_client_token(monkeypatch):
    """Override the conftest bypass — this file MUST test the real gate.

    The directory conftest nulls ``_SESSION_TOKEN`` so header-less route
    tests pass; these tests need a concrete token to compare against.
    """
    monkeypatch.setattr("attune.ops.security._SESSION_TOKEN", _TOKEN)


class TestAcceptsAndRejects:
    def test_valid_token_is_accepted(self):
        security.require_client_token(_TOKEN)

    @pytest.mark.parametrize(
        ("header", "label"),
        [
            (None, "missing header"),
            ("", "empty header"),
            ("wrong-token", "wrong token"),
            ("токен", "non-ASCII"),
            ("\udcff", "lone surrogate in surrogateescape range"),
            # OUTSIDE U+DC80–U+DCFF, so surrogateescape cannot encode it.
            # The original test used only \udcff and passed while this
            # case still 500'd — found by the cross-review lane (codex).
            ("\ud800", "lone surrogate below the range"),
            ("\udbff", "lone surrogate above the range"),
            ("pre\ud800post", "surrogate embedded in ASCII"),
            ("tok\x00en", "embedded NUL"),
        ],
    )
    def test_bad_header_is_403_not_500(self, header, label):
        """Every rejection path must be an HTTPException(403), never a crash."""
        with pytest.raises(HTTPException) as exc:
            security.require_client_token(header)
        assert exc.value.status_code == 403, label

    def test_prefix_of_the_real_token_is_rejected(self):
        """A correct prefix must not be accepted — the byte-by-byte attack."""
        with pytest.raises(HTTPException):
            security.require_client_token(_TOKEN[:-1])


class TestConstantTimeComparison:
    def test_uses_compare_digest(self, monkeypatch):
        """Pin the mechanism: a plain == would not call compare_digest."""
        calls: list[tuple[bytes, bytes]] = []
        real = security.secrets.compare_digest

        def spy(a, b):
            calls.append((a, b))
            return real(a, b)

        monkeypatch.setattr(security.secrets, "compare_digest", spy)
        security.require_client_token(_TOKEN)

        assert calls, "require_client_token did not use secrets.compare_digest"

    def test_compares_bytes_not_str(self, monkeypatch):
        """str comparison raises TypeError on non-ASCII; bytes never does."""
        seen: list[type] = []

        def spy(a, b):
            seen.extend((type(a), type(b)))
            return False

        monkeypatch.setattr(security.secrets, "compare_digest", spy)
        with pytest.raises(HTTPException):
            security.require_client_token("токен")

        assert set(seen) == {bytes}, f"expected bytes on both sides, got {seen}"
