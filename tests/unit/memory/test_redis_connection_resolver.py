"""Tests for resolve_redis_connection — redis-config-truth rct-1.

Pins the R1 five-step precedence, the conflict matrix (precedence
always decides, disagreements recorded, only malformed raises), and
password redaction. The incident shape (password-less REDIS_URL +
REDIS_PASSWORD set, 2026-08-08) is the load-bearing case.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.memory.config import ResolvedRedisConnection, resolve_redis_connection


class TestPrecedence:
    def test_nothing_set_yields_default(self):
        r = resolve_redis_connection(env={})
        assert r.url == "redis://127.0.0.1:6379/0"
        assert r.source_map["url"] == "default"
        assert r.overrides == ()

    def test_credentialed_url_used_as_is(self):
        url = "redis://user:secret@example.com:6380/2"  # pragma: allowlist secret
        r = resolve_redis_connection(env={"REDIS_URL": url})
        assert r.url == url
        assert r.source_map == {"url": "REDIS_URL", "password": "REDIS_URL", "user": "REDIS_URL"}

    def test_incident_shape_password_merges_into_url(self):
        """The 2026-08-08 incident: password-less URL + REDIS_PASSWORD set."""
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://127.0.0.1:6379/0",
                "REDIS_PASSWORD": "hunter2",  # pragma: allowlist secret
            }
        )
        assert r.url == "redis://:hunter2@127.0.0.1:6379/0"  # pragma: allowlist secret
        assert r.source_map["password"] == "REDIS_PASSWORD"
        assert r.overrides == ()

    def test_user_and_password_merge(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://h:6379/1",
                "REDIS_PASSWORD": "pw",  # pragma: allowlist secret
                "REDIS_USER": "svc",
            }
        )
        assert r.url == "redis://svc:pw@h:6379/1"  # pragma: allowlist secret
        assert r.source_map["user"] == "REDIS_USER"

    def test_private_preferred_over_public(self):
        r = resolve_redis_connection(
            env={
                "REDIS_PRIVATE_URL": "redis://private:6379/0",
                "REDIS_PUBLIC_URL": "redis://public:6379/0",
            }
        )
        assert "private" in r.url
        assert any("REDIS_PUBLIC_URL ignored" in o for o in r.overrides)

    def test_redis_url_beats_variants(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://main:6379/0",
                "REDIS_PRIVATE_URL": "redis://private:6379/0",
            }
        )
        assert "main" in r.url
        assert any("REDIS_PRIVATE_URL ignored" in o for o in r.overrides)

    def test_components_path(self):
        r = resolve_redis_connection(
            env={
                "REDIS_HOST": "h.example",
                "REDIS_PORT": "6380",
                "REDIS_DB": "3",
                "REDIS_PASSWORD": "pw",  # pragma: allowlist secret
            }
        )
        assert r.url == "redis://:pw@h.example:6380/3"  # pragma: allowlist secret
        assert r.source_map["url"] == "REDIS_HOST"

    def test_password_alone_merges_into_default(self):
        """requirepass on localhost with only REDIS_PASSWORD exported."""
        r = resolve_redis_connection(env={"REDIS_PASSWORD": "pw"})  # pragma: allowlist secret
        assert r.url == "redis://:pw@127.0.0.1:6379/0"  # pragma: allowlist secret
        assert r.source_map["url"] == "default"
        assert r.source_map["password"] == "REDIS_PASSWORD"


class TestConflictMatrix:
    def test_credentialed_url_wins_over_differing_password(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://:urlpw@h:6379/0",  # pragma: allowlist secret
                "REDIS_PASSWORD": "otherpw",  # pragma: allowlist secret
            }
        )
        assert "urlpw" in r.url
        assert any("REDIS_PASSWORD ignored" in o for o in r.overrides)

    def test_identical_redundant_password_is_not_a_conflict(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://:same@h:6379/0",  # pragma: allowlist secret
                "REDIS_PASSWORD": "same",  # pragma: allowlist secret
            }
        )
        assert r.overrides == ()

    def test_identical_redundant_urls_are_not_a_conflict(self):
        url = "redis://h:6379/0"
        r = resolve_redis_connection(env={"REDIS_URL": url, "REDIS_PUBLIC_URL": url})
        assert r.overrides == ()

    def test_never_raises_on_redundancy(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://a:6379/0",
                "REDIS_PRIVATE_URL": "redis://b:6379/0",
                "REDIS_PUBLIC_URL": "redis://c:6379/0",
                "REDIS_PASSWORD": "pw",  # pragma: allowlist secret
                "REDIS_HOST": "d",
            }
        )
        assert isinstance(r, ResolvedRedisConnection)
        assert len(r.overrides) == 2  # the two unused, differing URL vars


class TestMalformed:
    def test_bad_scheme_raises_actionable(self):
        with pytest.raises(ValueError, match="not a Redis URL"):
            resolve_redis_connection(env={"REDIS_URL": "http://h:6379/0"})

    def test_non_numeric_url_port_raises(self):
        with pytest.raises(ValueError, match="non-numeric port"):
            resolve_redis_connection(env={"REDIS_URL": "redis://h:notaport/0"})

    def test_non_numeric_component_port_raises(self):
        with pytest.raises(ValueError, match="REDIS_PORT must be numeric"):
            resolve_redis_connection(env={"REDIS_HOST": "h", "REDIS_PORT": "abc"})

    def test_non_numeric_db_raises(self):
        with pytest.raises(ValueError, match="REDIS_DB must be numeric"):
            resolve_redis_connection(env={"REDIS_HOST": "h", "REDIS_DB": "x"})


class TestCrossReviewHardening:
    """Regressions from the 2026-08-08 codex cross-review lane (PR #1984)."""

    def test_credentialed_variant_beats_passwordless_redis_url(self):
        """R1 tier 1: a URL already carrying credentials outranks var order."""
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://plain:6379/0",
                "REDIS_PRIVATE_URL": "redis://:pw@private:6379/0",  # pragma: allowlist secret
            }
        )
        assert "private" in r.url
        assert r.source_map["url"] == "REDIS_PRIVATE_URL"
        assert any("REDIS_URL ignored" in o for o in r.overrides)

    def test_url_username_preserved_when_password_merges(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://svc@h:6379/0",
                "REDIS_PASSWORD": "pw",  # pragma: allowlist secret
            }
        )
        assert r.url == "redis://svc:pw@h:6379/0"  # pragma: allowlist secret
        assert r.source_map["user"] == "REDIS_URL"

    def test_redis_user_still_beats_url_username(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://svc@h:6379/0",
                "REDIS_PASSWORD": "pw",  # pragma: allowlist secret
                "REDIS_USER": "envuser",
            }
        )
        assert r.url == "redis://envuser:pw@h:6379/0"  # pragma: allowlist secret
        assert r.source_map["user"] == "REDIS_USER"

    def test_ipv6_host_rebracketed_on_merge(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://[::1]:6379/0",
                "REDIS_PASSWORD": "pw",  # pragma: allowlist secret
            }
        )
        assert r.url == "redis://:pw@[::1]:6379/0"  # pragma: allowlist secret
        assert "[::1]" in r.redacted_url

    def test_unix_socket_merge_keeps_socket_path(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "unix:///tmp/redis.sock",
                "REDIS_PASSWORD": "pw",  # pragma: allowlist secret
            }
        )
        assert r.url == "unix://:pw@/tmp/redis.sock"  # pragma: allowlist secret
        assert r.redacted_url == "unix://:***@/tmp/redis.sock"

    def test_unix_socket_path_is_not_db_checked(self):
        r = resolve_redis_connection(env={"REDIS_URL": "unix:///tmp/redis.sock"})
        assert r.url == "unix:///tmp/redis.sock"

    def test_non_numeric_url_db_raises(self):
        with pytest.raises(ValueError, match="non-numeric db"):
            resolve_redis_connection(env={"REDIS_URL": "redis://h:6379/abc"})


