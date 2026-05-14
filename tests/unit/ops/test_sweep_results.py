"""Unit tests for the discovery-sweep scope-keyed results storage.

Spec: docs/specs/discovery-sweep-ops-integration/design.md
      (Phase 2A — sweep_results storage primitives)

Covers the four primitives in ``attune.ops.sweep_results``:

- ``scope_hash``: canonicalization + collision properties.
- ``parse_lines``: ATTUNE_DS round-trip from captured stdout.
- ``persist_result`` / ``read_result``: atomic write + scope-keyed
  read. Latest-only semantics.
- ``persist_from_lines``: composition wrapper used by the
  upcoming Phase 2B daemon hook.

No HTTP routes, no daemon wiring — those are Phase 2B and require
modifying conflict-prone files (runner.py, server.py, routes/runner.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.ops import sweep_results
from attune.ops.config import Config
from attune.workflows.discovery_sweep import ds_stdout


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    """Config rooted at tmp_path so writes don't touch the user's home."""
    return Config(
        project_root=tmp_path / "project",
        attune_home=tmp_path / "attune-home",
    )


def _captured_lines(
    *, sweep_payload: dict, source: str = "fake", findings_count: int = 1
) -> list[str]:
    """Build a fake captured-stdout buffer matching ds_stdout's grammar."""
    return [
        f"ATTUNE_DS_VERSION {ds_stdout.VERSION}",
        f"ATTUNE_DS source_started {source} ts=2026-05-13T12:00:00+00:00",
        (
            f"ATTUNE_DS source_finished {source} "
            f"ts=2026-05-13T12:00:05+00:00 findings={findings_count}"
        ),
        f"ATTUNE_DS final {json.dumps(sweep_payload)}",
    ]


# ---------------------------------------------------------------------------
# Persistence-flag gate
# ---------------------------------------------------------------------------


class TestPersistenceFlag:
    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(sweep_results.ENABLE_ENV, raising=False)
        assert sweep_results.is_persistence_enabled() is False

    def test_empty_value_is_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(sweep_results.ENABLE_ENV, "")
        assert sweep_results.is_persistence_enabled() is False

    def test_any_truthy_value_enables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for value in ("1", "true", "yes", "anything"):
            monkeypatch.setenv(sweep_results.ENABLE_ENV, value)
            assert sweep_results.is_persistence_enabled() is True


# ---------------------------------------------------------------------------
# scope_hash
# ---------------------------------------------------------------------------


class TestScopeHash:
    def test_deterministic(self) -> None:
        h1 = sweep_results.scope_hash("src/")
        h2 = sweep_results.scope_hash("src/")
        assert h1 == h2

    def test_length_matches_constant(self) -> None:
        h = sweep_results.scope_hash("src/")
        assert len(h) == sweep_results.HASH_LENGTH

    def test_distinct_paths_distinct_hashes(self) -> None:
        assert sweep_results.scope_hash("src/") != sweep_results.scope_hash("tests/")

    def test_canonicalizes_equivalent_paths(self, tmp_path: Path) -> None:
        # Same resolved path through different surface forms should hash
        # identically. The "./X" vs "X" forms are the most common
        # equivalence the dashboard will hit.
        (tmp_path / "src").mkdir()
        a = sweep_results.scope_hash(str(tmp_path / "src"))
        b = sweep_results.scope_hash(str(tmp_path / "src") + "/")
        c = sweep_results.scope_hash(f"{tmp_path}/./src")
        assert a == b == c

    def test_empty_path_does_not_canonicalize(self) -> None:
        # Empty path → Path.resolve() would return cwd, which would be
        # misleading. The function hashes the empty string directly.
        h_empty = sweep_results.scope_hash("")
        h_dot = sweep_results.scope_hash(".")
        assert h_empty != h_dot


# ---------------------------------------------------------------------------
# parse_lines
# ---------------------------------------------------------------------------


class TestParseLines:
    def test_round_trip_with_valid_payload(self) -> None:
        payload = {
            "queue": [{"source": "x"}],
            "questions": [],
            "rejected": [],
            "metadata": {"sources": ["x"]},
        }
        lines = _captured_lines(sweep_payload=payload)
        result = sweep_results.parse_lines(lines)
        assert result == payload

    def test_missing_version_line_returns_none(self) -> None:
        # No version → can't trust the wire format; refuse.
        payload = {"queue": [], "questions": [], "rejected": [], "metadata": {}}
        lines = [
            f"ATTUNE_DS final {json.dumps(payload)}",
        ]
        assert sweep_results.parse_lines(lines) is None

    def test_version_mismatch_returns_none(self, caplog: pytest.LogCaptureFixture) -> None:
        # Future version → refuse to parse so the daemon doesn't
        # persist data it might be reading wrong.
        payload = {"queue": [], "questions": [], "rejected": [], "metadata": {}}
        lines = [
            "ATTUNE_DS_VERSION 99",
            f"ATTUNE_DS final {json.dumps(payload)}",
        ]
        with caplog.at_level("WARNING"):
            assert sweep_results.parse_lines(lines) is None
        assert any("version mismatch" in r.getMessage() for r in caplog.records)

    def test_missing_final_line_returns_none(self) -> None:
        # Version line + events, but no final blob → nothing to persist.
        lines = [
            f"ATTUNE_DS_VERSION {ds_stdout.VERSION}",
            "ATTUNE_DS source_started fake ts=2026-05-13T12:00:00+00:00",
        ]
        assert sweep_results.parse_lines(lines) is None

    def test_malformed_final_json_returns_none(self, caplog: pytest.LogCaptureFixture) -> None:
        lines = [
            f"ATTUNE_DS_VERSION {ds_stdout.VERSION}",
            "ATTUNE_DS final {not valid json",
        ]
        with caplog.at_level("WARNING"):
            assert sweep_results.parse_lines(lines) is None
        assert any("not valid JSON" in r.getMessage() for r in caplog.records)

    def test_ignores_interleaved_non_attune_ds_lines(self) -> None:
        # The subprocess stdout can carry markdown + ATTUNE_DS together
        # (depending on output_format). parse_lines must not be fragile
        # to interleaving.
        payload = {"queue": [], "questions": [], "rejected": [], "metadata": {}}
        lines = [
            "## Queue (0 findings)",
            f"ATTUNE_DS_VERSION {ds_stdout.VERSION}",
            "## Questions (0 findings)",
            "ATTUNE_DS source_started fake ts=2026-05-13T12:00:00+00:00",
            "Some other stdout noise",
            f"ATTUNE_DS final {json.dumps(payload)}",
            "Spent: $0.00 / $10.00 budget",
        ]
        result = sweep_results.parse_lines(lines)
        assert result == payload


