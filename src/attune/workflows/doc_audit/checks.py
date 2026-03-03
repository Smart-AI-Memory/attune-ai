"""Documentation audit check functions.

Each function returns a CheckResult with status "pass", "fail", or "warn".
All checks parse files on disk and do NOT import attune modules directly,
making each independently testable.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    """Result of a single documentation audit check.

    Attributes:
        id: Unique identifier for the check (e.g. "test-count").
        name: Human-readable name.
        status: "pass", "fail", or "warn".
        details: Explanation of what was found.
        file: Path to the relevant file, if applicable.
        line: Line number in the file, if applicable.
        auto_fixable: Whether this check can be fixed automatically.

    """

    id: str
    name: str
    status: str  # "pass" | "fail" | "warn"
    details: str
    file: str | None = None
    line: int | None = None
    auto_fixable: bool = False


def check_test_count(project_root: str = ".") -> CheckResult:
    """Count tests via pytest --collect-only and compare to README badge.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "test-count"
    check_name = "Test count matches README badge"

    # Count tests
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(root),
        )
        output = result.stdout + result.stderr
        # pytest --collect-only -q ends with a summary line like "X tests collected"
        match = re.search(r"(\d+)\s+test[s]?\s+collected", output)
        if not match:
            return CheckResult(
                id=check_id,
                name=check_name,
                status="warn",
                details="Could not parse pytest --collect-only output.",
            )
        actual_count = int(match.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=f"Could not run pytest: {e}",
        )

    # Find README badge count
    readme_path = root / "README.md"
    if not readme_path.exists():
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=f"No README.md found; {actual_count} tests collected.",
        )

    content = readme_path.read_text(encoding="utf-8")
    # Look for badge patterns like "146 tests" or "tests-146-brightgreen"
    badge_match = re.search(
        r"tests[-_]?(\d+)[-_]|(\d+)\s+tests?\b",
        content,
        re.IGNORECASE,
    )
    if not badge_match:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=(
                f"No test count badge found in README.md; " f"{actual_count} tests collected."
            ),
            file=str(readme_path),
        )

    badge_count = int(badge_match.group(1) or badge_match.group(2))
    if badge_count == actual_count:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details=f"{actual_count} tests collected; README badge matches.",
            file=str(readme_path),
            auto_fixable=False,
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=(f"README badge says {badge_count} tests but " f"pytest collected {actual_count}."),
        file=str(readme_path),
        auto_fixable=True,
    )


def check_workflow_count(project_root: str = ".") -> CheckResult:
    """Count workflows in _DEFAULT_WORKFLOW_NAMES and compare to docs.

    Parses src/attune/workflows/__init__.py for the dict literal rather
    than importing the module.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "workflow-count"
    check_name = "Workflow count matches docs"

    workflows_init = root / "src" / "attune" / "workflows" / "__init__.py"
    if not workflows_init.exists():
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="src/attune/workflows/__init__.py not found.",
        )

    content = workflows_init.read_text(encoding="utf-8")
    # Extract entries from _DEFAULT_WORKFLOW_NAMES dict
    block_match = re.search(
        r"_DEFAULT_WORKFLOW_NAMES\s*:\s*dict[^=]*=\s*\{(.*?)\}",
        content,
        re.DOTALL,
    )
    if not block_match:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="_DEFAULT_WORKFLOW_NAMES not found in workflows/__init__.py.",
            file=str(workflows_init),
        )

    block = block_match.group(1)
    # Count non-comment string keys: lines like "code-review": ...
    keys = re.findall(r'^\s*"([^"]+)"\s*:', block, re.MULTILINE)
    actual_count = len(keys)

    # Check README.md or docs for a claimed workflow count
    readme_path = root / "README.md"
    claimed = _find_numeric_claim(readme_path, r"(\d+)\s+workflow[s]?")
    if claimed is None:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=(f"{actual_count} workflows registered; " "no count found in README.md."),
            file=str(workflows_init),
        )

    if claimed == actual_count:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details=f"{actual_count} workflows registered; README matches.",
            file=str(readme_path),
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=(f"README claims {claimed} workflows but " f"{actual_count} are registered."),
        file=str(readme_path),
        auto_fixable=True,
    )


def check_skill_count(project_root: str = ".") -> CheckResult:
    """Count .md files in .claude/commands/ and compare to docs.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "skill-count"
    check_name = "Skill count matches docs"

    commands_dir = root / ".claude" / "commands"
    if not commands_dir.exists():
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=".claude/commands/ directory not found.",
        )

    skill_files = list(commands_dir.glob("*.md"))
    actual_count = len(skill_files)

    readme_path = root / "README.md"
    claimed = _find_numeric_claim(readme_path, r"(\d+)\s+(?:skill|command)[s]?")
    if claimed is None:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=(f"{actual_count} skill files found; " "no count claim found in README.md."),
            file=str(commands_dir),
        )

    if claimed == actual_count:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details=f"{actual_count} skills found; README matches.",
            file=str(readme_path),
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=(
            f"README claims {claimed} skills but "
            f"{actual_count} .md files found in .claude/commands/."
        ),
        file=str(readme_path),
        auto_fixable=True,
    )


