"""Security tests for HookExecutor._execute_webhook() SSRF prevention.

Ensures webhook URLs are validated against SSRF attacks before
making HTTP requests.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.hooks.executor import HookExecutor


@pytest.fixture()
def executor():
    """Create a HookExecutor instance."""
    return HookExecutor()


class TestWebhookSSRFPrevention:
    """Verify _execute_webhook blocks SSRF attack vectors."""

    @pytest.mark.asyncio
    async def test_blocks_localhost(self, executor):
        """Localhost URLs are rejected."""
        with pytest.raises(ValueError):
            await executor._execute_webhook("http://127.0.0.1/hook", {"event": "test"})

    @pytest.mark.asyncio
    async def test_blocks_localhost_name(self, executor):
        """'localhost' hostname is rejected."""
        with pytest.raises(ValueError):
            await executor._execute_webhook("http://localhost/hook", {"event": "test"})

    @pytest.mark.asyncio
    async def test_blocks_private_ip(self, executor):
        """Private IP addresses are rejected."""
        with pytest.raises(ValueError):
            await executor._execute_webhook("http://10.0.0.1/hook", {"event": "test"})

    @pytest.mark.asyncio
    async def test_blocks_private_ip_172(self, executor):
        """172.16.x.x private IPs are rejected."""
        with pytest.raises(ValueError):
            await executor._execute_webhook("http://172.16.0.1/hook", {"event": "test"})

    @pytest.mark.asyncio
    async def test_blocks_metadata_service(self, executor):
        """Cloud metadata service IP is rejected."""
        with pytest.raises(ValueError):
            await executor._execute_webhook(
                "http://169.254.169.254/latest/meta-data/",
                {"event": "test"},
            )

    @pytest.mark.asyncio
    async def test_blocks_non_http_scheme(self, executor):
        """Non-HTTP schemes are rejected."""
        with pytest.raises(ValueError):
            await executor._execute_webhook("ftp://example.com/hook", {"event": "test"})

    @pytest.mark.asyncio
    async def test_blocks_encoded_localhost(self, executor):
        """Percent-encoded localhost bypass is rejected."""
        with pytest.raises(ValueError):
            await executor._execute_webhook(
                "http://%31%32%37%2e%30%2e%30%2e%31/hook",
                {"event": "test"},
            )

    @pytest.mark.asyncio
    async def test_allows_valid_url(self, executor):
        """Valid external HTTPS URL is allowed."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})

        mock_session = MagicMock()
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_post_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch("aiohttp.ClientSession", return_value=mock_session_cm),
        ):
            result = await executor._execute_webhook(
                "https://hooks.example.com/notify",
                {"event": "test"},
            )

        assert result == {"ok": True}
