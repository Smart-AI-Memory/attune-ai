"""Unit tests for src/attune/workflows/caching.py

Tests cover:
- CachedResponse dataclass (construction, serialization, deserialization, edge cases)
- CacheAwareWorkflow protocol (actual members: name, _cache, _enable_cache,
  get_model_for_tier)
- CachingMixin behaviour (_maybe_setup_cache, _make_cache_key, _try_cache_lookup,
  _store_in_cache, _get_cache_type, _get_cache_stats)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.caching import CacheAwareWorkflow, CachedResponse, CachingMixin

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_cached_response(
    content: str = "Hello, world!",
    input_tokens: int = 10,
    output_tokens: int = 20,
) -> CachedResponse:
    """Factory helper to reduce boilerplate in tests."""
    return CachedResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


# ---------------------------------------------------------------------------
# CachedResponse – construction
# ---------------------------------------------------------------------------


class TestCachedResponseConstruction:
    """Tests that CachedResponse is constructed correctly."""

    def test_basic_construction(self):
        response = CachedResponse(content="Test content", input_tokens=5, output_tokens=15)
        assert response.content == "Test content"
        assert response.input_tokens == 5
        assert response.output_tokens == 15

    def test_empty_content(self):
        response = CachedResponse(content="", input_tokens=0, output_tokens=0)
        assert response.content == ""

    def test_zero_tokens(self):
        response = CachedResponse(content="text", input_tokens=0, output_tokens=0)
        assert response.input_tokens == 0
        assert response.output_tokens == 0

    def test_large_token_counts(self):
        response = CachedResponse(content="x" * 10_000, input_tokens=999_999, output_tokens=999_999)
        assert response.input_tokens == 999_999
        assert response.output_tokens == 999_999

    def test_multiline_content(self):
        multiline = "line1\nline2\nline3"
        response = CachedResponse(content=multiline, input_tokens=3, output_tokens=3)
        assert response.content == multiline

    def test_unicode_content(self):
        unicode_text = "こんにちは 🌍 ñoño"
        response = CachedResponse(content=unicode_text, input_tokens=7, output_tokens=7)
        assert response.content == unicode_text

    def test_whitespace_only_content(self):
        response = CachedResponse(content="   \t\n  ", input_tokens=1, output_tokens=1)
        assert response.content == "   \t\n  "


# ---------------------------------------------------------------------------
# CachedResponse – dataclass semantics
# ---------------------------------------------------------------------------


class TestCachedResponseDataclassSemantics:
    """Tests dataclass-level behaviour (equality, repr)."""

    def test_equality_same_values(self):
        r1 = make_cached_response("hello", 10, 20)
        r2 = make_cached_response("hello", 10, 20)
        assert r1 == r2

    def test_inequality_different_content(self):
        r1 = make_cached_response("hello", 10, 20)
        r2 = make_cached_response("world", 10, 20)
        assert r1 != r2

    def test_inequality_different_input_tokens(self):
        r1 = make_cached_response("hello", 10, 20)
        r2 = make_cached_response("hello", 99, 20)
        assert r1 != r2

    def test_inequality_different_output_tokens(self):
        r1 = make_cached_response("hello", 10, 20)
        r2 = make_cached_response("hello", 10, 99)
        assert r1 != r2

    def test_repr_contains_class_name(self):
        response = make_cached_response()
        assert "CachedResponse" in repr(response)

    def test_not_equal_to_none(self):
        response = make_cached_response()
        assert response is not None

    def test_not_equal_to_different_type(self):
        response = make_cached_response("hello", 10, 20)
        assert response != {"content": "hello", "input_tokens": 10, "output_tokens": 20}

    def test_mutable_dataclass_allows_assignment(self):
        """CachedResponse is a regular (non-frozen) dataclass."""
        response = make_cached_response("original", 1, 1)
        response.content = "modified"
        assert response.content == "modified"


# ---------------------------------------------------------------------------
# CachedResponse – to_dict
# ---------------------------------------------------------------------------


class TestCachedResponseToDict:
    """Tests the to_dict serialisation method."""

    def test_to_dict_returns_dict(self):
        response = make_cached_response()
        assert isinstance(response.to_dict(), dict)

    def test_to_dict_contains_expected_keys(self):
        response = make_cached_response("some text", 1, 2)
        result = response.to_dict()
        assert set(result.keys()) == {"content", "input_tokens", "output_tokens"}

    def test_to_dict_content_value(self):
        response = make_cached_response("hello", 1, 2)
        assert response.to_dict()["content"] == "hello"

    def test_to_dict_input_tokens_value(self):
        response = make_cached_response("hello", 42, 2)
        assert response.to_dict()["input_tokens"] == 42

    def test_to_dict_output_tokens_value(self):
        response = make_cached_response("hello", 1, 99)
        assert response.to_dict()["output_tokens"] == 99

    def test_to_dict_empty_content(self):
        response = CachedResponse(content="", input_tokens=0, output_tokens=0)
        d = response.to_dict()
        assert d["content"] == ""
        assert d["input_tokens"] == 0
        assert d["output_tokens"] == 0

    def test_to_dict_is_json_serialisable(self):
        response = make_cached_response("hello world", 10, 20)
        serialised = json.dumps(response.to_dict())
        assert isinstance(serialised, str)

    def test_to_dict_unicode_is_json_serialisable(self):
        response = make_cached_response("こんにちは", 5, 5)
        serialised = json.dumps(response.to_dict(), ensure_ascii=False)
        assert "こんにちは" in serialised

    def test_to_dict_returns_new_dict_each_call(self):
        response = make_cached_response()
        d1 = response.to_dict()
        d2 = response.to_dict()
        assert d1 == d2
        assert d1 is not d2

    def test_to_dict_mutation_does_not_affect_original(self):
        response = make_cached_response("original", 1, 1)
        d = response.to_dict()
        d["content"] = "mutated"
        assert response.content == "original"


# ---------------------------------------------------------------------------
# CachedResponse – from_dict
# ---------------------------------------------------------------------------


class TestCachedResponseFromDict:
    """Tests the from_dict deserialisation class method."""

    def test_from_dict_returns_cached_response_instance(self):
        d = {"content": "hi", "input_tokens": 3, "output_tokens": 7}
        result = CachedResponse.from_dict(d)
        assert isinstance(result, CachedResponse)

    def test_from_dict_content_is_restored(self):
        d = {"content": "restored text", "input_tokens": 1, "output_tokens": 2}
        assert CachedResponse.from_dict(d).content == "restored text"

    def test_from_dict_input_tokens_are_restored(self):
        d = {"content": "x", "input_tokens": 55, "output_tokens": 2}
        assert CachedResponse.from_dict(d).input_tokens == 55

    def test_from_dict_output_tokens_are_restored(self):
        d = {"content": "x", "input_tokens": 1, "output_tokens": 88}
        assert CachedResponse.from_dict(d).output_tokens == 88

    def test_roundtrip_to_dict_from_dict(self):
        original = make_cached_response("roundtrip text", 12, 34)
        restored = CachedResponse.from_dict(original.to_dict())
        assert restored == original

    def test_roundtrip_via_json(self):
        original = make_cached_response("json roundtrip", 7, 13)
        json_str = json.dumps(original.to_dict())
        restored = CachedResponse.from_dict(json.loads(json_str))
        assert restored == original

    def test_from_dict_missing_content_raises(self):
        with pytest.raises(KeyError):
            CachedResponse.from_dict({"input_tokens": 1, "output_tokens": 2})

    def test_from_dict_missing_input_tokens_raises(self):
        with pytest.raises(KeyError):
            CachedResponse.from_dict({"content": "text", "output_tokens": 2})

    def test_from_dict_missing_output_tokens_raises(self):
        with pytest.raises(KeyError):
            CachedResponse.from_dict({"content": "text", "input_tokens": 1})

    def test_from_dict_empty_dict_raises(self):
        with pytest.raises(KeyError):
            CachedResponse.from_dict({})


# ---------------------------------------------------------------------------
# Parametrised roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content, input_tokens, output_tokens",
    [
        ("", 0, 0),
        ("single word", 1, 1),
        ("multi\nline\ncontent", 3, 6),
        ("unicode: 日本語", 10, 20),
        ("special chars: <>&\"'", 5, 10),
        ("a" * 1000, 1000, 2000),
    ],
)
def test_roundtrip_parametrised(content, input_tokens, output_tokens):
    original = CachedResponse(
        content=content, input_tokens=input_tokens, output_tokens=output_tokens
    )
    restored = CachedResponse.from_dict(original.to_dict())
    assert restored == original


# ---------------------------------------------------------------------------
# CacheAwareWorkflow – protocol definition
# ---------------------------------------------------------------------------


class TestCacheAwareWorkflowProtocol:
    """Tests the CacheAwareWorkflow Protocol's actual interface.

    Actual protocol members (from caching.py):
      - name: str
      - _cache: BaseCache | None
      - _enable_cache: bool
      - get_model_for_tier(tier) -> str
    """

    def test_protocol_is_runtime_checkable(self):
        """CacheAwareWorkflow is decorated with @runtime_checkable."""
        # Should support isinstance() checks without TypeError
        assert isinstance(object(), CacheAwareWorkflow) is not None  # no TypeError

    def test_compliant_class_satisfies_isinstance(self):
        """A class with the required attributes satisfies the protocol."""

        class ConcreteWorkflow:
            name = "my-workflow"
            _cache = None
            _enable_cache = True

            def get_model_for_tier(self, tier: Any) -> str:
                return "claude-haiku-4-5"

        assert isinstance(ConcreteWorkflow(), CacheAwareWorkflow)

    def test_missing_get_model_for_tier_fails(self):
        """A class missing get_model_for_tier should fail the isinstance check."""

        class Incomplete:
            name = "wf"
            _cache = None
            _enable_cache = True
            # no get_model_for_tier

        assert not isinstance(Incomplete(), CacheAwareWorkflow)

    def test_protocol_has_name_attribute(self):
        # Protocol annotations live in __annotations__, not as class attrs
        assert "name" in CacheAwareWorkflow.__annotations__

    def test_protocol_has_cache_attribute(self):
        assert "_cache" in CacheAwareWorkflow.__annotations__

    def test_protocol_has_enable_cache_attribute(self):
        assert "_enable_cache" in CacheAwareWorkflow.__annotations__

    def test_protocol_has_get_model_for_tier(self):
        assert hasattr(CacheAwareWorkflow, "get_model_for_tier")


# ---------------------------------------------------------------------------
# CachingMixin – unit tests
# ---------------------------------------------------------------------------


class MinimalMixinHost(CachingMixin):
    """Minimal concrete class hosting CachingMixin for testing."""

    name = "test-workflow"

    def get_model_for_tier(self, tier: Any) -> str:
        return "claude-haiku-4-5"


class TestCachingMixinDefaults:
    """Tests default attribute values on a fresh CachingMixin host."""

    def test_cache_is_none_by_default(self):
        host = MinimalMixinHost()
        assert host._cache is None

    def test_enable_cache_true_by_default(self):
        host = MinimalMixinHost()
        assert host._enable_cache is True

    def test_cache_setup_attempted_false_by_default(self):
        host = MinimalMixinHost()
        assert host._cache_setup_attempted is False

    def test_name_attribute_available(self):
        host = MinimalMixinHost()
        assert host.name == "test-workflow"


class TestCachingMixinMakeCacheKey:
    """Tests _make_cache_key()."""

    def test_with_system_prompt(self):
        host = MinimalMixinHost()
        key = host._make_cache_key("sys", "user msg")
        assert "sys" in key
        assert "user msg" in key

    def test_without_system_prompt(self):
        host = MinimalMixinHost()
        key = host._make_cache_key("", "user only")
        assert key == "user only"

    def test_system_and_user_separated(self):
        host = MinimalMixinHost()
        key = host._make_cache_key("SYSTEM", "USER")
        assert "SYSTEM\n\nUSER" == key


class TestCachingMixinTryCacheLookup:
    """Tests _try_cache_lookup()."""

    def test_returns_none_when_cache_disabled(self):
        host = MinimalMixinHost()
        host._enable_cache = False
        result = host._try_cache_lookup("stage1", "sys", "user", "model-id")
        assert result is None

    def test_returns_none_when_no_cache(self):
        host = MinimalMixinHost()
        host._enable_cache = True
        host._cache = None
        result = host._try_cache_lookup("stage1", "sys", "user", "model-id")
        assert result is None

    def test_returns_cached_response_on_hit(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        mock_cache.get.return_value = {"content": "cached", "input_tokens": 5, "output_tokens": 10}
        host._cache = mock_cache
        host._enable_cache = True

        result = host._try_cache_lookup("stage1", "sys", "user", "model-id")
        assert isinstance(result, CachedResponse)
        assert result.content == "cached"

    def test_returns_none_on_cache_miss(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        host._cache = mock_cache
        host._enable_cache = True

        result = host._try_cache_lookup("stage1", "sys", "user", "model-id")
        assert result is None

    def test_handles_key_error_gracefully(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        mock_cache.get.side_effect = KeyError("bad key")
        host._cache = mock_cache
        host._enable_cache = True

        result = host._try_cache_lookup("stage1", "sys", "user", "model-id")
        assert result is None


class TestCachingMixinStoreInCache:
    """Tests _store_in_cache()."""

    def test_returns_false_when_cache_disabled(self):
        host = MinimalMixinHost()
        host._enable_cache = False
        result = host._store_in_cache("stage", "sys", "user", "model", make_cached_response())
        assert result is False

    def test_returns_false_when_no_cache(self):
        host = MinimalMixinHost()
        host._cache = None
        result = host._store_in_cache("stage", "sys", "user", "model", make_cached_response())
        assert result is False

    def test_returns_true_on_success(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        host._cache = mock_cache
        host._enable_cache = True

        result = host._store_in_cache("stage", "sys", "user", "model", make_cached_response())
        assert result is True
        mock_cache.put.assert_called_once()

    def test_returns_false_on_os_error(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        mock_cache.put.side_effect = OSError("disk full")
        host._cache = mock_cache
        host._enable_cache = True

        result = host._store_in_cache("stage", "sys", "user", "model", make_cached_response())
        assert result is False


class TestCachingMixinGetCacheType:
    """Tests _get_cache_type()."""

    def test_returns_none_string_when_no_cache(self):
        host = MinimalMixinHost()
        host._cache = None
        assert host._get_cache_type() == "none"

    def test_returns_cache_type_from_cache(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        mock_cache.cache_type = "semantic"
        host._cache = mock_cache
        assert host._get_cache_type() == "semantic"

    def test_returns_hash_default_when_no_cache_type_attr(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock(spec=[])  # no cache_type attribute
        host._cache = mock_cache
        assert host._get_cache_type() == "hash"


class TestCachingMixinGetCacheStats:
    """Tests _get_cache_stats()."""

    def test_returns_zeros_when_no_cache(self):
        host = MinimalMixinHost()
        host._cache = None
        stats = host._get_cache_stats()
        assert stats == {"hits": 0, "misses": 0, "hit_rate": 0.0}

    def test_returns_stats_from_cache(self):
        host = MinimalMixinHost()
        mock_stats = MagicMock()
        mock_stats.hits = 10
        mock_stats.misses = 5
        mock_stats.hit_rate = 0.667
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = mock_stats
        host._cache = mock_cache

        stats = host._get_cache_stats()
        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert stats["hit_rate"] == pytest.approx(0.667)

    def test_returns_zeros_when_get_stats_raises(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        mock_cache.get_stats.side_effect = AttributeError("no stats")
        host._cache = mock_cache

        stats = host._get_cache_stats()
        assert stats == {"hits": 0, "misses": 0, "hit_rate": 0.0}


class TestMaybeSetupCache:
    """Tests _maybe_setup_cache() lazy initialisation logic."""

    def test_skips_when_cache_disabled(self):
        host = MinimalMixinHost()
        host._enable_cache = False
        host._maybe_setup_cache()
        assert host._cache_setup_attempted is False

    def test_skips_second_call(self):
        host = MinimalMixinHost()
        host._cache_setup_attempted = True
        # Should return immediately without side effects
        host._maybe_setup_cache()

    def test_uses_existing_cache_if_provided(self):
        host = MinimalMixinHost()
        mock_cache = MagicMock()
        host._cache = mock_cache
        host._maybe_setup_cache()
        assert host._cache is mock_cache
        assert host._cache_setup_attempted is True

    def test_sets_attempted_flag(self):
        host = MinimalMixinHost()
        # auto_setup_cache/create_cache are lazy-imported inside _maybe_setup_cache
        # from attune.cache, so patch them there (not on the caching module)
        with (
            patch("attune.cache.auto_setup_cache"),
            patch("attune.cache.create_cache", return_value=MagicMock()),
        ):
            host._maybe_setup_cache()
        assert host._cache_setup_attempted is True