# ---------------------------------------------------------------------------
# persist_result + read_result
# ---------------------------------------------------------------------------


class TestPersistAndRead:
    def test_persist_writes_to_scope_keyed_file(self, cfg: Config) -> None:
        payload = {
            "queue": [{"source": "x"}],
            "questions": [],
            "rejected": [],
            "metadata": {},
        }
        target = sweep_results.persist_result("src/", payload, cfg)
        assert target.exists()
        assert target.name == f"{sweep_results.scope_hash('src/')}.json"
        assert json.loads(target.read_text(encoding="utf-8")) == payload

    def test_read_round_trip(self, cfg: Config) -> None:
        payload = {"queue": [], "questions": [], "rejected": [], "metadata": {}}
        sweep_results.persist_result("src/", payload, cfg)
        digest = sweep_results.scope_hash("src/")
        assert sweep_results.read_result(digest, cfg) == payload

    def test_read_missing_returns_none(self, cfg: Config) -> None:
        assert sweep_results.read_result("0000000000000000", cfg) is None

    def test_latest_only_semantics(self, cfg: Config) -> None:
        # Two writes for the same scope → second wins; only one file
        # on disk for that scope. (History is post-v1 per decisions.md.)
        first = {"queue": [{"v": 1}], "questions": [], "rejected": [], "metadata": {}}
        second = {"queue": [{"v": 2}], "questions": [], "rejected": [], "metadata": {}}
        sweep_results.persist_result("src/", first, cfg)
        sweep_results.persist_result("src/", second, cfg)
        digest = sweep_results.scope_hash("src/")
        assert sweep_results.read_result(digest, cfg) == second
        files = list(sweep_results.results_dir(cfg).iterdir())
        assert [f.name for f in files] == [f"{digest}.json"]

    def test_distinct_scopes_do_not_collide(self, cfg: Config) -> None:
        a = {"queue": [{"scope": "src"}], "questions": [], "rejected": [], "metadata": {}}
        b = {"queue": [{"scope": "tests"}], "questions": [], "rejected": [], "metadata": {}}
        sweep_results.persist_result("src/", a, cfg)
        sweep_results.persist_result("tests/", b, cfg)
        assert sweep_results.read_result(sweep_results.scope_hash("src/"), cfg) == a
        assert sweep_results.read_result(sweep_results.scope_hash("tests/"), cfg) == b

    def test_read_corrupt_file_returns_none(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        out_dir = sweep_results.results_dir(cfg)
        digest = "deadbeefdeadbeef"
        (out_dir / f"{digest}.json").write_text("{not valid", encoding="utf-8")
        with caplog.at_level("WARNING"):
            assert sweep_results.read_result(digest, cfg) is None
        assert any("unreadable" in r.getMessage() for r in caplog.records)

    def test_persist_creates_results_dir(self, cfg: Config) -> None:
        # Fresh attune_home → directory tree doesn't exist yet.
        assert not (cfg.attune_home / "ops" / "sweep-results").exists()
        payload = {"queue": [], "questions": [], "rejected": [], "metadata": {}}
        sweep_results.persist_result("src/", payload, cfg)
        assert (cfg.attune_home / "ops" / "sweep-results").is_dir()

    def test_persist_is_atomic_no_tempfile_left_behind(self, cfg: Config) -> None:
        # After a successful write the only file in the dir should be
        # the target; no .tmp leftovers.
        payload = {"queue": [], "questions": [], "rejected": [], "metadata": {}}
        sweep_results.persist_result("src/", payload, cfg)
        files = list(sweep_results.results_dir(cfg).iterdir())
        assert len(files) == 1
        assert not files[0].name.endswith(".tmp")


# ---------------------------------------------------------------------------
# persist_from_lines
# ---------------------------------------------------------------------------


class TestPersistFromLines:
    def test_success_path(self, cfg: Config) -> None:
        payload = {
            "queue": [{"source": "x"}],
            "questions": [],
            "rejected": [],
            "metadata": {},
        }
        lines = _captured_lines(sweep_payload=payload)
        path = sweep_results.persist_from_lines("src/", lines, cfg)
        assert path is not None
        assert path.exists()
        digest = sweep_results.scope_hash("src/")
        assert sweep_results.read_result(digest, cfg) == payload

    def test_invalid_payload_returns_none_and_writes_nothing(self, cfg: Config) -> None:
        # No version line → parse_lines returns None → no file written.
        lines = ["random stdout noise", "## Queue (0 findings)"]
        result = sweep_results.persist_from_lines("src/", lines, cfg)
        assert result is None
        # results_dir is created by results_dir() — but it should be empty.
        assert list(sweep_results.results_dir(cfg).iterdir()) == []
