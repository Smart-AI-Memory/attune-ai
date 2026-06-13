"""Behavioral tests for PatternOperationsMixin (long_term_operations).

Covers list / delete / statistics for secure pattern management — no
prior dedicated test file (73%). A fake storage supplies controlled
pattern data (and error injection) and a fake audit logger records
events; a minimal _Host mixes in the operations.

Emphasis on the branches line coverage missed: classification /
pattern-type filters, access-denied exclusion, the best-effort
"retrieve returned None / raised" continues, delete validation +
permission + audit, and the statistics aggregation including its
bad-data continue.
"""

import pytest

from attune.memory.long_term_operations import PatternOperationsMixin
from attune.memory.long_term_types import Classification, PermissionError


class _FakeStorage:
    def __init__(self, patterns):
        self._patterns = patterns  # id -> pattern_data | None
        self.deleted: list[str] = []
        self.delete_result = True

    def list_patterns(self):
        return list(self._patterns.keys())

    def retrieve(self, pattern_id):
        return self._patterns.get(pattern_id)

    def delete(self, pattern_id):
        self.deleted.append(pattern_id)
        return self.delete_result


class _FakeAudit:
    def __init__(self):
        self.events = []

    def _write_event(self, event):
        self.events.append(event)


class _Host(PatternOperationsMixin):
    def __init__(self, storage, audit):
        self.storage = storage
        self.audit_logger = audit


def _pat(classification="PUBLIC", created_by="alice", pattern_type="general", **extra):
    return {
        "metadata": {
            "classification": classification,
            "created_by": created_by,
            "pattern_type": pattern_type,
            **extra,
        }
    }


def _host(patterns):
    return _Host(_FakeStorage(patterns), _FakeAudit())


# ===========================================================================
# list_patterns
# ===========================================================================


def test_list_returns_accessible_public_pattern_summary():
    host = _host({"p1": _pat(created_by="bob", created_at="t0", encrypted=True)})
    result = host.list_patterns(user_id="anyone")
    assert result == [
        {
            "pattern_id": "p1",
            "pattern_type": "general",
            "classification": "PUBLIC",
            "created_by": "bob",
            "created_at": "t0",
            "encrypted": True,
        }
    ]


def test_list_filters_by_classification():
    host = _host(
        {
            "pub": _pat(classification="PUBLIC"),
            "intl": _pat(classification="INTERNAL"),
        }
    )
    result = host.list_patterns(user_id="alice", classification=Classification.INTERNAL)
    assert [p["pattern_id"] for p in result] == ["intl"]


def test_list_filters_by_pattern_type():
    host = _host(
        {
            "a": _pat(pattern_type="auth"),
            "b": _pat(pattern_type="db"),
        }
    )
    result = host.list_patterns(user_id="alice", pattern_type="auth")
    assert [p["pattern_id"] for p in result] == ["a"]


def test_list_excludes_inaccessible_sensitive_pattern():
    # SENSITIVE is creator-only; a different user is denied -> excluded.
    host = _host({"s": _pat(classification="SENSITIVE", created_by="owner")})
    assert host.list_patterns(user_id="intruder") == []


def test_list_skips_none_retrieve():
    host = _host({"missing": None, "ok": _pat()})
    result = host.list_patterns(user_id="alice")
    assert [p["pattern_id"] for p in result] == ["ok"]


def test_list_skips_pattern_with_bad_metadata():
    # Invalid classification string raises KeyError in Classification[...],
    # caught by the best-effort guard; the valid one still returns.
    host = _host({"bad": _pat(classification="NONSENSE"), "ok": _pat()})
    result = host.list_patterns(user_id="alice")
    assert [p["pattern_id"] for p in result] == ["ok"]


# ===========================================================================
# delete_pattern
# ===========================================================================


@pytest.mark.parametrize("bad_id", ["", "   "])
def test_delete_empty_pattern_id_raises(bad_id):
    host = _host({})
    with pytest.raises(ValueError, match="pattern_id cannot be empty"):
        host.delete_pattern(bad_id, user_id="alice")


def test_delete_empty_user_id_raises():
    host = _host({"p1": _pat()})
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        host.delete_pattern("p1", user_id="  ")


def test_delete_missing_pattern_returns_false():
    host = _host({"p1": None})
    assert host.delete_pattern("p1", user_id="alice") is False


def test_delete_non_creator_raises_permission_error():
    host = _host({"p1": _pat(created_by="owner")})
    with pytest.raises(PermissionError, match="cannot delete"):
        host.delete_pattern("p1", user_id="intruder")


def test_delete_success_writes_audit_event():
    storage = _FakeStorage({"p1": _pat(created_by="alice", classification="PUBLIC")})
    audit = _FakeAudit()
    host = _Host(storage, audit)

    assert host.delete_pattern("p1", user_id="alice", session_id="s1") is True
    assert storage.deleted == ["p1"]
    assert len(audit.events) == 1
    assert audit.events[0].event_type == "delete_pattern"


def test_delete_storage_failure_returns_false_without_audit():
    storage = _FakeStorage({"p1": _pat(created_by="alice")})
    storage.delete_result = False
    audit = _FakeAudit()
    host = _Host(storage, audit)

    assert host.delete_pattern("p1", user_id="alice") is False
    assert audit.events == []  # no audit on failed delete


# ===========================================================================
# get_statistics
# ===========================================================================


def test_statistics_aggregates_counts():
    host = _host(
        {
            "a": _pat(classification="PUBLIC"),
            "b": _pat(classification="INTERNAL", encrypted=True),
            "c": _pat(classification="SENSITIVE", created_by="x", pii_removed=3),
        }
    )
    stats = host.get_statistics()
    assert stats["total_patterns"] == 3
    assert stats["by_classification"] == {"PUBLIC": 1, "INTERNAL": 1, "SENSITIVE": 1}
    assert stats["encrypted_count"] == 1
    assert stats["with_pii_scrubbed"] == 1


def test_statistics_skips_none_retrieve():
    host = _host({"gone": None, "ok": _pat(classification="PUBLIC")})
    stats = host.get_statistics()
    assert stats["total_patterns"] == 2  # counts ids
    assert stats["by_classification"]["PUBLIC"] == 1  # only the retrievable one


def test_statistics_skips_bad_classification():
    # Classification not in the counter dict -> KeyError -> best-effort continue.
    host = _host(
        {
            "weird": _pat(classification="WEIRD"),
            "ok": _pat(classification="PUBLIC"),
        }
    )
    stats = host.get_statistics()
    assert stats["by_classification"]["PUBLIC"] == 1
