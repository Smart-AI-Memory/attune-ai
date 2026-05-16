"""Unit tests for ``attune.ops.dismiss_store``.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T1).

Covers the five public functions:

- ``store_path``: path derivation
- ``load``: missing / corrupt / valid file roundtrip
- ``save``: atomic write, input validation, overwrite semantics
- ``clear``: removal + no-op
- ``is_active``: three-condition truth table + TTL boundary

All filesystem effects scoped to ``tmp_path`` so the user's real
``~/.attune/ops/`` is never touched.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.ops import dismiss_store
from attune.ops.config import Config


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    """Config rooted at tmp_path so writes don't touch the user's home."""
    return Config(
        project_root=tmp_path / "project",
        attune_home=tmp_path / "attune-home",
    )


def _write_raw(cfg: Config, content: str) -> Path:
    """Write arbitrary content directly to the store path, bypassing save()."""
    path = dismiss_store.store_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# store_path
# ---------------------------------------------------------------------------


class TestStorePath:
    def test_derives_from_attune_home(self, cfg: Config) -> None:
        expected = cfg.attune_home / "ops" / "spec_completion_dismissed.json"
        assert dismiss_store.store_path(cfg) == expected

    def test_does_not_create_anything(self, cfg: Config) -> None:
        path = dismiss_store.store_path(cfg)
        # Neither the file nor its parent dir should exist after this call.
        assert not path.exists()
        assert not path.parent.exists()


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------


class TestLoadMissing:
    def test_missing_file_returns_empty(self, cfg: Config) -> None:
        assert dismiss_store.load(cfg) == {}

    def test_missing_does_not_log_warning(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.WARNING, logger="attune.ops.dismiss_store")
        dismiss_store.load(cfg)
        assert caplog.records == []


class TestLoadCorrupt:
    def test_invalid_json_returns_empty_and_warns(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write_raw(cfg, "{not valid json")
        caplog.set_level(logging.WARNING, logger="attune.ops.dismiss_store")
        assert dismiss_store.load(cfg) == {}
        assert any("invalid JSON" in r.message for r in caplog.records)

    def test_non_object_root_returns_empty_and_warns(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write_raw(cfg, "[]")
        caplog.set_level(logging.WARNING, logger="attune.ops.dismiss_store")
        assert dismiss_store.load(cfg) == {}
        assert any("not a JSON object" in r.message for r in caplog.records)

    def test_wrong_schema_version_returns_empty_and_warns(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write_raw(cfg, json.dumps({"version": "bad", "dismissed": {}}))
        caplog.set_level(logging.WARNING, logger="attune.ops.dismiss_store")
        assert dismiss_store.load(cfg) == {}
        assert any("unsupported version" in r.message for r in caplog.records)

    def test_missing_dismissed_key_returns_empty(self, cfg: Config) -> None:
        _write_raw(cfg, json.dumps({"version": dismiss_store.SCHEMA_VERSION}))
        assert dismiss_store.load(cfg) == {}

    def test_dismissed_not_a_dict_returns_empty(self, cfg: Config) -> None:
        _write_raw(
            cfg,
            json.dumps({"version": dismiss_store.SCHEMA_VERSION, "dismissed": []}),
        )
        assert dismiss_store.load(cfg) == {}


class TestLoadMalformedEntry:
    """Per-entry corruption is skipped; other entries still load."""

    def _store_with(self, cfg: Config, entries: dict) -> None:
        _write_raw(
            cfg,
            json.dumps(
                {
                    "version": dismiss_store.SCHEMA_VERSION,
                    "dismissed": entries,
                }
            ),
        )

    def test_missing_fields(self, cfg: Config) -> None:
        self._store_with(
            cfg,
            {
                "bad-slug": {"dismissed_at": "2026-05-15T18:30:00+00:00"},
                "good-slug": {
                    "dismissed_at": "2026-05-15T18:30:00+00:00",
                    "snapshot_hash": "abc123",
                    "ttl_days": 14,
                },
            },
        )
        loaded = dismiss_store.load(cfg)
        assert "bad-slug" not in loaded
        assert "good-slug" in loaded

    def test_bad_datetime(self, cfg: Config) -> None:
        self._store_with(
            cfg,
            {
                "bad-slug": {
                    "dismissed_at": "not-a-date",
                    "snapshot_hash": "abc123",
                    "ttl_days": 14,
                },
            },
        )
        assert dismiss_store.load(cfg) == {}

    def test_naive_datetime_rejected(self, cfg: Config) -> None:
        # Tz-naive ISO strings can't be safely compared with tz-aware now.
        self._store_with(
            cfg,
            {
                "bad-slug": {
                    "dismissed_at": "2026-05-15T18:30:00",
                    "snapshot_hash": "abc123",
                    "ttl_days": 14,
                },
            },
        )
        assert dismiss_store.load(cfg) == {}

    def test_bool_ttl_rejected(self, cfg: Config) -> None:
        # bool is a subclass of int in Python; the parser must explicitly
        # reject it (TTL=True would silently mean TTL=1 day).
        self._store_with(
            cfg,
            {
                "bad-slug": {
                    "dismissed_at": "2026-05-15T18:30:00+00:00",
                    "snapshot_hash": "abc123",
                    "ttl_days": True,
                },
            },
        )
        assert dismiss_store.load(cfg) == {}

    def test_negative_ttl_rejected(self, cfg: Config) -> None:
        self._store_with(
            cfg,
            {
                "bad-slug": {
                    "dismissed_at": "2026-05-15T18:30:00+00:00",
                    "snapshot_hash": "abc123",
                    "ttl_days": -1,
                },
            },
        )
        assert dismiss_store.load(cfg) == {}


# ---------------------------------------------------------------------------
# save (roundtrip + validation + atomicity)
# ---------------------------------------------------------------------------


class TestSaveRoundtrip:
    def test_save_then_load(self, cfg: Config) -> None:
        now = datetime(2026, 5, 15, 18, 30, tzinfo=timezone.utc)
        dismiss_store.save("ops-sessions-page", "hash-1", cfg, now=now)
        loaded = dismiss_store.load(cfg)
        assert "ops-sessions-page" in loaded
        entry = loaded["ops-sessions-page"]
        assert entry.snapshot_hash == "hash-1"
        assert entry.ttl_days == dismiss_store.DEFAULT_TTL_DAYS
        assert entry.dismissed_at == now

    def test_save_creates_parent_dir(self, cfg: Config) -> None:
        # attune_home/ops/ doesn't exist yet
        assert not (cfg.attune_home / "ops").exists()
        dismiss_store.save("slug", "hash", cfg)
        assert dismiss_store.store_path(cfg).is_file()

    def test_save_overwrites_prior_entry(self, cfg: Config) -> None:
        now1 = datetime(2026, 5, 15, 18, 0, tzinfo=timezone.utc)
        now2 = datetime(2026, 5, 16, 9, 0, tzinfo=timezone.utc)
        dismiss_store.save("slug", "old-hash", cfg, now=now1)
        dismiss_store.save("slug", "new-hash", cfg, now=now2)
        loaded = dismiss_store.load(cfg)
        assert len(loaded) == 1
        assert loaded["slug"].snapshot_hash == "new-hash"
        assert loaded["slug"].dismissed_at == now2

    def test_multiple_slugs_coexist(self, cfg: Config) -> None:
        dismiss_store.save("slug-a", "hash-a", cfg)
        dismiss_store.save("slug-b", "hash-b", cfg)
        loaded = dismiss_store.load(cfg)
        assert set(loaded.keys()) == {"slug-a", "slug-b"}

    def test_uses_utc_now_when_not_injected(self, cfg: Config) -> None:
        before = datetime.now(timezone.utc)
        dismiss_store.save("slug", "hash", cfg)
        after = datetime.now(timezone.utc)
        entry = dismiss_store.load(cfg)["slug"]
        assert entry.dismissed_at.tzinfo is not None
        assert before <= entry.dismissed_at <= after

    def test_custom_ttl_persists(self, cfg: Config) -> None:
        dismiss_store.save("slug", "hash", cfg, ttl_days=7)
        assert dismiss_store.load(cfg)["slug"].ttl_days == 7


class TestSaveValidation:
    def test_empty_slug_rejected(self, cfg: Config) -> None:
        with pytest.raises(ValueError, match="slug"):
            dismiss_store.save("", "hash", cfg)

    def test_non_string_slug_rejected(self, cfg: Config) -> None:
        with pytest.raises(ValueError, match="slug"):
            dismiss_store.save(123, "hash", cfg)  # type: ignore[arg-type]

    def test_empty_hash_rejected(self, cfg: Config) -> None:
        with pytest.raises(ValueError, match="snapshot_hash"):
            dismiss_store.save("slug", "", cfg)

    def test_negative_ttl_rejected(self, cfg: Config) -> None:
        with pytest.raises(ValueError, match="ttl_days"):
            dismiss_store.save("slug", "hash", cfg, ttl_days=-1)


class TestSaveAtomicity:
    def test_no_temp_files_left_after_save(self, cfg: Config) -> None:
        dismiss_store.save("slug", "hash", cfg)
        parent = dismiss_store.store_path(cfg).parent
        leftovers = [p.name for p in parent.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == []

    def test_back_to_back_saves_yield_latest(self, cfg: Config) -> None:
        # No threading here — the "concurrent-write smoke" requirement
        # from the spec maps to: rapid consecutive saves leave a single
        # well-formed entry with the latest content, and no temp files.
        for i in range(5):
            dismiss_store.save("slug", f"hash-{i}", cfg)
        loaded = dismiss_store.load(cfg)
        assert loaded["slug"].snapshot_hash == "hash-4"
        parent = dismiss_store.store_path(cfg).parent
        leftovers = [p.name for p in parent.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == []


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    def test_removes_entry(self, cfg: Config) -> None:
        dismiss_store.save("slug-a", "hash-a", cfg)
        dismiss_store.save("slug-b", "hash-b", cfg)
        dismiss_store.clear("slug-a", cfg)
        loaded = dismiss_store.load(cfg)
        assert "slug-a" not in loaded
        assert "slug-b" in loaded

    def test_missing_slug_is_noop(self, cfg: Config) -> None:
        # No prior save → clear should not raise and not create the file.
        dismiss_store.clear("nope", cfg)
        assert not dismiss_store.store_path(cfg).exists()

    def test_clearing_only_entry_leaves_empty_store(self, cfg: Config) -> None:
        dismiss_store.save("slug", "hash", cfg)
        dismiss_store.clear("slug", cfg)
        assert dismiss_store.load(cfg) == {}


# ---------------------------------------------------------------------------
# is_active (the three-condition truth table)
# ---------------------------------------------------------------------------


class TestIsActiveMissing:
    def test_unknown_slug_inactive(self, cfg: Config) -> None:
        assert dismiss_store.is_active("never-dismissed", "any-hash", cfg) is False

    def test_unreadable_store_inactive(self, cfg: Config) -> None:
        _write_raw(cfg, "{not valid")
        assert dismiss_store.is_active("anything", "hash", cfg) is False


class TestIsActiveHashMismatch:
    def test_different_hash_inactive_even_within_ttl(self, cfg: Config) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        dismiss_store.save("slug", "original-hash", cfg, now=now)
        # Same day, well within TTL — but the hash changed (new signal
        # landed). Must re-surface.
        result = dismiss_store.is_active(
            "slug",
            "new-hash",
            cfg,
            now=now + timedelta(hours=1),
        )
        assert result is False


class TestIsActiveTTLBoundary:
    """The 14-day default TTL window."""

    def setup_method(self) -> None:
        self.dismissed_at = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)

    def test_13d_23h_active(self, cfg: Config) -> None:
        dismiss_store.save("slug", "hash", cfg, now=self.dismissed_at)
        check_at = self.dismissed_at + timedelta(days=13, hours=23)
        assert dismiss_store.is_active("slug", "hash", cfg, now=check_at) is True

    def test_14d_1h_inactive(self, cfg: Config) -> None:
        dismiss_store.save("slug", "hash", cfg, now=self.dismissed_at)
        check_at = self.dismissed_at + timedelta(days=14, hours=1)
        assert dismiss_store.is_active("slug", "hash", cfg, now=check_at) is False

    def test_exact_boundary_inactive(self, cfg: Config) -> None:
        # Condition 3 uses strict ``<``: at exactly TTL, the dismiss expires.
        dismiss_store.save("slug", "hash", cfg, now=self.dismissed_at)
        check_at = self.dismissed_at + timedelta(days=14)
        assert dismiss_store.is_active("slug", "hash", cfg, now=check_at) is False

    def test_custom_ttl_honored(self, cfg: Config) -> None:
        dismiss_store.save("slug", "hash", cfg, ttl_days=7, now=self.dismissed_at)
        within = self.dismissed_at + timedelta(days=6, hours=23)
        past = self.dismissed_at + timedelta(days=7, hours=1)
        assert dismiss_store.is_active("slug", "hash", cfg, now=within) is True
        assert dismiss_store.is_active("slug", "hash", cfg, now=past) is False

    def test_zero_ttl_immediately_inactive(self, cfg: Config) -> None:
        # Edge case: TTL=0 should be inactive even at the moment of dismissal.
        dismiss_store.save("slug", "hash", cfg, ttl_days=0, now=self.dismissed_at)
        assert dismiss_store.is_active("slug", "hash", cfg, now=self.dismissed_at) is False


class TestIsActiveHappyPath:
    def test_matching_hash_within_ttl(self, cfg: Config) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        dismiss_store.save("slug", "hash", cfg, now=now)
        assert dismiss_store.is_active("slug", "hash", cfg, now=now) is True
