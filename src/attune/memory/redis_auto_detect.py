"""Redis auto-detection and install prompting for Attune AI.

Detects whether Redis is available (Python package + running server),
offers platform-specific installation when missing, and persists
user preferences to avoid repeated prompts.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# Platform detection (reuse redis_bootstrap constants when imported there)
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Module-level cache for fast repeated calls within a process
_cached_result: "RedisDetectionResult | None" = None
_cached_at: float = 0.0
_CACHE_TTL: float = 30.0  # seconds


@dataclass
class RedisDetectionResult:
    """Result of Redis auto-detection."""

    available: bool
    has_python_package: bool
    server_reachable: bool
    reason: str


class RedisAutoDetector:
    """Auto-detect Redis availability and manage user preferences.

    Detection flow:
    1. Check module-level cache (30s TTL)
    2. Check if redis Python package is importable
    3. Check if Redis server is reachable (fast ping)
    4. If not reachable, try auto-start via ensure_redis()
    5. If auto-start fails and interactive, prompt to install
    6. Remember user's choice in ~/.attune/config.yml

    Example:
        detector = RedisAutoDetector()
        result = detector.detect()
        if result.available:
            print("Redis ready")

    """

    def __init__(self, config_path: Path | None = None):
        """Initialize Redis auto-detector.

        Args:
            config_path: Path to config file (default: ~/.attune/config.yml).

        """
        self.config_path = config_path or Path.home() / ".attune" / "config.yml"
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load user configuration.

        Returns:
            Configuration dictionary.

        """
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError) as e:
            logger.warning(f"Failed to load config: {e}")
            return {}

    def _save_config(self) -> None:
        """Save configuration to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            validated_path = _validate_file_path(str(self.config_path))
            with open(validated_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
        except (yaml.YAMLError, OSError, ValueError) as e:
            logger.error(f"Failed to save config: {e}")

    def detect(self) -> RedisDetectionResult:
        """Detect Redis availability with caching.

        Returns:
            RedisDetectionResult with availability info.

        """
        global _cached_result, _cached_at

        # Return cached result if fresh
        now = time.monotonic()
        if _cached_result is not None and (now - _cached_at) < _CACHE_TTL:
            return _cached_result

        has_package = self._check_python_package()
        if not has_package:
            result = RedisDetectionResult(
                available=False,
                has_python_package=False,
                server_reachable=False,
                reason="redis Python package not installed",
            )
            _cached_result = result
            _cached_at = now
            return result

        server_up = self._check_server_reachable()
        if server_up:
            result = RedisDetectionResult(
                available=True,
                has_python_package=True,
                server_reachable=True,
                reason="Redis server is running",
            )
            _cached_result = result
            _cached_at = now
            return result

        # Server not reachable — don't cache this so
        # ensure_redis() retries can update the result
        return RedisDetectionResult(
            available=False,
            has_python_package=True,
            server_reachable=False,
            reason="Redis server not reachable",
        )

    def _check_python_package(self) -> bool:
        """Check if the redis Python package is importable.

        Returns:
            True if redis package is available.

        """
        try:
            import redis  # noqa: F401

            return True
        except ImportError:
            return False

    def _check_server_reachable(self, host: str = "127.0.0.1", port: int = 6379) -> bool:
        """Check if Redis server responds to ping.

        Uses a short timeout to avoid slowing down CLI startup.

        Args:
            host: Redis host.
            port: Redis port.

        Returns:
            True if Redis server responds to ping.

        """
        try:
            import redis

            client = redis.Redis(host=host, port=port, socket_connect_timeout=0.5)
            return bool(client.ping())
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Any failure means server is not reachable
            return False

    def should_prompt(self) -> bool:
        """Check whether to prompt the user to install Redis.

        Returns:
            True if we should prompt, False otherwise.

        """
        # Never prompt in non-interactive contexts
        if not sys.stdin.isatty():
            return False

        redis_config = self.config.get("redis", {})

        # Never prompt if user permanently declined
        if redis_config.get("install_declined", False):
            return False

        return True

    def prompt_install(self) -> bool:
        """Prompt the user to install Redis with platform-aware instructions.

        Returns:
            True if install succeeded and Redis is now available.

        """
        result = self.detect()

        if not result.has_python_package:
            return self._prompt_python_package()

        if not result.server_reachable:
            return self._prompt_server_install()

        return True  # Already available

    def _prompt_python_package(self) -> bool:
        """Prompt to install the redis Python package.

        Returns:
            True if installation succeeded.

        """
        print()
        print("=" * 60)
        print("  Redis Python Package Required")
        print("=" * 60)
        print()
        print("  Redis enables multi-agent coordination and")
        print("  persistent session memory in Attune AI.")
        print()
        print("  Install now?")
        print("    pip install --force-reinstall 'redis>=5.0.0,<9.0.0'")
        print()

        try:
            response = input("  [Y]es, install  |  [s]kip  |  [d]on't ask again: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Skipping.")
            response = "s"

        if response in ("d", "dont", "don't"):
            self._save_preference("install_declined", True)
            print("  Won't ask again. Enable later with:")
            print("    pip install --force-reinstall 'redis>=5.0.0,<9.0.0'")
            print("=" * 60)
            print()
            return False

        if response in ("s", "skip", "n", "no"):
            print("  Skipped. Using in-memory storage for now.")
            print("=" * 60)
            print()
            return False

        # Install the package. Target `redis` directly, NOT
        # `attune-ai[redis]` — that extra is an empty back-compat alias
        # (redis ships as a core dep), so installing it is a no-op that
        # exits 0 and would make the success message below a lie.
        print()
        print("  Installing redis package...")
        try:
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--force-reinstall",
                    # Same spec as pyproject's core dep — an unpinned
                    # install could pull a redis major that violates it.
                    "redis>=5.0.0,<9.0.0",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Installation failed: {e}")
            print("  Install manually: pip install --force-reinstall 'redis>=5.0.0,<9.0.0'")
            print("=" * 60)
            print()
            logger.error(f"Failed to install redis package: {e}")
            return False

        # pip exiting 0 is not proof the import works — verify before
        # claiming success, or a no-op install reports "✓ installed"
        # and sends the user off to debug their server instead.
        import importlib

        # The import finder caches directory listings; without this a
        # just-installed package can still look missing.
        importlib.invalidate_caches()
        self._invalidate_cache()
        if not self._check_python_package():
            print("  ✗ pip reported success but redis is still not importable.")
            print("    The install command was already retried, so don't re-run it —")
            print("    this points at the environment itself. Diagnose with:")
            print("      python -m pip check")
            print("      python -c 'import redis'   (read the actual ImportError)")
            print("    or rebuild the env: pip install --force-reinstall attune-ai")
            print("=" * 60)
            print()
            logger.error("redis still not importable after a successful pip install")
            return False

        print("  ✓ redis package installed")
        print("=" * 60)
        print()
        # Now check if server is also available
        if self._check_server_reachable():
            return True
        # Package installed but server not running — prompt for server
        return self._prompt_server_install()

    def _prompt_server_install(self) -> bool:
        """Prompt to install and start the Redis server.

        Returns:
            True if Redis server is now running.

        """
        install_cmd = self._get_install_command()

        print()
        print("=" * 60)
        print("  Redis Recommended")
        print("=" * 60)
        print()
        print("  Redis enables multi-agent coordination, session")
        print("  memory, and real-time cross-agent communication.")
        print()
        print("  Without Redis, Attune uses in-memory storage (basic).")
        print()
        print("  Install Redis now?")
        print(f"    {install_cmd}")
        print()

        try:
            response = input("  [Y]es, install  |  [s]kip  |  [d]on't ask again: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Skipping.")
            response = "s"

        if response in ("d", "dont", "don't"):
            self._save_preference("install_declined", True)
            print("  Won't ask again. Install later with:")
            print(f"    {install_cmd}")
            print("=" * 60)
            print()
            return False

        if response in ("s", "skip", "n", "no"):
            print("  Skipped. Using in-memory storage for now.")
            print("=" * 60)
            print()
            return False

        # Run the install
        return self._run_server_install(install_cmd)

    def _get_install_command(self) -> str:
        """Get the platform-appropriate Redis install command.

        Returns:
            Install command string for the current platform.

        """
        if IS_MACOS:
            return "brew install redis && brew services start redis"
        if IS_LINUX:
            if shutil.which("apt"):
                return "sudo apt install -y redis-server"
            if shutil.which("yum"):
                return "sudo yum install -y redis"
            return "sudo apt install -y redis-server"
        return "docker run -d -p 6379:6379 --name attune-redis redis:alpine"

    def _run_server_install(self, install_cmd: str) -> bool:
        """Execute the Redis server installation command.

        Args:
            install_cmd: The install command to run.

        Returns:
            True if install succeeded and Redis is now running.

        """
        print()
        print(f"  Running: {install_cmd}")
        print()

        try:
            # Run install commands sequentially
            # Commands may be compound (e.g., "brew install redis && brew services start redis")
            for cmd_part in install_cmd.split("&&"):
                cmd_args = cmd_part.strip().split()
                subprocess.check_call(  # noqa: S603
                    cmd_args,
                    timeout=120,
                )

            # Give Redis a moment to start
            time.sleep(1)

            if self._check_server_reachable():
                print("  ✓ Redis installed and running")
                self._save_preference("installed", True)
                self._save_preference("install_method", install_cmd.split(maxsplit=1)[0])
                self._invalidate_cache()
                print("=" * 60)
                print()
                return True
            print("  ✗ Redis installed but not responding")
            print("  Try starting manually: redis-server")
            print("=" * 60)
            print()
            return False

        except subprocess.CalledProcessError as e:
            print(f"  ✗ Installation failed: {e}")
            print(f"  Try manually: {install_cmd}")
            print("=" * 60)
            print()
            logger.error(f"Redis server install failed: {e}")
            return False
        except subprocess.TimeoutExpired:
            print("  ✗ Installation timed out")
            print(f"  Try manually: {install_cmd}")
            print("=" * 60)
            print()
            return False

    def _save_preference(self, key: str, value: object) -> None:
        """Save a Redis preference to config.

        Args:
            key: Preference key.
            value: Preference value.

        """
        if "redis" not in self.config:
            self.config["redis"] = {}
        self.config["redis"][key] = value
        self._save_config()

    def _invalidate_cache(self) -> None:
        """Invalidate the module-level detection cache."""
        global _cached_result, _cached_at
        _cached_result = None
        _cached_at = 0.0


def auto_detect_redis() -> RedisDetectionResult:
    """Convenience function for auto-detecting Redis.

    Returns:
        RedisDetectionResult with availability info.

    """
    detector = RedisAutoDetector()
    result = detector.detect()

    # If not available and we should prompt, do so
    if not result.available and detector.should_prompt():
        if detector.prompt_install():
            return detector.detect()

    return result