def check_mcp_tool_count(project_root: str = ".") -> CheckResult:
    """Count @server.tool() decorators in src/ and compare to docs.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "mcp-tool-count"
    check_name = "MCP tool count matches docs"

    src_dir = root / "src"
    if not src_dir.exists():
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="src/ directory not found.",
        )

    actual_count = 0
    for py_file in src_dir.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
            actual_count += len(re.findall(r"@server\.tool\(\)", text))
        except OSError:
            continue

    if actual_count == 0:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="No @server.tool() decorators found in src/.",
        )

    readme_path = root / "README.md"
    claimed = _find_numeric_claim(readme_path, r"(\d+)\s+MCP\s+tool[s]?")
    if claimed is None:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=(
                f"{actual_count} @server.tool() decorators found; "
                "no count claim found in README.md."
            ),
        )

    if claimed == actual_count:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details=f"{actual_count} MCP tools found; README matches.",
            file=str(readme_path),
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=(
            f"README claims {claimed} MCP tools but "
            f"{actual_count} @server.tool() decorators found."
        ),
        file=str(readme_path),
        auto_fixable=True,
    )


def check_file_line_limits(project_root: str = ".") -> CheckResult:
    """Check that no Python file in src/ exceeds 1000 lines.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "file-line-limits"
    check_name = "No Python file exceeds 1000 lines"
    limit = 1000

    src_dir = root / "src"
    if not src_dir.exists():
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="src/ directory not found.",
        )

    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        try:
            lines = py_file.read_text(encoding="utf-8").count("\n")
            if lines > limit:
                rel = py_file.relative_to(root)
                violations.append(f"{rel} ({lines} lines)")
        except OSError:
            continue

    if not violations:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details=f"All Python files are under {limit} lines.",
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=(
            f"{len(violations)} file(s) exceed {limit} lines: "
            + ", ".join(violations[:5])
            + (" ..." if len(violations) > 5 else "")
        ),
        file=str(src_dir),
        auto_fixable=False,
    )


