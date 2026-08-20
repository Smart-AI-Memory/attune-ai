"""Dependency Check Parser Mixin.

Mixin providing dependency file parsing methods for DependencyCheckWorkflow.
Extracted from dependency_check.py for maintainability.

Supports:
- requirements.txt (with packaging library or fallback regex)
- pyproject.toml (PEP 621 + Poetry, with tomllib or fallback)
- package.json (npm dependencies + devDependencies)
- poetry.lock (pinned Python versions)
- package-lock.json (pinned Node.js versions, v6 + v7 formats)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class DependencyParserMixin:
    """Mixin providing dependency file parsing methods.

    Expected attributes on host class:
        (none - parsing methods are self-contained)
    """

    def _parse_requirements(self, path: Path) -> list[dict]:
        """Parse requirements.txt format using packaging library.

        Properly handles:
        - Version specifiers (>=, ==, ~=, etc.)
        - Extras ([dev], [test], etc.)
        - Environment markers (; python_version >= "3.8")
        - Comments and blank lines
        """
        deps = []
        try:
            from packaging.requirements import Requirement
        except ImportError:
            logger.warning("packaging library not installed, using fallback parser")
            return self._parse_requirements_fallback(path)

        try:
            content = path.read_text()
            for line in content.splitlines():
                line = line.strip()

                # Skip empty lines, comments, and options
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Skip URLs and local paths
                if line.startswith("http://") or line.startswith("https://"):
                    continue
                if line.startswith(".") or line.startswith("/"):
                    continue

                try:
                    req = Requirement(line)
                    deps.append(
                        {
                            "name": req.name,
                            "version": str(req.specifier) if req.specifier else "any",
                            "extras": list(req.extras) if req.extras else [],
                            "source": str(path),
                            "ecosystem": "python",
                        },
                    )
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"Skipping unparseable requirement '{line}': {e}")

        except OSError as e:
            logger.warning(f"Cannot read {path}: {e}")

        return deps

    def _parse_requirements_fallback(self, path: Path) -> list[dict]:
        """Fallback parser if packaging library not available."""
        deps = []
        try:
            content = path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Basic regex parsing
                match = re.match(r"^([a-zA-Z0-9_-]+)\s*([<>=!~]+\s*[\d.]+)?", line)
                if match:
                    name = match.group(1)
                    version = match.group(2).strip() if match.group(2) else "any"
                    deps.append(
                        {
                            "name": name,
                            "version": version,
                            "source": str(path),
                            "ecosystem": "python",
                        },
                    )
        except OSError:
            pass
        return deps

    def _parse_pyproject(self, path: Path) -> list[dict]:
        """Parse pyproject.toml for dependencies using tomllib.

        Supports:
        - PEP 621 [project.dependencies]
        - Poetry [tool.poetry.dependencies]
        - Optional dependencies
        """
        deps = []

        # Try tomllib (Python 3.11+) or tomli as fallback
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                logger.warning("tomllib/tomli not available, using fallback parser")
                return self._parse_pyproject_fallback(path)

        try:
            from packaging.requirements import Requirement
        except ImportError:
            Requirement = None  # type: ignore

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)

            # PEP 621: [project.dependencies]
            for dep_str in data.get("project", {}).get("dependencies", []):
                if Requirement:
                    try:
                        req = Requirement(dep_str)
                        deps.append(
                            {
                                "name": req.name,
                                "version": str(req.specifier) if req.specifier else "any",
                                "source": str(path),
                                "ecosystem": "python",
                            },
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.debug(f"Skipping unparseable dependency '{dep_str}': {e}")
                else:
                    # Basic extraction without packaging
                    match = re.match(r"^([a-zA-Z0-9_-]+)", dep_str)
                    if match:
                        deps.append(
                            {
                                "name": match.group(1),
                                "version": "any",
                                "source": str(path),
                                "ecosystem": "python",
                            },
                        )

            # Poetry: [tool.poetry.dependencies]
            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            for name, spec in poetry_deps.items():
                if name == "python":
                    continue  # Skip Python version constraint

                if isinstance(spec, str):
                    version = spec
                elif isinstance(spec, dict):
                    version = spec.get("version", "any")
                else:
                    version = "any"

                deps.append(
                    {
                        "name": name,
                        "version": version,
                        "source": str(path),
                        "ecosystem": "python",
                    },
                )

            # Poetry dev dependencies
            poetry_dev = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
            for name, spec in poetry_dev.items():
                version = spec if isinstance(spec, str) else spec.get("version", "any")
                deps.append(
                    {
                        "name": name,
                        "version": version,
                        "source": str(path),
                        "ecosystem": "python",
                        "dev": True,
                    },
                )

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Cannot parse {path}: {e}")

        return deps

    def _parse_pyproject_fallback(self, path: Path) -> list[dict]:
        """Fallback parser if tomllib not available."""
        deps = []
        try:
            content = path.read_text()
            in_deps = False
            for line in content.splitlines():
                if "dependencies" in line and "=" in line:
                    in_deps = True
                    continue
                if in_deps:
                    if line.strip().startswith("]"):
                        in_deps = False
                        continue
                    match = re.search(r'"([a-zA-Z0-9_-]+)([<>=!~]+[\d.]+)?"', line)
                    if match:
                        name = match.group(1)
                        version = match.group(2) if match.group(2) else "any"
                        deps.append(
                            {
                                "name": name,
                                "version": version,
                                "source": str(path),
                                "ecosystem": "python",
                            },
                        )
        except OSError:
            pass
        return deps

    def _parse_package_json(self, path: Path) -> list[dict]:
        """Parse package.json for dependencies."""
        deps = []
        try:
            with open(path) as f:
                data = json.load(f)

            # An npm manifest that is not an object reaches data.get()
            # below and raises AttributeError past this method's
            # (OSError, JSONDecodeError) handler (library-review C3).
            if not isinstance(data, dict):
                return deps

            for dep_type in ["dependencies", "devDependencies"]:
                for name, version in data.get(dep_type, {}).items():
                    deps.append(
                        {
                            "name": name,
                            "version": version,
                            "source": str(path),
                            "ecosystem": "node",
                            "dev": dep_type == "devDependencies",
                        },
                    )
        except (OSError, json.JSONDecodeError):
            pass
        return deps

    def _parse_poetry_lock(self, path: Path) -> list[dict]:
        """Parse poetry.lock for pinned dependency versions.

        Lockfiles provide exact versions for reproducible vulnerability findings.
        """
        deps = []

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                logger.debug("tomllib/tomli not available for poetry.lock parsing")
                return deps

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)

            for pkg in data.get("package", []):
                deps.append(
                    {
                        "name": pkg.get("name", ""),
                        "version": f"=={pkg.get('version', '')}",  # Pinned version
                        "source": str(path),
                        "ecosystem": "python",
                        "pinned": True,
                    },
                )

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Cannot parse poetry.lock: {e}")

        return deps

    def _parse_package_lock_json(self, path: Path) -> list[dict]:
        """Parse package-lock.json for pinned Node.js versions."""
        deps = []
        try:
            with open(path) as f:
                data = json.load(f)

            # Same guard as _parse_package_json: a non-object lock file
            # would escape the handler below (library-review C3).
            if not isinstance(data, dict):
                return deps

            # npm v7+ format (packages)
            packages = data.get("packages", {})
            for pkg_path, pkg_data in packages.items():
                if not pkg_path or pkg_path == "":  # Root package
                    continue

                name = pkg_path.replace("node_modules/", "").split("/")[-1]
                version = pkg_data.get("version", "")
                if name and version:
                    deps.append(
                        {
                            "name": name,
                            "version": f"=={version}",
                            "source": str(path),
                            "ecosystem": "node",
                            "pinned": True,
                        },
                    )

            # npm v6 format (dependencies)
            if not packages:
                for name, pkg_data in data.get("dependencies", {}).items():
                    version = pkg_data.get("version", "")
                    deps.append(
                        {
                            "name": name,
                            "version": f"=={version}",
                            "source": str(path),
                            "ecosystem": "node",
                            "pinned": True,
                        },
                    )

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Cannot parse package-lock.json: {e}")

        return deps
