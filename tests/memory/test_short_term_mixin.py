"""Behavioral tests for ShortTermOperationsMixin (mixins/short_term_mixin).

Covers working-memory stash/retrieve and pattern staging — no prior
dedicated test file (70%). A minimal _Host supplies the attributes the
mixin expects; fake file-session and short-term (Redis) backends record
calls and inject failures so the dual-backend branches, the TTL-strategy
mapping, and the best-effort Redis exception handlers are all exercised.
"""

from types import SimpleNamespace

import pytest

from attune.memory.mixins.short_term_mixin import ShortTermOperationsMixin
from attune.memory.types import AccessTier, AgentCredentials, TTLStrategy


class _FileSession:
    def __init__(self, value=None):
        self.stashed: list = []
        self._value = value

    def stash(self, key, value, ttl=None):
        self.stashed.append((key, value, ttl))

    def retrieve(self, key):
        return self._value


class _ShortTerm:
    def __init__(self, retrieve_value=None, stage_ok=True, staged=None):
        self.stashed: list = []
        self.staged_args: list = []
        self._retrieve_value = retrieve_value
        self._stage_ok = stage_ok
        self._staged = staged or []
        self.raise_on_stash = False
        self.raise_on_retrieve = False

    def stash(self, key, value, creds, ttl_strategy):
        if self.raise_on_stash:
            raise RuntimeError("redis down")
        self.stashed.append((key, value, creds, ttl_strategy))

    def retrieve(self, key, creds):
        if self.raise_on_retrieve:
            raise RuntimeError("redis down")
        return self._retrieve_value

    def stage_pattern(self, staged_pattern, creds):
        self.staged_args.append(staged_pattern)
        return self._stage_ok

    def list_staged_patterns(self, creds):
        return self._staged


class _Host(ShortTermOperationsMixin):
    def __init__(
        self,
        file_session=None,
        short_term=None,
        redis_available=False,
        default_ttl=3600,
    ):
        self.user_id = "alice"
        self.access_tier = AccessTier.CONTRIBUTOR
        self._file_session = file_session
        self._short_term = short_term
        self._redis_status = SimpleNamespace(available=redis_available) if short_term else None
        self.config = SimpleNamespace(default_ttl_seconds=default_ttl)


# ===========================================================================
# credentials
# ===========================================================================


def test_credentials_carries_user_and_tier():
    creds = _Host().credentials
    assert isinstance(creds, AgentCredentials)
    assert creds.agent_id == "alice"
    assert creds.tier == AccessTier.CONTRIBUTOR


# ===========================================================================
# stash
# ===========================================================================


def test_stash_to_file_session_returns_true():
    fs = _FileSession()
    host = _Host(file_session=fs)
    assert host.stash("k", "v", ttl_seconds=120) is True
    assert fs.stashed == [("k", "v", 120)]


def test_stash_without_file_session_returns_false():
    assert _Host().stash("k", "v") is False


def test_stash_uses_default_ttl_when_unspecified():
    fs = _FileSession()
    _Host(file_session=fs, default_ttl=999).stash("k", "v")
    assert fs.stashed[0][2] == 999  # config.default_ttl_seconds


def test_stash_redis_default_strategy_when_ttl_none():
    st = _ShortTerm()
    _Host(file_session=_FileSession(), short_term=st, redis_available=True).stash("k", "v")
    assert st.stashed[0][3] == TTLStrategy.WORKING_RESULTS


@pytest.mark.parametrize(
    "ttl,expected",
    [
        (100, TTLStrategy.SESSION),  # <= 1800
        (3000, TTLStrategy.WORKING_RESULTS),  # <= 3600
        (5000, TTLStrategy.STAGED_PATTERNS),  # <= 86400
        (999999, TTLStrategy.CONFLICT_CONTEXT),  # else
    ],
)
def test_stash_ttl_strategy_mapping(ttl, expected):
    st = _ShortTerm()
    host = _Host(file_session=_FileSession(), short_term=st, redis_available=True)
    host.stash("k", "v", ttl_seconds=ttl)
    assert st.stashed[0][3] == expected


def test_stash_swallows_redis_failure_still_true():
    st = _ShortTerm()
    st.raise_on_stash = True
    host = _Host(file_session=_FileSession(), short_term=st, redis_available=True)
    assert host.stash("k", "v") is True  # file session succeeded; redis error logged


def test_stash_skips_redis_when_unavailable():
    st = _ShortTerm()
    _Host(file_session=_FileSession(), short_term=st, redis_available=False).stash("k", "v")
    assert st.stashed == []  # redis branch skipped


# ===========================================================================
# retrieve
# ===========================================================================


def test_retrieve_prefers_redis_hit():
    st = _ShortTerm(retrieve_value="from-redis")
    fs = _FileSession(value="from-file")
    host = _Host(file_session=fs, short_term=st, redis_available=True)
    assert host.retrieve("k") == "from-redis"


def test_retrieve_falls_back_to_file_on_redis_miss():
    st = _ShortTerm(retrieve_value=None)
    fs = _FileSession(value="from-file")
    host = _Host(file_session=fs, short_term=st, redis_available=True)
    assert host.retrieve("k") == "from-file"


def test_retrieve_falls_back_on_redis_exception():
    st = _ShortTerm()
    st.raise_on_retrieve = True
    fs = _FileSession(value="from-file")
    host = _Host(file_session=fs, short_term=st, redis_available=True)
    assert host.retrieve("k") == "from-file"


def test_retrieve_file_only():
    assert _Host(file_session=_FileSession(value="x")).retrieve("k") == "x"


def test_retrieve_returns_none_when_no_backends():
    assert _Host().retrieve("k") is None


# ===========================================================================
# stage_pattern
# ===========================================================================


def test_stage_pattern_without_backend_returns_none():
    assert _Host().stage_pattern({"name": "p"}) is None


def test_stage_pattern_success_returns_id():
    st = _ShortTerm(stage_ok=True)
    host = _Host(short_term=st)
    pid = host.stage_pattern({"name": "p", "description": "d"}, pattern_type="algo")
    assert pid is not None and pid.startswith("staged_")
    assert st.staged_args[0].pattern_type == "algo"
    assert st.staged_args[0].agent_id == "alice"


def test_stage_pattern_failure_returns_none():
    host = _Host(short_term=_ShortTerm(stage_ok=False))
    assert host.stage_pattern({"name": "p"}) is None


def test_stage_pattern_puts_content_into_context():
    st = _ShortTerm(stage_ok=True)
    host = _Host(short_term=st)
    host.stage_pattern({"name": "p", "content": "the body"})
    assert st.staged_args[0].context["content"] == "the body"


# ===========================================================================
# get_staged_patterns
# ===========================================================================


def test_get_staged_patterns_without_backend_returns_empty():
    assert _Host().get_staged_patterns() == []


def test_get_staged_patterns_serializes_each():
    fake = SimpleNamespace(to_dict=lambda: {"pattern_id": "staged_1"})
    host = _Host(short_term=_ShortTerm(staged=[fake]))
    assert host.get_staged_patterns() == [{"pattern_id": "staged_1"}]
