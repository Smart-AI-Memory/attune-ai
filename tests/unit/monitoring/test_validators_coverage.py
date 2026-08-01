"""Coverage-gap tests for ``attune.monitoring.validators``.

Targets the branches not exercised by the existing SSRF suites
(``tests/unit/security/test_ssrf_prevention.py`` and
``tests/monitoring/test_webhook_ssrf.py``):

- ``urllib.parse.unquote`` raising during decode (line 77/80)
- ``urllib.parse.urlparse`` raising during parse (line 85/88)
- an IP literal that is loopback but not in the ``blocked_hosts``
  set, e.g. ``127.5.5.5`` (line 127)
- an IP literal that is unspecified but not in ``blocked_hosts``,
  e.g. IPv6 ``::`` (line 133)
- an IP literal that is reserved but not loopback/link-local/
  multicast/unspecified/private-blocked earlier, e.g. ``240.0.0.1``
  (line 135)

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.monitoring.validators import _validate_webhook_url


class TestDecodeAndParseFailures:
    """Exercise the broad except clauses around unquote/urlparse."""

    def test_unquote_failure_wraps_as_invalid_encoding(self):
        with patch(
            "attune.monitoring.validators.urllib.parse.unquote",
            side_effect=ValueError("bad percent-encoding"),
        ):
            with pytest.raises(ValueError, match="Invalid URL encoding"):
                _validate_webhook_url("http://example.com/%zz")

    def test_urlparse_failure_wraps_as_invalid_format(self):
        with patch(
            "attune.monitoring.validators.urllib.parse.urlparse",
            side_effect=ValueError("cannot parse"),
        ):
            with pytest.raises(ValueError, match="Invalid URL format"):
                _validate_webhook_url("http://example.com/hook")


class TestIPLiteralOrderingEdgeCases:
    """IP literals that reach the per-attribute checks, not blocked_hosts."""

    def test_blocks_loopback_ip_literal_outside_blocklist(self):
        # 127.5.5.5 is loopback (127.0.0.0/8) but not the literal
        # "127.0.0.1" string in blocked_hosts, so it must be caught
        # by the ip.is_loopback check instead.
        with pytest.raises(ValueError, match="loopback"):
            _validate_webhook_url("http://127.5.5.5/hook")

    def test_blocks_unspecified_ipv6_literal(self):
        # "::" is the IPv6 unspecified address; only "::1"/"[::1]"
        # are in blocked_hosts, so "::" must reach ip.is_unspecified.
        with pytest.raises(ValueError, match="unspecified"):
            _validate_webhook_url("http://[::]/hook")

    def test_blocks_reserved_ip_literal(self):
        # 240.0.0.0/4 (Class E) is reserved but not loopback,
        # link-local, multicast, or unspecified.
        with pytest.raises(ValueError, match="reserved"):
            _validate_webhook_url("http://240.0.0.1/hook")
