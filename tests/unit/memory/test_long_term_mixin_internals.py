"""Internal-branch tests for LongTermOperationsMixin.

Covers the pattern LRU cache, the classification/pattern-type filter
branches, the storage-directory resolution ladder, and the
pattern-iteration error paths — the parts the broader memory suite
leaves uncovered. Each test drives the real mixin method with a small
fake `_long_term`, so a regression in the caching or filtering logic
turns these red.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.memory.long_term import Classification
from attune.memory.mixins.long_term_mixin import LongTermOperationsMixin


class _Host(LongTermOperationsMixin):
    """Minimal UnifiedMemory stand-in carrying the mixin's required attrs."""

    def __init__(self, long_term: Any = None, max_size: int = 128):
        self.user_id = "u"
        self._long_term = long_term
        self._pattern_cache: dict[str, dict[str, Any]] = {}
        self._pattern_cache_max_size = max_size


class _RaisingLongTerm:
    """A backend whose retrieve_pattern must NOT be called (proves cache hit)."""

    def retrieve_pattern(self, **_kw):
        raise AssertionError("backend hit on a cache hit")


class _StorageDirAttr:
    """Backend exposing .storage_dir directly."""

    def __init__(self, d: str):
        self.storage_dir = d


class _StorageObjAttr:
    """Backend exposing .storage.storage_dir but not .storage_dir."""

    class _S:
        def __init__(self, d: str):
            self.storage_dir = d

    def __init__(self, d: str):
        self.storage = self._S(d)


class _UnderscoreStorageAttr:
    """Backend exposing ._storage.storage_dir but not .storage_dir/.storage."""

    class _S:
        def __init__(self, d: str):
            self.storage_dir = d

    def __init__(self, d: str):
        self._storage = self._S(d)


class TestPatternCache:
    """LRU cache insertion, eviction, hit, and clear."""

    def test_cache_pattern_evicts_oldest_at_capacity(self):
        host = _Host(long_term=object(), max_size=2)
        host._cache_pattern("a", {"v": 1})
        host._cache_pattern("b", {"v": 2})
        host._cache_pattern("c", {"v": 3})  # evicts "a"

        assert "a" not in host._pattern_cache
        assert set(host._pattern_cache) == {"b", "c"}
        assert host._pattern_cache["c"] == {"v": 3}

    def test_recall_pattern_cache_hit_skips_backend(self):
        host = _Host(long_term=_RaisingLongTerm())
        cached = {"content": "from-cache"}
        host._pattern_cache["p1"] = cached

        result = host.recall_pattern("p1", use_cache=True)

        # Returned the cached object without touching the backend.
        assert result is cached

    def test_clear_pattern_cache_returns_count_and_empties(self):
        host = _Host(long_term=object())
        host._pattern_cache.update({"a": {}, "b": {}, "c": {}})

        cleared = host.clear_pattern_cache()

        assert cleared == 3
        assert host._pattern_cache == {}


class _PatternsHost(_Host):
    """Host that yields a fixed pattern list from _iter_all_patterns."""

    def __init__(self, patterns: list[dict[str, Any]], **kw):
        super().__init__(long_term=object(), **kw)
        self._patterns = patterns

    def _iter_all_patterns(self):
        yield from self._patterns


