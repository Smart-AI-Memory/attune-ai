"""Security tests for HookExecutor._execute_webhook() SSRF prevention.

Ensures webhook URLs are validated against SSRF attacks before
making HTTP requests.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("aiohttp", reason="aiohttp required for webhook tests")

from attune.hooks.executor import HookExecutor  # noqa: E402


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


class TestWebhookDNSPinning:
    """The request must connect to the pre-vetted IP (rebinding TOCTOU)."""

    @pytest.mark.asyncio
    async def test_webhook_pins_resolved_ip(self, executor):
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

        session_cls = MagicMock(return_value=mock_session_cm)
        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch(
                "attune.monitoring.validators.resolve_pinned_ip",
                return_value="93.184.216.34",
            ) as pin,
            patch("aiohttp.ClientSession", session_cls),
        ):
            await executor._execute_webhook(
                "https://hooks.example.com/notify",
                {"event": "test"},
            )

        pin.assert_called_once_with("hooks.example.com")
        connector = session_cls.call_args.kwargs["connector"]
        assert connector is not None
        resolved = await connector._resolver.resolve("hooks.example.com", 443)
        assert resolved[0]["host"] == "93.184.216.34"
        assert resolved[0]["hostname"] == "hooks.example.com"
        # The resolver's own close() is part of the AbstractResolver
        # contract aiohttp calls on connector teardown — exercise it.
        await connector._resolver.close()
        await connector.close()


class TestCommandArgvInjection:
    """Context values must stay single argv tokens (flag-injection guard)."""

    @pytest.mark.asyncio
    async def test_context_value_with_spaces_stays_one_token(self, executor):
        process = AsyncMock()
        process.communicate = AsyncMock(return_value=(b"ok", b""))
        process.returncode = 0
        with patch("asyncio.create_subprocess_exec", return_value=process) as spawn:
            out = await executor._execute_command(
                "notify-send {msg}",
                {"msg": "hello world --urgency=critical"},
            )
        assert out == "ok"
        argv = spawn.call_args.args
        assert argv[0] == "notify-send"
        assert argv[1] == "hello world --urgency=critical"
        assert len(argv) == 2, "value with spaces must NOT split into extra argv tokens"

    @pytest.mark.asyncio
    async def test_missing_context_variable_still_raises_value_error(self, executor):
        with pytest.raises(ValueError, match="Missing context variable"):
            await executor._execute_command("echo {absent}", {})


def _mock_session_returning(response: AsyncMock) -> MagicMock:
    """Session context-manager mock whose post() yields ``response``."""
    mock_session = MagicMock()
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=response)
    mock_post_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.post = MagicMock(return_value=mock_post_cm)
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_session_cm


class TestWebhookResponseHandling:
    """The response branches past the pinned connect: error status,
    JSON body, and the non-JSON fallback."""

    @pytest.mark.asyncio
    async def test_error_status_raises_with_body(self, executor):
        """A >=400 response raises RuntimeError carrying status + text —
        never returns a payload the caller would mistake for success."""
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.text = AsyncMock(return_value="upstream down")
        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch("aiohttp.ClientSession", return_value=_mock_session_returning(mock_response)),
        ):
            with pytest.raises(RuntimeError, match="status 503.*upstream down"):
                await executor._execute_webhook(
                    "https://hooks.example.com/notify", {"event": "test"}
                )

    @pytest.mark.asyncio
    async def test_non_json_response_falls_back_to_status_and_text(self, executor):
        """A 2xx body that isn't JSON degrades to {status, text} instead
        of raising out of the hook."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=ValueError("not json"))
        mock_response.text = AsyncMock(return_value="OK\n")
        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch("aiohttp.ClientSession", return_value=_mock_session_returning(mock_response)),
        ):
            result = await executor._execute_webhook(
                "https://hooks.example.com/notify", {"event": "test"}
            )
        assert result == {"status": 200, "text": "OK\n"}

    @pytest.mark.asyncio
    async def test_webhook_hook_dispatches_through_execute(self, executor):
        """A HookDefinition of type WEBHOOK routes through execute() to
        the webhook path and comes back in the success envelope."""
        from attune.hooks.config import HookDefinition, HookType

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})
        hook = HookDefinition(
            type=HookType.WEBHOOK,
            command="https://hooks.example.com/notify",
            description="test webhook dispatch",
        )
        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch("aiohttp.ClientSession", return_value=_mock_session_returning(mock_response)),
        ):
            result = await executor.execute(hook, {"event": "test"})
        assert result["success"] is True
        assert result["output"] == {"ok": True}