def check_install_extras(project_root: str = ".") -> CheckResult:
    """Compare [project.optional-dependencies] in pyproject.toml to README.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "install-extras"
    check_name = "Install extras match between pyproject.toml and README"

    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="pyproject.toml not found.",
        )

    content = pyproject_path.read_text(encoding="utf-8")
    # Extract extra names from [project.optional-dependencies]
    block_match = re.search(
        r"\[project\.optional-dependencies\](.*?)(?=\[|\Z)",
        content,
        re.DOTALL,
    )
    if not block_match:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="[project.optional-dependencies] not found in pyproject.toml.",
            file=str(pyproject_path),
        )

    extras_block = block_match.group(1)
    # Lines like: developer = [...]
    pyproject_extras = set(re.findall(r"^(\w+)\s*=", extras_block, re.MULTILINE))

    readme_path = root / "README.md"
    if not readme_path.exists():
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=(f"pyproject.toml extras: {sorted(pyproject_extras)}. " "README.md not found."),
            file=str(pyproject_path),
        )

    readme_content = readme_path.read_text(encoding="utf-8")
    # Look for extras in install examples: pip install attune-ai[extra]
    readme_extras = set(re.findall(r"attune-ai\[([^\]]+)\]", readme_content))
    # Split comma-separated combos like [memory,redis]
    expanded: set[str] = set()
    for combo in readme_extras:
        for part in combo.split(","):
            expanded.add(part.strip())
    readme_extras = expanded

    missing_from_readme = pyproject_extras - readme_extras
    missing_from_pyproject = readme_extras - pyproject_extras

    if not missing_from_readme and not missing_from_pyproject:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details=f"Extras consistent: {sorted(pyproject_extras)}.",
            file=str(pyproject_path),
        )

    parts = []
    if missing_from_readme:
        parts.append(f"in pyproject.toml but not README: {sorted(missing_from_readme)}")
    if missing_from_pyproject:
        parts.append(f"in README but not pyproject.toml: {sorted(missing_from_pyproject)}")

    return CheckResult(
        id=check_id,
        name=check_name,
        status="warn",
        details="; ".join(parts),
        file=str(readme_path),
        auto_fixable=False,
    )


def check_stale_references(project_root: str = ".") -> CheckResult:
    """Grep docs and .claude/ for removed/renamed patterns.

    Looks for references to removed features such as "dashboard",
    "empathy_framework", or other deprecated names.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "stale-references"
    check_name = "No stale references to removed features"

    # Patterns that should no longer appear in docs or skill files
    stale_patterns = [
        "empathy_framework",
        "EmpathyConfig",
        "HealthCheckCrew",
        "TestCoverageBoostCrew",
        "ReleasePreparationCrew",
    ]

    # Search dirs: docs/, .claude/commands/, README.md
    search_paths: list[Path] = []
    docs_dir = root / "docs"
    if docs_dir.exists():
        search_paths.extend(docs_dir.rglob("*.md"))
    commands_dir = root / ".claude" / "commands"
    if commands_dir.exists():
        search_paths.extend(commands_dir.glob("*.md"))
    readme = root / "README.md"
    if readme.exists():
        search_paths.append(readme)

    hits: list[str] = []
    for path in search_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for pattern in stale_patterns:
            if pattern in text:
                rel = path.relative_to(root) if path.is_relative_to(root) else path
                hits.append(f"{rel}: '{pattern}'")

    if not hits:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details="No stale references found.",
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=f"{len(hits)} stale reference(s): " + "; ".join(hits[:5]),
        file=str(root),
        auto_fixable=False,
    )


def check_version_consistency(project_root: str = ".") -> CheckResult:
    """Compare version strings across pyproject.toml, __init__.py, CHANGELOG.md.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "version-consistency"
    check_name = "Version consistent across pyproject.toml, __init__.py, CHANGELOG.md"

    sources: dict[str, str | None] = {}

    # pyproject.toml: version = "X.Y.Z"
    pyproject_path = root / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        sources["pyproject.toml"] = m.group(1) if m else None

    # src/attune/__init__.py: __version__ = "X.Y.Z"
    init_path = root / "src" / "attune" / "__init__.py"
    if init_path.exists():
        content = init_path.read_text(encoding="utf-8")
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        sources["__init__.py"] = m.group(1) if m else None

    # CHANGELOG.md: ## [X.Y.Z] or ## X.Y.Z
    changelog_path = root / "CHANGELOG.md"
    if changelog_path.exists():
        content = changelog_path.read_text(encoding="utf-8")
        m = re.search(r"##\s+\[?(\d+\.\d+\.\d+[^\s\]]*)", content)
        sources["CHANGELOG.md"] = m.group(1) if m else None

    found = {k: v for k, v in sources.items() if v is not None}
    if not found:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="Could not extract version from any source file.",
        )

    versions = set(found.values())
    if len(versions) == 1:
        version = next(iter(versions))
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details=f"Version {version!r} consistent across: {list(found.keys())}.",
        )

    mismatch_detail = "; ".join(f"{k}={v}" for k, v in found.items())
    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=f"Version mismatch: {mismatch_detail}.",
        file=str(pyproject_path),
        auto_fixable=False,
    )


def check_cross_doc_numbers(project_root: str = ".") -> CheckResult:
    """Find numeric claims in docs that contradict each other.

    Scans README.md and docs/ for sentences containing numbers adjacent
    to common nouns (tests, workflows, skills) and flags contradictions.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "cross-doc-numbers"
    check_name = "Numeric claims consistent across docs"

    # Pattern: number + noun (e.g. "146 tests", "10 workflows")
    claim_pattern = re.compile(
        r"(\d+)\s+(test[s]?|workflow[s]?|skill[s]?|command[s]?|tool[s]?|stage[s]?)",
        re.IGNORECASE,
    )

    # Collect all claims: noun -> set of (count, file)
    claims: dict[str, list[tuple[int, str]]] = {}

    scan_paths: list[Path] = []
    readme = root / "README.md"
    if readme.exists():
        scan_paths.append(readme)
    docs_dir = root / "docs"
    if docs_dir.exists():
        scan_paths.extend(docs_dir.rglob("*.md"))

    for path in scan_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        for m in claim_pattern.finditer(text):
            count = int(m.group(1))
            noun = m.group(2).lower().rstrip("s")  # normalize to singular
            claims.setdefault(noun, []).append((count, rel))

    contradictions: list[str] = []
    for noun, entries in claims.items():
        counts = {c for c, _ in entries}
        if len(counts) > 1:
            detail = "; ".join(f"{c} ({f})" for c, f in entries[:4])
            contradictions.append(f"{noun}: {detail}")

    if not contradictions:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details="No numeric contradictions found across docs.",
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=(f"{len(contradictions)} contradiction(s): " + " | ".join(contradictions[:3])),
        auto_fixable=False,
    )


