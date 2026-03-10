"""Adapter mixin for SDK tool integration.

Provides ``SDKToolsMixin`` that existing agents can mix in to optionally
use Agent SDK-style tools (Read, Bash, Glob) instead of
``subprocess.run()`` for file operations.

When the SDK is not installed the mixin methods fall back to the
standard-library equivalents.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .sdk_models import SDK_AVAILABLE

logger = logging.getLogger(__name__)


class SDKToolsMixin:
    """Mixin that provides SDK tool wrappers for existing agents.

    Usage::

        class MyAgent(ReleaseAgent, SDKToolsMixin):
            def _execute_tier(self, codebase_path, tier):
                content = self._sdk_read_file("src/main.py")
                files = self._sdk_glob("src/**/*.py")
                rc, out, err = self._sdk_bash(["pytest", "-v"])
                ...

    When the Agent SDK is available the mixin delegates to the SDK's
    native file-system tools.  Otherwise it falls back to built-in
    Python (``Path.read_text``, ``Path.glob``, ``subprocess.run``).
    """

    def _sdk_read_file(self, file_path: str) -> str:
        """Read a file using SDK tools or stdlib fallback.

        Args:
            file_path: Path to the file to read.

        Returns:
            File contents as a string, or empty string on failure.

        """
        if SDK_AVAILABLE:
            try:
                import claude_agent_sdk  # type: ignore[import-untyped]

                result = claude_agent_sdk.tools.read(file_path)
                return str(result)
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Fall back to stdlib on any SDK error
                logger.debug(f"SDK read failed, using fallback: {e}")

        try:
            return Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return ""

    def _sdk_glob(self, pattern: str, root: str = ".") -> list[str]:
        """Find files using SDK tools or stdlib fallback.

        Args:
            pattern: Glob pattern (e.g. ``src/**/*.py``).
            root: Root directory to search from.

        Returns:
            List of matching file paths as strings.

        """
        if SDK_AVAILABLE:
            try:
                import claude_agent_sdk  # type: ignore[import-untyped]

                result = claude_agent_sdk.tools.glob(pattern, path=root)
                if isinstance(result, list):
                    return [str(p) for p in result]
                return [str(result)]
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Fall back to stdlib on any SDK error
                logger.debug(f"SDK glob failed, using fallback: {e}")

        try:
            matches = sorted(Path(root).glob(pattern))
            return [str(p) for p in matches]
        except (OSError, ValueError) as e:
            logger.warning(f"Glob failed for {pattern}: {e}")
            return []

    def _sdk_bash(self, cmd: list[str], cwd: str = ".", timeout: int = 120) -> tuple[int, str, str]:
        """Run a command using SDK tools or subprocess fallback.

        Args:
            cmd: Command and arguments.
            cwd: Working directory.
            timeout: Timeout in seconds.

        Returns:
            Tuple of (return_code, stdout, stderr).

        """
        if SDK_AVAILABLE:
            try:
                import claude_agent_sdk  # type: ignore[import-untyped]

                result = claude_agent_sdk.tools.bash(
                    " ".join(cmd),
                    cwd=cwd,
                    timeout=timeout * 1000,
                )
                return 0, str(result), ""
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Fall back to subprocess on any SDK error
                logger.debug(f"SDK bash failed, using fallback: {e}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return -1, "", f"Command not found: {cmd[0]}"
        except subprocess.TimeoutExpired:
            return -2, "", f"Command timed out: {' '.join(cmd)}"
