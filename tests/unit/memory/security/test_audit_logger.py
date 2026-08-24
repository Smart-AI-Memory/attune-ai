"""Behavioral tests for the core audit logger.

Codex-authored under the first post-activation delegated lane
(feature-lead model); integrated by the lead. Real files under
tmp_path -- the file-op seam is the point.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from attune.memory.security.audit_logger import AuditEvent, AuditLogger


def make_event(sequence: int = 1) -> AuditEvent:
    """Create a representative audit event."""
    return AuditEvent(
        event_type="test_event",
        user_id="user@example.com",
        status="success",
        data={"sequence": sequence, "message": "héllo"},
    )


class TestInitialization:
    def test_explicit_log_directory_and_configuration(self, tmp_path):
        log_dir = tmp_path / "audit"

        audit_logger = AuditLogger(
            log_dir=str(log_dir),
            log_filename="security.jsonl",
            retention_days=14,
            enable_rotation=False,
        )

        assert audit_logger.log_dir == log_dir
        assert audit_logger.log_path == log_dir / "security.jsonl"
        assert audit_logger.retention_days == 14
        assert audit_logger.enable_rotation is False
        assert log_dir.is_dir()

    def test_default_configuration_uses_platform_log_directory(
        self,
        tmp_path,
        monkeypatch,
    ):
        default_dir = tmp_path / "platform-logs"
        monkeypatch.setattr(
            "attune.platform_utils.get_default_log_dir",
            lambda: default_dir,
        )

        audit_logger = AuditLogger()

        assert audit_logger.log_dir == default_dir
        assert audit_logger.log_path == default_dir / "audit.jsonl"
        assert audit_logger.retention_days == 365
        assert audit_logger.enable_rotation is True
        assert default_dir.is_dir()

    def test_initialization_requests_restrictive_permissions(
        self,
        tmp_path,
        monkeypatch,
    ):
        chmod_calls = []
        monkeypatch.setattr(
            os,
            "chmod",
            lambda path, mode: chmod_calls.append((Path(path), mode)),
        )
        log_dir = tmp_path / "restricted"

        AuditLogger(log_dir=str(log_dir))

        assert chmod_calls == [(log_dir, 0o700)]

    def test_mkdir_failure_falls_back_to_local_logs(
        self,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)
        original_mkdir = Path.mkdir
        calls = 0

        def fail_first_mkdir(path, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise PermissionError("primary directory unavailable")
            return original_mkdir(path, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", fail_first_mkdir)
        # #2242: fallback is home-relative (never cwd-relative ./logs)
        # and carries the same 0o700 as the primary directory.
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

        audit_logger = AuditLogger(log_dir=str(tmp_path / "unavailable"))

        expected = tmp_path / "home" / ".attune" / "logs" / "audit"
        assert audit_logger.log_dir == expected
        assert audit_logger.log_path == expected / "audit.jsonl"
        assert expected.is_dir()
        assert (expected.stat().st_mode & 0o777) == 0o700


class TestWriting:
    def test_write_event_appends_one_parseable_json_line_per_event(
        self,
        tmp_path,
    ):
        audit_logger = AuditLogger(log_dir=str(tmp_path))
        first = make_event(1)
        second = make_event(2)

        audit_logger._write_event(first)
        first_contents = audit_logger.log_path.read_text(encoding="utf-8")
        audit_logger._write_event(second)

        contents = audit_logger.log_path.read_text(encoding="utf-8")
        lines = contents.splitlines()

        assert len(lines) == 2
        assert contents.startswith(first_contents)
        assert first_contents.endswith("\n")
        assert json.loads(lines[0])["sequence"] == 1
        assert json.loads(lines[1])["sequence"] == 2
        assert json.loads(lines[0])["message"] == "héllo"

    def test_write_failure_is_swallowed_and_reported(
        self,
        tmp_path,
        monkeypatch,
        caplog,
        capsys,
    ):
        audit_logger = AuditLogger(
            log_dir=str(tmp_path),
            enable_console_logging=True,
        )

        def failing_dump(*args, **kwargs):
            raise OSError("disk unavailable")

        monkeypatch.setattr(json, "dump", failing_dump)

        with caplog.at_level(logging.ERROR):
            audit_logger._write_event(make_event())

        assert "Failed to write audit event: disk unavailable" in caplog.text
        assert "AUDIT LOG FAILURE: disk unavailable" in capsys.readouterr().out

    def test_console_logging_records_successful_event(
        self,
        tmp_path,
        caplog,
    ):
        audit_logger = AuditLogger(
            log_dir=str(tmp_path),
            enable_console_logging=True,
        )

        with caplog.at_level(logging.DEBUG):
            audit_logger._write_event(make_event())

        assert "Audit event: test_event - success" in caplog.text


class TestRotation:
    def test_oversized_file_rotates_before_next_write(self, tmp_path):
        audit_logger = AuditLogger(
            log_dir=str(tmp_path),
            max_file_size_mb=0,
        )
        audit_logger._write_event(make_event(1))
        original_line = audit_logger.log_path.read_text(encoding="utf-8")

        audit_logger._write_event(make_event(2))

        rotated_files = list(tmp_path.glob("audit.jsonl.*"))
        assert len(rotated_files) == 1
        assert rotated_files[0].name.startswith("audit.jsonl.")
        datetime.strptime(
            rotated_files[0].name.removeprefix("audit.jsonl."),
            "%Y%m%d_%H%M%S",
        )
        assert rotated_files[0].read_text(encoding="utf-8") == original_line

        fresh_lines = audit_logger.log_path.read_text(
            encoding="utf-8",
        ).splitlines()
        assert len(fresh_lines) == 1
        assert json.loads(fresh_lines[0])["sequence"] == 2

    def test_rotation_disabled_keeps_events_in_original_file(self, tmp_path):
        audit_logger = AuditLogger(
            log_dir=str(tmp_path),
            max_file_size_mb=0,
            enable_rotation=False,
        )

        audit_logger._write_event(make_event(1))
        audit_logger._write_event(make_event(2))

        assert list(tmp_path.glob("audit.jsonl.*")) == []
        lines = audit_logger.log_path.read_text(encoding="utf-8").splitlines()
        assert [json.loads(line)["sequence"] for line in lines] == [1, 2]


class TestCleanup:
    def test_cleanup_removes_only_expired_well_named_logs(self, tmp_path):
        audit_logger = AuditLogger(
            log_dir=str(tmp_path),
            retention_days=30,
        )
        now = datetime.now(timezone.utc)
        old_stamp = (now - timedelta(days=60)).strftime("%Y%m%d_%H%M%S")
        recent_stamp = (now - timedelta(days=1)).strftime("%Y%m%d_%H%M%S")
        old_log = tmp_path / f"audit.jsonl.{old_stamp}"
        recent_log = tmp_path / f"audit.jsonl.{recent_stamp}"
        malformed_log = tmp_path / "audit.jsonl.badformat"
        old_log.write_text("old\n", encoding="utf-8")
        recent_log.write_text("recent\n", encoding="utf-8")
        malformed_log.write_text("unknown\n", encoding="utf-8")

        audit_logger._cleanup_old_logs()

        assert not old_log.exists()
        assert recent_log.read_text(encoding="utf-8") == "recent\n"
        assert malformed_log.read_text(encoding="utf-8") == "unknown\n"


class TestSecurityViolations:
    def test_violation_counts_increment_and_third_logs_warning(
        self,
        tmp_path,
        caplog,
    ):
        audit_logger = AuditLogger(log_dir=str(tmp_path))

        with caplog.at_level(logging.WARNING):
            for attempt in range(3):
                audit_logger._handle_security_violation(
                    user_id="alice@example.com",
                    violation_type="unauthorized_access",
                    severity="HIGH",
                    details={"attempt": attempt + 1},
                )

        key = "alice@example.com:unauthorized_access"
        assert audit_logger._violation_counts[key] == 3
        assert caplog.text.count("Security violation threshold reached") == 1
        assert "count: 3, severity: HIGH" in caplog.text

        lines = audit_logger.log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        events = [json.loads(line) for line in lines]
        assert all(event["violation"]["type"] == "unauthorized_access" for event in events)
        assert events[-1]["violation"]["details"] == {"attempt": 3}

    def test_critical_violation_warns_on_first_occurrence(
        self,
        tmp_path,
        caplog,
    ):
        audit_logger = AuditLogger(log_dir=str(tmp_path))

        with caplog.at_level(logging.WARNING):
            audit_logger._handle_security_violation(
                user_id="bob@example.com",
                violation_type="secret_exposure",
                severity="CRITICAL",
                details={"source": "request"},
            )

        assert audit_logger._violation_counts["bob@example.com:secret_exposure"] == 1
        assert "Security violation threshold reached" in caplog.text
        assert "count: 1, severity: CRITICAL" in caplog.text
        event = json.loads(audit_logger.log_path.read_text(encoding="utf-8").strip())
        assert event["user_id"] == "bob@example.com"
        assert event["violation"]["severity"] == "CRITICAL"