def check_documentation_links(project_root: str = ".") -> CheckResult:
    """Verify that local links in .md files resolve to existing files.

    Scans all .md files under docs/ and .claude/commands/ for
    Markdown links like [text](path) where path does not start with
    http:// or https://.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status.

    """
    root = Path(project_root)
    check_id = "documentation-links"
    check_name = "Local links in .md files resolve to existing files"

    # Pattern: [text](path) where path is not a URL
    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

    scan_paths: list[Path] = []
    docs_dir = root / "docs"
    if docs_dir.exists():
        scan_paths.extend(docs_dir.rglob("*.md"))
    commands_dir = root / ".claude" / "commands"
    if commands_dir.exists():
        scan_paths.extend(commands_dir.glob("*.md"))
    readme = root / "README.md"
    if readme.exists():
        scan_paths.append(readme)

    broken: list[str] = []

    for md_path in scan_paths:
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue

        for m in link_pattern.finditer(text):
            raw_target = m.group(2)
            # Skip URLs and anchors
            if raw_target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Strip anchor fragments
            target = raw_target.split("#")[0]
            if not target:
                continue

            # Resolve relative to the md file's directory
            resolved = (md_path.parent / target).resolve()
            if not resolved.exists():
                rel_md = md_path.relative_to(root) if md_path.is_relative_to(root) else md_path
                broken.append(f"{rel_md}: '{raw_target}'")

    if not broken:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="pass",
            details="All local documentation links resolve correctly.",
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="fail",
        details=(
            f"{len(broken)} broken link(s): "
            + "; ".join(broken[:5])
            + (" ..." if len(broken) > 5 else "")
        ),
        auto_fixable=False,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _find_numeric_claim(path: Path, pattern: str) -> int | None:
    """Search a file for the first match of a numeric claim pattern.

    Args:
        path: Path to the file to search.
        pattern: Regex pattern with one numeric capture group.

    Returns:
        Matched integer or None.

    """
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(pattern, content, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def run_all_checks(project_root: str = ".") -> list[CheckResult]:
    """Run all 10 documentation audit checks.

    Args:
        project_root: Root directory of the project.

    Returns:
        List of CheckResult objects, one per check.

    """
    check_functions = [
        check_test_count,
        check_workflow_count,
        check_skill_count,
        check_mcp_tool_count,
        check_file_line_limits,
        check_install_extras,
        check_stale_references,
        check_version_consistency,
        check_cross_doc_numbers,
        check_documentation_links,
    ]
    return [fn(project_root) for fn in check_functions]
