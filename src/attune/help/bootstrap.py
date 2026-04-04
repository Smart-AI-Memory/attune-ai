"""Project scanning and manifest bootstrapping.

Scans a project's directory structure to discover features
and propose an initial features.yaml manifest. Used by the
/coach init flow.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from attune.help.manifest import _MANIFEST_VERSION, Feature, FeatureManifest

logger = logging.getLogger(__name__)

# Directories to always skip during discovery
_SKIP_DIRS = {
    ".git",
    ".github",
    ".help",
    ".claude",
    ".agents",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".egg-info",
    "htmlcov",
    "site",
}

# File patterns that suggest entry points
_ENTRY_POINT_NAMES = {
    "main.py",
    "app.py",
    "cli.py",
    "server.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "index.ts",
    "index.js",
    "main.go",
    "main.rs",
}

# Config file patterns suggesting configurable subsystems
_CONFIG_PATTERNS = {
    "config",
    "settings",
    "conf",
}


@dataclass
class ProposedFeature:
    """A feature discovered by scanning.

    Attributes:
        name: Suggested feature name.
        description: Generated description.
        files: Glob patterns for source files.
        tags: Suggested tags.
        confidence: How confident the heuristic is (high/medium/low).
        reason: Why this was proposed.
    """

    name: str
    description: str
    files: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    confidence: str = "medium"
    reason: str = ""


def scan_project(project_root: str | Path) -> list[ProposedFeature]:
    """Scan a project and propose features.

    Uses heuristics to identify features from:
    - Top-level source directories
    - Entry points (CLI, API, main files)
    - Config files (suggesting subsystems)
    - Test directories (mirroring feature structure)
    - README sections

    Args:
        project_root: Root directory of the project.

    Returns:
        List of proposed features, sorted by confidence.
    """
    root = Path(project_root).resolve()
    proposals: list[ProposedFeature] = []
    seen_names: set[str] = set()

    # Find the source root (src/pkg/, lib/, or project root)
    src_root = _find_source_root(root)

    # 1. Discover from top-level source directories
    proposals.extend(_discover_from_directories(src_root, root, seen_names))

    # 2. Discover from entry points
    proposals.extend(_discover_from_entry_points(root, seen_names))

    # 3. Discover from config files
    proposals.extend(_discover_from_config(root, seen_names))

    # Sort: high confidence first, then alphabetical
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    proposals.sort(key=lambda p: (confidence_order.get(p.confidence, 2), p.name))

    return proposals


def proposals_to_manifest(
    proposals: list[ProposedFeature],
) -> FeatureManifest:
    """Convert accepted proposals to a FeatureManifest.

    Args:
        proposals: List of accepted feature proposals.

    Returns:
        A FeatureManifest ready to save.
    """
    features: dict[str, Feature] = {}
    for p in proposals:
        features[p.name] = Feature(
            name=p.name,
            description=p.description,
            files=p.files,
            tags=p.tags,
        )
    return FeatureManifest(version=_MANIFEST_VERSION, features=features)


def _find_source_root(project_root: Path) -> Path:
    """Find the primary source directory.

    Looks for common patterns: src/<pkg>/, lib/, app/.
    Falls back to project root if none found.

    Args:
        project_root: Project root directory.

    Returns:
        Path to the source root.
    """
    # src/<package>/ pattern (Python, Rust)
    src_dir = project_root / "src"
    if src_dir.is_dir():
        children = [d for d in src_dir.iterdir() if d.is_dir() and d.name not in _SKIP_DIRS]
        if len(children) == 1:
            return children[0]
        if children:
            return src_dir

    # lib/ pattern (Ruby, Elixir)
    lib_dir = project_root / "lib"
    if lib_dir.is_dir():
        return lib_dir

    # app/ pattern (Rails, Django, Next.js)
    app_dir = project_root / "app"
    if app_dir.is_dir():
        return app_dir

    return project_root


def _discover_from_directories(
    src_root: Path,
    project_root: Path,
    seen: set[str],
) -> list[ProposedFeature]:
    """Discover features from source directory structure.

    Each immediate subdirectory of the source root is a
    candidate feature.

    Args:
        src_root: Source root directory.
        project_root: Project root for relative paths.
        seen: Already-proposed feature names (mutated).

    Returns:
        List of proposed features.
    """
    proposals: list[ProposedFeature] = []

    if not src_root.is_dir():
        return proposals

    for child in sorted(src_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        if child.name in _SKIP_DIRS:
            continue

        name = child.name.replace("_", "-")
        if name in seen:
            continue
        seen.add(name)

        rel = str(child.relative_to(project_root))
        glob_pattern = f"{rel}/**"

        # Count source files to gauge importance
        file_count = sum(1 for _ in child.rglob("*") if _.is_file() and not _.name.startswith("."))

        if file_count == 0:
            continue

        desc = _infer_description(child)

        proposals.append(
            ProposedFeature(
                name=name,
                description=desc,
                files=[glob_pattern],
                tags=_infer_tags(child.name),
                confidence="high" if file_count >= 3 else "medium",
                reason=f"Source directory with {file_count} files",
            )
        )

    return proposals


def _discover_from_entry_points(
    project_root: Path,
    seen: set[str],
) -> list[ProposedFeature]:
    """Discover features from entry point files.

    Args:
        project_root: Project root directory.
        seen: Already-proposed feature names (mutated).

    Returns:
        List of proposed features.
    """
    proposals: list[ProposedFeature] = []

    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in filenames:
            if fname not in _ENTRY_POINT_NAMES:
                continue

            path = Path(dirpath) / fname
            rel = str(path.relative_to(project_root))
            parent_name = path.parent.name

            if parent_name in seen or parent_name in _SKIP_DIRS:
                continue

            name = f"{parent_name}-entry" if parent_name != project_root.name else "main"
            if name in seen:
                continue
            seen.add(name)

            proposals.append(
                ProposedFeature(
                    name=name,
                    description=f"Entry point: {rel}",
                    files=[rel],
                    tags=["entry-point"],
                    confidence="low",
                    reason=f"Entry point file: {fname}",
                )
            )

    return proposals


def _discover_from_config(
    project_root: Path,
    seen: set[str],
) -> list[ProposedFeature]:
    """Discover features from config files.

    Args:
        project_root: Project root directory.
        seen: Already-proposed feature names (mutated).

    Returns:
        List of proposed features.
    """
    proposals: list[ProposedFeature] = []

    for child in sorted(project_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name not in _CONFIG_PATTERNS:
            continue

        name = "configuration"
        if name in seen:
            continue
        seen.add(name)

        rel = str(child.relative_to(project_root))
        proposals.append(
            ProposedFeature(
                name=name,
                description="Project configuration and settings",
                files=[f"{rel}/**"],
                tags=["config", "settings"],
                confidence="medium",
                reason=f"Config directory: {rel}/",
            )
        )

    return proposals


def _infer_description(directory: Path) -> str:
    """Infer a feature description from directory contents.

    Checks for module docstrings in __init__.py or README.

    Args:
        directory: Feature directory to inspect.

    Returns:
        Best-effort description string.
    """
    # Try __init__.py docstring
    init = directory / "__init__.py"
    if init.exists():
        try:
            text = init.read_text(encoding="utf-8")
            # Extract first docstring
            for delim in ('"""', "'''"):
                if delim in text:
                    start = text.index(delim) + 3
                    end = text.index(delim, start)
                    doc = text[start:end].strip()
                    first_line = doc.split("\n")[0].strip()
                    if first_line:
                        return first_line
        except (OSError, ValueError):
            pass

    # Try README
    for readme_name in ("README.md", "README.rst", "README"):
        readme = directory / readme_name
        if readme.exists():
            try:
                first_line = readme.read_text(encoding="utf-8").strip().split("\n")[0]
                return first_line.lstrip("# ").strip()
            except OSError:
                pass

    # Fallback: humanize the directory name
    return directory.name.replace("_", " ").replace("-", " ").title()


def _infer_tags(name: str) -> list[str]:
    """Infer tags from a feature name.

    Args:
        name: Feature or directory name.

    Returns:
        List of inferred tags.
    """
    tag_hints: dict[str, list[str]] = {
        "auth": ["security", "users"],
        "api": ["api", "rest"],
        "cli": ["cli", "commands"],
        "db": ["database"],
        "model": ["data", "models"],
        "test": ["testing"],
        "security": ["security"],
        "config": ["configuration"],
        "webhook": ["integrations"],
        "plugin": ["plugins", "extensions"],
        "workflow": ["workflows"],
        "agent": ["agents", "ai"],
        "memory": ["memory", "storage"],
        "mcp": ["mcp", "tools"],
    }
    tags: list[str] = []
    lower = name.lower()
    for hint, hint_tags in tag_hints.items():
        if hint in lower:
            tags.extend(hint_tags)
    return list(dict.fromkeys(tags))  # dedupe, preserve order
