"""Dependency Check Audit Helpers.

Module-level functions for running pip-audit and npm audit,
plus advisory caching for offline mode.
Extracted from dependency_check.py for maintainability.

Functions:
    _get_cache_path: Get advisory cache file path
    _load_cached_advisories: Load cached advisories for offline mode
    _save_advisory_cache: Persist advisories to cache
    _run_pip_audit: Run pip-audit for Python vulnerabilities
    _run_npm_audit: Run npm audit for Node.js vulnerabilities

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import subprocess
import time
from pathlib import Path

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# Cache directory for offline advisory data
CACHE_DIR = Path.home() / ".attune" / "advisory_cache"


def _get_cache_path() -> Path:
    """Get path to advisory cache file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "pip_audit_cache.json"


def _load_cached_advisories() -> dict[str, list[dict]]:
    """Load cached advisories for offline mode.

    Returns:
        Dict mapping package names to list of vulnerability dicts.

    """
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return {}

    try:
        age_days = (time.time() - cache_path.stat().st_mtime) / 86400
        if age_days > 7:
            logger.warning("Advisory cache is %.0f days old - consider updating", age_days)

        return json.loads(cache_path.read_text())
    except Exception as e:
        logger.warning("Could not load advisory cache: %s", e)
        return {}


def _save_advisory_cache(advisories: dict[str, list[dict]]) -> None:
    """Save advisories to cache for offline use."""
    try:
        cache_path = _get_cache_path()
        validated_path = _validate_file_path(str(cache_path))
        validated_path.write_text(json.dumps(advisories, indent=2))
        logger.info("Advisory cache updated: %s packages", len(advisories))
    except Exception as e:
        logger.warning("Could not save advisory cache: %s", e)


def _run_pip_audit(target_path: Path) -> list[dict]:
    """Run pip-audit for real vulnerability data.

    Args:
        target_path: Directory containing requirements files

    Returns:
        List of vulnerability dicts from pip-audit

    """
    # Check for requirements file
    req_file = target_path / "requirements.txt"
    if not req_file.exists():
        # Try pyproject.toml
        pyproject = target_path / "pyproject.toml"
        if pyproject.exists():
            req_file = pyproject
        else:
            logger.info("No requirements.txt or pyproject.toml found for pip-audit")
            return []

    try:
        cmd = [
            "pip-audit",
            "--format=json",
            "--desc=on",
            "-r" if req_file.suffix == ".txt" else "--requirement",
            str(req_file),
        ]

        # For pyproject.toml, pip-audit needs different handling
        if req_file.suffix == ".toml":
            cmd = ["pip-audit", "--format=json", "--desc=on", "--local"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=target_path,
        )

        if result.stdout:
            data = json.loads(result.stdout)
            vulnerabilities = data.get("dependencies", [])

            # Update cache with results
            cache_update = {}
            for vuln in vulnerabilities:
                pkg_name = vuln.get("name", "").lower()
                if pkg_name and vuln.get("vulns"):
                    cache_update[pkg_name] = vuln.get("vulns", [])
            if cache_update:
                existing = _load_cached_advisories()
                existing.update(cache_update)
                _save_advisory_cache(existing)

            return vulnerabilities

    except FileNotFoundError:
        logger.warning(
            "pip-audit not installed. Install with: pip install pip-audit. "
            "Falling back to cached advisories.",
        )
    except subprocess.TimeoutExpired:
        logger.warning("pip-audit timed out after 120s")
    except json.JSONDecodeError as e:
        logger.warning("pip-audit returned invalid JSON: %s", e)
    except Exception as e:
        logger.warning("pip-audit failed: %s", e)

    return []


def _run_npm_audit(target_path: Path) -> list[dict]:
    """Run npm audit for Node.js vulnerability data.

    Args:
        target_path: Directory containing package.json

    Returns:
        List of vulnerability dicts from npm audit

    """
    package_json = target_path / "package.json"
    if not package_json.exists():
        return []

    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=target_path,
        )

        # npm audit returns non-zero if vulnerabilities found
        if result.stdout:
            data = json.loads(result.stdout)
            vulnerabilities = []

            # Parse npm audit format
            for vuln_id, vuln_data in data.get("vulnerabilities", {}).items():
                vulnerabilities.append(
                    {
                        "name": vuln_data.get("name", vuln_id),
                        "severity": vuln_data.get("severity", "unknown"),
                        "via": vuln_data.get("via", []),
                        "range": vuln_data.get("range", ""),
                        "fixAvailable": vuln_data.get("fixAvailable", False),
                    },
                )

            return vulnerabilities

    except FileNotFoundError:
        logger.debug("npm not installed, skipping npm audit")
    except subprocess.TimeoutExpired:
        logger.warning("npm audit timed out")
    except Exception as e:
        logger.warning("npm audit failed: %s", e)

    return []
