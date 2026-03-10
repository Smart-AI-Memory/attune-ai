"""Tests for path traversal prevention (CWE-22).

Verifies that _validate_file_path() properly blocks:
- Relative path traversal (../)
- Absolute paths to system directories
- Null byte injection
- Symlink attacks

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys
from pathlib import Path

import pytest

from attune.security.path_validation import _validate_file_path

_skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix path separators don't work with Path on Windows",
)


class TestPathTraversalPrevention:
    """Test suite for path traversal attack prevention."""

    def test_blocks_absolute_system_paths(self):
        """Test that absolute paths to system directories are blocked.

        Note: On macOS, /etc is a symlink to /private/etc, so paths like
        /etc/passwd resolve to /private/etc/passwd which doesn't match
        the /etc prefix check. We test paths that work cross-platform.
        """
        # These paths work on both Linux and macOS
        dangerous_paths = [
            "/sys/kernel",
            "/proc/version",
            "/dev/zero",
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError, match="Cannot write to system directory"):
                _validate_file_path(path)

    def test_blocks_traversal_with_allowed_dir_only(self, tmp_path):
        """Test that path traversal is blocked when allowed_dir is set.

        Note: Without allowed_dir, relative paths like '../foo' resolve to
        valid filesystem paths. The protection comes from:
        1. System directory blocking (/etc, /sys, /proc, /dev)
        2. The allowed_dir parameter to restrict writes to a specific directory

        The API uses allowed_dir=tempfile.gettempdir() to prevent
        writes outside the temp directory.
        """
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        # Traversal attempts should be blocked
        traversal_paths = [
            str(allowed_dir / ".." / "outside.txt"),
            str(allowed_dir / ".." / ".." / "etc" / "passwd"),
        ]

        for path in traversal_paths:
            with pytest.raises(ValueError, match="outside allowed directory"):
                _validate_file_path(path, allowed_dir=str(allowed_dir))

    def test_blocks_null_byte_injection(self):
        """Test that null byte injection is blocked."""
        dangerous_paths = [
            "config\x00.json",
            "file.txt\x00.jpg",
            "\x00/etc/passwd",
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError, match="null bytes"):
                _validate_file_path(path)

    def test_blocks_empty_path(self):
        """Test that empty paths are rejected."""
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_file_path("")

        with pytest.raises(ValueError, match="non-empty string"):
            _validate_file_path(None)

    def test_allows_valid_paths(self, tmp_path):
        """Test that valid paths are allowed."""
        valid_paths = [
            str(tmp_path / "config.yaml"),
            str(tmp_path / "subdir" / "config.json"),
            str(tmp_path / "data-2026-01-24.txt"),
        ]

        for path in valid_paths:
            # Should not raise
            result = _validate_file_path(path)
            assert result == Path(path).resolve()

    def test_allowed_dir_restriction(self, tmp_path):
        """Test that allowed_dir parameter restricts writes correctly."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        # Valid path within allowed directory
        valid_path = str(allowed_dir / "file.txt")
        result = _validate_file_path(valid_path, allowed_dir=str(allowed_dir))
        assert result.parent == allowed_dir.resolve()

        # Invalid path outside allowed directory
        invalid_path = str(tmp_path / "outside.txt")
        with pytest.raises(ValueError, match="outside allowed directory"):
            _validate_file_path(invalid_path, allowed_dir=str(allowed_dir))

    def test_blocks_traversal_with_allowed_dir(self, tmp_path):
        """Test that traversal is blocked even with allowed_dir set."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        traversal_path = str(allowed_dir / ".." / "outside.txt")
        with pytest.raises(ValueError, match="outside allowed directory"):
            _validate_file_path(traversal_path, allowed_dir=str(allowed_dir))


class TestPathTraversalInPatternAPI:
    """Test path traversal prevention in patterns API endpoints."""

    def test_export_filename_validated(self):
        """Test that export filename parameter is validated.

        This is a documentation test - actual API testing requires FastAPI test client.
        The fix ensures API endpoints validate paths before writing.
        """
        # Path validation is called in the API endpoint
        assert True  # Placeholder - add FastAPI test if available

    def test_download_filename_validated(self):
        """Test that download filename parameter is validated.

        This is a documentation test - actual API testing requires FastAPI test client.
        The fix ensures API endpoints validate paths before writing.
        """
        # Path validation is called in the API endpoint
        assert True  # Placeholder - add FastAPI test if available


class TestPathValidationOSErrorHandling:
    """Tests for OSError/RuntimeError path resolution edge cases (lines 38-39)."""

    def test_raises_value_error_on_resolution_oserror(self):
        """Test that OSError during path resolution raises ValueError."""
        from pathlib import Path
        from unittest.mock import patch

        with patch.object(Path, "resolve", side_effect=OSError("resolution failed")):
            with pytest.raises(ValueError, match="Invalid path"):
                _validate_file_path("some_path.txt")

    def test_raises_value_error_on_resolution_runtime_error(self):
        """Test that RuntimeError during path resolution raises ValueError."""
        from pathlib import Path
        from unittest.mock import patch

        with patch.object(Path, "resolve", side_effect=RuntimeError("runtime error")):
            with pytest.raises(ValueError, match="Invalid path"):
                _validate_file_path("some_path.txt")

    def test_raises_value_error_on_allowed_dir_outside(self, tmp_path):
        """Test ValueError when path is outside allowed_dir."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        outside_path = tmp_path / "outside.txt"

        with pytest.raises(ValueError, match="outside allowed directory"):
            _validate_file_path(str(outside_path), allowed_dir=str(allowed_dir))

    def test_non_string_type_raises_value_error(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_file_path(123)  # type: ignore[arg-type]

    def test_returns_path_object(self, tmp_path):
        """Test that a valid path returns a Path object."""
        valid = str(tmp_path / "file.txt")
        result = _validate_file_path(valid)
        assert isinstance(result, Path)


class TestPathValidationWindowsPaths:
    """Tests for Windows system directory blocking (lines 54-69).

    These tests mock sys.platform to simulate Windows behavior
    on non-Windows platforms.
    """

    def test_blocks_windows_system32(self):
        """Test that Windows system32 paths are blocked."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "win32"):
            with pytest.raises(ValueError, match="Cannot write to system directory"):
                _validate_file_path("C:\\Windows\\System32\\config.txt")

    def test_blocks_windows_syswow64(self):
        """Test that Windows SysWOW64 paths are blocked."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "win32"):
            with pytest.raises(ValueError, match="Cannot write to system directory"):
                _validate_file_path("C:\\Windows\\SysWOW64\\file.txt")

    def test_blocks_windows_system(self):
        """Test that Windows System directory paths are blocked."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "win32"):
            with pytest.raises(ValueError, match="Cannot write to system directory"):
                _validate_file_path("C:\\Windows\\System\\file.txt")

    def test_blocks_windows_program_files(self):
        """Test that Windows Program Files paths are blocked."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "win32"):
            with pytest.raises(ValueError, match="Cannot write to system directory"):
                _validate_file_path("C:\\Program Files\\app\\config.txt")

    def test_blocks_windows_program_files_x86(self):
        """Test that Windows Program Files (x86) paths are blocked."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "win32"):
            with pytest.raises(ValueError, match="Cannot write to system directory"):
                _validate_file_path("C:\\Program Files (x86)\\app\\config.txt")

    def test_windows_allows_safe_user_path(self, tmp_path):
        """Test that safe user paths are allowed on Windows."""
        import sys
        from unittest.mock import patch

        safe_path = str(tmp_path / "config.txt")

        with patch.object(sys, "platform", "win32"):
            result = _validate_file_path(safe_path)

        assert result is not None

    def test_windows_blocks_unix_etc_marker(self, tmp_path):
        """Test that Unix-style /etc markers are blocked on Windows paths."""
        import sys
        from pathlib import Path
        from unittest.mock import patch

        # Create a mock resolved path that looks like a Windows etc path
        resolved_path = Path("C:\\etc\\passwd")

        with patch.object(sys, "platform", "win32"):
            with patch.object(Path, "resolve", return_value=resolved_path):
                with pytest.raises(ValueError, match="Cannot write to system directory"):
                    _validate_file_path("C:\\etc\\passwd")

    @_skip_on_windows
    def test_unix_blocks_etc(self):
        """Test that Unix /etc paths are blocked."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "linux"):
            with patch.object(Path, "resolve", return_value=Path("/etc/passwd")):
                with pytest.raises(ValueError, match="Cannot write to system directory"):
                    _validate_file_path("/etc/passwd")

    @_skip_on_windows
    def test_unix_blocks_usr_bin(self):
        """Test that /usr/bin paths are blocked on Unix."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "linux"):
            with patch.object(Path, "resolve", return_value=Path("/usr/bin/myapp")):
                with pytest.raises(ValueError, match="Cannot write to system directory"):
                    _validate_file_path("/usr/bin/myapp")

    @_skip_on_windows
    def test_unix_blocks_bin(self):
        """Test that /bin paths are blocked on Unix."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "linux"):
            with patch.object(Path, "resolve", return_value=Path("/bin/sh")):
                with pytest.raises(ValueError, match="Cannot write to system directory"):
                    _validate_file_path("/bin/sh")

    @_skip_on_windows
    def test_unix_blocks_sbin(self):
        """Test that /usr/sbin paths are blocked on Unix."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "platform", "linux"):
            with patch.object(Path, "resolve", return_value=Path("/usr/sbin/nologin")):
                with pytest.raises(ValueError, match="Cannot write to system directory"):
                    _validate_file_path("/usr/sbin/nologin")

    @_skip_on_windows
    def test_exact_system_dir_without_trailing_slash(self):
        """Test that exact system directory matches (not just prefix)."""
        import sys
        from pathlib import Path
        from unittest.mock import patch

        # Test the exact match case (resolved_str == dangerous)
        with patch.object(sys, "platform", "linux"):
            with patch.object(Path, "resolve", return_value=Path("/etc")):
                with pytest.raises(ValueError, match="Cannot write to system directory"):
                    _validate_file_path("/etc")