class TestRedaction:
    CASES = [
        {"REDIS_URL": "redis://:sekret@h:6379/0"},  # pragma: allowlist secret
        {"REDIS_URL": "redis://h:6379/0", "REDIS_PASSWORD": "sekret"},  # pragma: allowlist secret
        {"REDIS_HOST": "h", "REDIS_PASSWORD": "sekret"},  # pragma: allowlist secret
        {"REDIS_PASSWORD": "sekret"},  # pragma: allowlist secret
    ]

    @pytest.mark.parametrize("env", CASES)
    def test_redacted_never_contains_password(self, env):
        r = resolve_redis_connection(env=env)
        assert "sekret" not in r.redacted_url
        assert "***" in r.redacted_url

    def test_no_password_redaction_is_identity(self):
        r = resolve_redis_connection(env={"REDIS_URL": "redis://h:6379/0"})
        assert r.redacted_url == r.url

    def test_special_char_password_quoted_and_redacted(self):
        r = resolve_redis_connection(
            env={
                "REDIS_URL": "redis://h:6379/0",
                "REDIS_PASSWORD": "p@ss/w:rd",  # pragma: allowlist secret
            }
        )
        assert "p%40ss%2Fw%3Ard" in r.url
        assert "p%40ss" not in r.redacted_url