class TestFilterAndScore:
    """Filter branches in _filter_and_score_patterns."""

    def test_string_classification_keeps_matching_drops_others(self):
        host = _PatternsHost(
            [
                {"content": "x", "classification": "INTERNAL"},
                {"content": "y", "classification": "PUBLIC"},
            ]
        )

        results = list(
            host._filter_and_score_patterns(
                query=None, pattern_type=None, classification="INTERNAL"
            )
        )

        kept = [p for _, p in results]
        assert len(kept) == 1
        assert kept[0]["classification"] == "INTERNAL"

    def test_enum_classification_filters_by_value(self):
        host = _PatternsHost(
            [
                {"content": "x", "classification": Classification.PUBLIC.value},
                {"content": "y", "classification": Classification.SENSITIVE.value},
            ]
        )

        results = list(
            host._filter_and_score_patterns(
                query=None, pattern_type=None, classification=Classification.PUBLIC
            )
        )

        kept = [p for _, p in results]
        assert len(kept) == 1
        assert kept[0]["classification"] == Classification.PUBLIC.value

    def test_pattern_type_filter_drops_wrong_type(self):
        host = _PatternsHost(
            [
                {"content": "x", "pattern_type": "algo"},
                {"content": "y", "pattern_type": "protocol"},
            ]
        )

        results = list(
            host._filter_and_score_patterns(query=None, pattern_type="algo", classification=None)
        )

        kept = [p for _, p in results]
        assert len(kept) == 1
        assert kept[0]["pattern_type"] == "algo"


class TestSearchPatterns:
    """search_patterns top-N selection and error handling."""

    def test_returns_top_n_by_relevance(self):
        host = _PatternsHost(
            [
                {"content": "redis caching guide", "pattern_type": "doc"},
                {"content": "unrelated note", "pattern_type": "doc"},
                {"content": "caching and redis tips", "pattern_type": "doc"},
            ]
        )

        results = host.search_patterns(query="redis caching", limit=2)

        # Only the two redis/caching patterns score > 0; order is by score.
        assert len(results) == 2
        contents = {r["content"] for r in results}
        assert "unrelated note" not in contents

    def test_no_long_term_returns_empty(self):
        host = _Host(long_term=None)

        assert host.search_patterns(query="anything") == []

    def test_iteration_error_returns_empty(self):
        class _BoomHost(_Host):
            def _iter_all_patterns(self):
                raise RuntimeError("boom")

        host = _BoomHost(long_term=object())

        assert host.search_patterns(query="x") == []


class TestGetStorageDir:
    """The storage-directory resolution ladder."""

    def test_none_when_no_long_term(self):
        assert _Host(long_term=None)._get_storage_dir() is None

    def test_direct_storage_dir_attr(self):
        host = _Host(long_term=_StorageDirAttr("/tmp/qa_lt"))
        assert str(host._get_storage_dir()) == "/tmp/qa_lt"

    def test_storage_object_attr(self):
        host = _Host(long_term=_StorageObjAttr("/tmp/qa_lt2"))
        assert str(host._get_storage_dir()) == "/tmp/qa_lt2"

    def test_underscore_storage_attr(self):
        host = _Host(long_term=_UnderscoreStorageAttr("/tmp/qa_lt3"))
        assert str(host._get_storage_dir()) == "/tmp/qa_lt3"

    def test_returns_none_when_no_storage_attrs(self):
        # A bare object is truthy but exposes none of the storage attrs.
        host = _Host(long_term=object())
        assert host._get_storage_dir() is None


class TestIterAllPatterns:
    """_iter_all_patterns file reading and guards."""

    def test_yields_good_skips_bad_json_and_unreadable(self, tmp_path):
        import json

        good = tmp_path / "good.json"
        good.write_text(json.dumps({"content": "ok"}), encoding="utf-8")
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        # A directory named like a pattern file -> open() raises -> broad except.
        (tmp_path / "dir.json").mkdir()

        host = _Host(long_term=_StorageDirAttr(str(tmp_path)))
        patterns = list(host._iter_all_patterns())

        assert patterns == [{"content": "ok"}]

    def test_no_storage_dir_yields_nothing(self):
        host = _Host(long_term=None)  # _get_storage_dir -> None
        assert list(host._iter_all_patterns()) == []

    def test_nonexistent_storage_dir_yields_nothing(self, tmp_path):
        missing = tmp_path / "does_not_exist"
        host = _Host(long_term=_StorageDirAttr(str(missing)))
        assert list(host._iter_all_patterns()) == []
