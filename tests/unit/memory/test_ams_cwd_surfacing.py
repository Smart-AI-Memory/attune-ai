"""Unit tests for AMS cwd surfacing (recall cwd soft-sort parity).

`_cwd_from_topics` lets `AMSMemoryBackend.search()` surface a `cwd` field
the same way the file backend does, so `recall_entries`' cwd soft-sort
works for AMS users. The helper is importable without the optional
`agent-memory-client` dep (the client import is function-local), so this
runs in CI unconditionally.
"""

from __future__ import annotations

from attune_redis.memory import _cwd_from_topics


def test_extracts_cwd_marker():
    assert _cwd_from_topics(["type:bug", "cwd:/home/proj"]) == "/home/proj"


def test_returns_none_when_absent():
    assert _cwd_from_topics(["type:note", "ci"]) is None


def test_handles_none_and_empty():
    assert _cwd_from_topics(None) is None
    assert _cwd_from_topics([]) is None


def test_first_cwd_marker_wins():
    assert _cwd_from_topics(["cwd:/a", "cwd:/b"]) == "/a"


def test_ignores_non_string_topics():
    # Defensive: topics from a backend could be non-str; must not raise.
    assert _cwd_from_topics([123, None, "cwd:/ok"]) == "/ok"


def test_preserves_path_with_colons():
    # Only the leading "cwd:" prefix is stripped; the rest is the path.
    assert _cwd_from_topics(["cwd:/a/b:c"]) == "/a/b:c"
