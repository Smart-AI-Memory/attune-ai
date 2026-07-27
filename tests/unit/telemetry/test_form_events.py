"""Error-path coverage for :mod:`attune.telemetry.form_events` (#1655).

The uncovered statements are exactly the defensive branches — rotation,
the ``except OSError`` arms, and the ``DO_NOT_TRACK`` gate. Telemetry
must never break routing, so these paths are exercised with REAL
filesystem failures (a file where a directory should be, a directory
where the file should be, a read-only parent) rather than mocks,
per the issue's guidance and the "non-mocked round-trip" lesson.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from attune.telemetry.form_events import (
    _MAX_BYTES,
    _rotate_if_huge,
    inference_rate,
    log_submission,
    log_surface_decision,
    maybe_keyboard_hint,
    submission_count,
    surface_mix,
)

_POSIX_NON_ROOT = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="read-only-dir semantics need non-root POSIX",
)


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ATTUNE_HOME at tmp and clear the consent env vars."""
    home = tmp_path / "attune-home"
    monkeypatch.setenv("ATTUNE_HOME", str(home))
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("ATTUNE_FORM_TELEMETRY", raising=False)
    return home


def _events_file(home: Path) -> Path:
    return home / "telemetry" / "form_events.jsonl"


class TestRotation:
    def test_rotates_when_over_limit(self, _isolated_home: Path) -> None:
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"x" * (_MAX_BYTES + 1))

        _rotate_if_huge(path)

        assert not path.exists()
        rotated = list(path.parent.glob("form_events.*.jsonl"))
        assert len(rotated) == 1
        assert rotated[0].stat().st_size == _MAX_BYTES + 1

    def test_dated_sibling_collision_appends_counter(self, _isolated_home: Path) -> None:
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"x" * (_MAX_BYTES + 1))
        # First rotation claims the dated name…
        _rotate_if_huge(path)
        (dated,) = path.parent.glob("form_events.*.jsonl")
        # …second rotation the same day must not clobber it.
        path.write_bytes(b"y" * (_MAX_BYTES + 1))
        _rotate_if_huge(path)

        assert dated.read_bytes()[:1] == b"x"  # first rotation intact
        rotated = sorted(p.name for p in path.parent.glob("form_events.*.jsonl"))
        assert len(rotated) == 2
        assert any(".1.jsonl" in name for name in rotated)

    def test_small_file_untouched(self, _isolated_home: Path) -> None:
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_text("{}\n", encoding="utf-8")
        _rotate_if_huge(path)
        assert path.exists()
        assert not list(path.parent.glob("form_events.*.jsonl"))

    @_POSIX_NON_ROOT
    def test_rotation_oserror_swallowed(self, _isolated_home: Path) -> None:
        """A failed rename is a nicety lost, never an exception raised."""
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"x" * (_MAX_BYTES + 1))
        path.parent.chmod(0o500)  # rename needs write on the dir
        try:
            _rotate_if_huge(path)  # must not raise
            assert path.exists()  # rotation failed, file left in place
        finally:
            path.parent.chmod(0o700)


class TestLogSurfaceDecisionErrorPaths:
    def test_oserror_on_mkdir_swallowed(self, _isolated_home: Path) -> None:
        """A FILE squatting on the telemetry dir path → OSError → silent."""
        _isolated_home.mkdir(parents=True)
        (_isolated_home / "telemetry").write_text("not a dir", encoding="utf-8")

        log_surface_decision("widget", reason="test")  # must not raise

        assert (_isolated_home / "telemetry").is_file()  # unchanged

    def test_do_not_track_disables(self, _isolated_home: Path, monkeypatch) -> None:
        monkeypatch.setenv("DO_NOT_TRACK", "1")
        log_surface_decision("widget")
        assert not _events_file(_isolated_home).exists()

    def test_falsey_do_not_track_still_records(self, _isolated_home: Path, monkeypatch) -> None:
        monkeypatch.setenv("DO_NOT_TRACK", "0")
        log_surface_decision("ask", reason="test")
        lines = _events_file(_isolated_home).read_text(encoding="utf-8").splitlines()
        assert json.loads(lines[0])["surface"] == "ask"

    def test_do_not_track_disables_submission_log(self, _isolated_home: Path, monkeypatch) -> None:
        monkeypatch.setenv("DO_NOT_TRACK", "yes")
        log_submission()
        assert not _events_file(_isolated_home).exists()


class TestSurfaceMixErrorPaths:
    def test_unopenable_log_returns_empty(self, _isolated_home: Path) -> None:
        """A DIRECTORY squatting on the log path → OSError → {}."""
        _events_file(_isolated_home).mkdir(parents=True)
        assert surface_mix() == {}

    def test_missing_log_returns_empty(self, _isolated_home: Path) -> None:
        assert surface_mix() == {}

    def test_malformed_tail_skipped(self, _isolated_home: Path) -> None:
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_text(
            '{"event":"form_surface","surface":"widget"}\n{not json\n',
            encoding="utf-8",
        )
        assert surface_mix() == {"widget": 1}


class TestSubmissionPathsErrorArms:
    def test_log_submission_oserror_swallowed(self, _isolated_home: Path) -> None:
        """A FILE squatting on the telemetry dir path → OSError → silent."""
        _isolated_home.mkdir(parents=True)
        (_isolated_home / "telemetry").write_text("not a dir", encoding="utf-8")
        log_submission()  # must not raise
        assert (_isolated_home / "telemetry").is_file()

    def test_submission_count_missing_log_is_zero(self, _isolated_home: Path) -> None:
        assert submission_count() == 0

    def test_submission_count_skips_malformed_lines(self, _isolated_home: Path) -> None:
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_text(
            '{"event":"form_submitted"}\n'
            "{not json\n"
            '"just a string"\n'
            '{"event":"form_surface","surface":"ask"}\n'
            '{"event":"form_submitted"}\n',
            encoding="utf-8",
        )
        assert submission_count() == 2

    @_POSIX_NON_ROOT
    def test_keyboard_hint_oserror_returns_none(self, _isolated_home: Path) -> None:
        """Marker write failing must degrade to 'no hint', not an error."""
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_text('{"event":"form_submitted"}\n' * 10, encoding="utf-8")
        path.parent.chmod(0o500)  # marker write_text will fail
        try:
            assert maybe_keyboard_hint() is None
        finally:
            path.parent.chmod(0o700)


class TestInferenceRate:
    def test_missing_log_returns_zeros(self, _isolated_home: Path) -> None:
        rate = inference_rate()
        assert rate["forms"] == 0
        assert rate["inferred_share"] == 0.0

    def test_unopenable_log_returns_zeros(self, _isolated_home: Path) -> None:
        _events_file(_isolated_home).mkdir(parents=True)
        assert inference_rate()["forms"] == 0

    def test_counts_inferred_fields(self, _isolated_home: Path) -> None:
        path = _events_file(_isolated_home)
        path.parent.mkdir(parents=True)
        path.write_text(
            '{"event":"form_surface","question_count":4,"inferred_fields":2}\n'
            '{"event":"form_surface","question_count":2,"inferred_fields":2,'
            '"fully_inferred":true}\n'
            "{not json\n"
            '{"event":"form_submitted"}\n',
            encoding="utf-8",
        )
        rate = inference_rate()
        assert rate["forms"] == 2
        assert rate["fields"] == 6
        assert rate["fields_inferred"] == 4
        assert rate["fully_inferred"] == 1
        assert rate["inferred_share"] == round(4 / 6, 3)
