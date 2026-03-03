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
    """Verify test count badge in README matches actual pytest count.

    Runs pytest --collect-only to get the actual test count and
    searches README.md for badge patterns like "tests-146-" or "146 tests".

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and file path if applicable.

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
    # Look for badge patterns like "tests-16%2C676%20passing" (URL-encoded),
    # "tests-146-brightgreen", or "16,676 tests passing"
    badge_match = re.search(
        r"tests[-_]?((?:\d+%2C)*\d+)(?:%20|\s|-)|" r"([\d,]+)\s+tests?\b",
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

    raw = badge_match.group(1) or badge_match.group(2)
    # Decode URL-encoded commas and strip regular commas
    badge_count = int(raw.replace("%2C", "").replace(",", ""))
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
    """Verify workflow count in docs matches registered workflows.

    Parses _DEFAULT_WORKFLOW_NAMES dict from workflows/__init__.py
    (without importing) and compares to README.md claims.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and file paths if applicable.

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

    # Check README.md or docs for a claimed workflow count.
    # Try table pattern "N built-in" first (comparison table), then "N workflow(s)".
    readme_path = root / "README.md"
    claimed = _find_numeric_claim(readme_path, r"(\d+)\s+built-in")
    if claimed is None:
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
    """Verify skill count in docs matches .claude/commands/ files.

    Counts .md files in .claude/commands/ and compares to README.md.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and file paths if applicable.

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
    """Verify MCP tool count in docs matches actual registered tools.

    Counts tools by looking for @server.tool() decorators and
    dict-key entries in _register_tools() methods across src/.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and file paths if applicable.

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
        except OSError:
            continue
        # Count @server.tool() decorators (only actual decorator lines)
        actual_count += len(re.findall(r"^\s*@server\.tool\(\)", text, re.MULTILINE))
        # Count dict-key tool entries in _register_tools() return dicts.
        # Extracts the return block and counts top-level keys by finding
        # the indentation of the first key, then matching that exact level.
        if "_register_tools" in text:
            block_match = re.search(
                r"def _register_tools\b.*?return\s*\{(.*?)\n\s{8}\}",
                text,
                re.DOTALL,
            )
            if block_match:
                block = block_match.group(1)
                # Find indentation of first key
                first_key = re.search(r"\n( +)\"(\w+)\": \{", block)
                if first_key:
                    indent = first_key.group(1)
                    for line in block.split("\n"):
                        if re.match(rf"^{re.escape(indent)}\"(\w+)\": \{{", line):
                            actual_count += 1

    if actual_count == 0:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details="No MCP tools found in src/.",
        )

    readme_path = root / "README.md"
    claimed = _find_numeric_claim(readme_path, r"(\d+)\s+MCP\s+tool[s]?")
    if claimed is None:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="warn",
            details=(f"{actual_count} MCP tools found; " "no count claim found in README.md."),
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
        details=(f"README claims {claimed} MCP tools but " f"{actual_count} MCP tools found."),
        file=str(readme_path),
        auto_fixable=True,
    )


def check_file_line_limits(project_root: str = ".") -> CheckResult:
    """Verify no Python file in src/ exceeds 1000 lines.

    Scans all .py files recursively and flags violations.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and violating files if any.

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
    """Verify install extras match between pyproject.toml and README.

    Extracts [project.optional-dependencies] from pyproject.toml and
    searches for corresponding extras in README.md install examples.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and file paths if applicable.

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
    # Extract extra names from [project.optional-dependencies].
    # Stop at the next TOML section header (line starting with [word).
    block_match = re.search(
        r"\[project\.optional-dependencies\]\n(.*?)(?=\n\[(?!project\.optional)|\Z)",
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

    # Extras in pyproject.toml but not README is fine (not all need advertising).
    # Extras in README but not pyproject.toml is a real problem (broken install).
    if missing_from_pyproject:
        return CheckResult(
            id=check_id,
            name=check_name,
            status="fail",
            details=f"in README but not pyproject.toml: {sorted(missing_from_pyproject)}",
            file=str(readme_path),
            auto_fixable=False,
        )

    return CheckResult(
        id=check_id,
        name=check_name,
        status="pass",
        details=(
            f"All {len(readme_extras)} README extras exist in pyproject.toml"
            f" ({len(pyproject_extras)} total defined)."
        ),
        file=str(pyproject_path),
    )


def check_stale_references(project_root: str = ".") -> CheckResult:
    """Detect references to removed or deprecated features in docs.

    Searches docs/, .claude/commands/, and README.md for patterns
    like "dashboard", "empathy_framework", and other removed names.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and files with stale refs.

    """
    root = Path(project_root)
    check_id = "stale-references"
    check_name = "No stale references to removed features"

    # Patterns that should no longer appear in docs or skill files
    stale_patterns = [
        "empathy_framework",
        "EmpathyConfig",
        "TestCoverageBoostCrew",
        "ReleasePreparationCrew",
    ]

    # Search dirs: docs/ (excluding archive/), .claude/commands/, README.md
    search_paths: list[Path] = []
    docs_dir = root / "docs"
    archive_dir = docs_dir / "archive"
    if docs_dir.exists():
        search_paths.extend(p for p in docs_dir.rglob("*.md") if not p.is_relative_to(archive_dir))
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
    """Verify version is consistent across pyproject.toml, __init__.py, CHANGELOG.md.

    Extracts version strings from all three files and confirms they match.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and version mismatches if any.

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
    """Detect contradictory numeric claims across documentation.

    Scans README.md and docs/ for numeric patterns adjacent to nouns
    (tests, workflows, skills, etc.) and flags inconsistencies.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and contradictions if found.

    """
    root = Path(project_root)
    check_id = "cross-doc-numbers"
    check_name = "Numeric claims consistent across docs"

    # Pattern: number + noun (e.g. "146 tests", "10 workflows")
    # Must be a direct count claim, not part of a larger phrase
    claim_pattern = re.compile(
        r"(?<!\w)(\d+)\s+(test[s]?|workflow[s]?|skill[s]?|command[s]?|tool[s]?|stage[s]?)"
        r"(?!\s+(?:mixin|module|helper|function|method|class|file|line|pattern|second|"
        r"minute|hour|day|week|month|year|byte|item|step|iteration|version|page|example))",
        re.IGNORECASE,
    )

    # Patterns that indicate a non-current claim (historical comparison)
    skip_context = re.compile(
        r"(?:from|up from|was|were|had|only|just|previously)\s+\d+\s+",
        re.IGNORECASE,
    )

    # Strip fenced code blocks
    code_block_pattern = re.compile(r"```.*?```", re.DOTALL)

    # Collect all claims: noun -> set of (count, file)
    claims: dict[str, list[tuple[int, str]]] = {}

    scan_paths: list[Path] = []
    readme = root / "README.md"
    if readme.exists():
        scan_paths.append(readme)
    docs_dir = root / "docs"
    archive_dir = docs_dir / "archive"
    if docs_dir.exists():
        scan_paths.extend(p for p in docs_dir.rglob("*.md") if not p.is_relative_to(archive_dir))

    for path in scan_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Remove code blocks to avoid matching example output
        text_clean = code_block_pattern.sub("", text)

        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        for m in claim_pattern.finditer(text_clean):
            count = int(m.group(1))
            noun = m.group(2).lower().rstrip("s")  # normalize to singular
            # Skip small numbers unlikely to be total project counts
            # Tests are typically 100+, workflows 5+, others 3+
            min_threshold = 100 if noun == "test" else 3
            if count < min_threshold:
                continue
            # Skip historical comparison context
            start = max(0, m.start() - 30)
            preceding = text_clean[start : m.start()]
            if skip_context.search(preceding):
                continue
            # Skip fraction patterns like "5/6 tests"
            if re.search(r"\d+/\d+\s*$", preceding):
                continue
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
    """Verify local links in markdown files resolve to existing files.

    Scans all .md files in docs/, .claude/commands/, and README.md for
    Markdown links [text](path) where path is not an http(s) URL or anchor,
    and checks that target files exist.

    Args:
        project_root: Root directory of the project.

    Returns:
        CheckResult with pass/fail/warn status and broken links if any.

    """
    root = Path(project_root)
    check_id = "documentation-links"
    check_name = "Local links in .md files resolve to existing files"

    # Pattern: [text](path) where path is not a URL
    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

    scan_paths: list[Path] = []
    docs_dir = root / "docs"
    archive_dir = docs_dir / "archive"
    if docs_dir.exists():
        scan_paths.extend(p for p in docs_dir.rglob("*.md") if not p.is_relative_to(archive_dir))
    commands_dir = root / ".claude" / "commands"
    if commands_dir.exists():
        scan_paths.extend(commands_dir.glob("*.md"))
    readme = root / "README.md"
    if readme.exists():
        scan_paths.append(readme)

    broken: list[str] = []

    # Pattern to strip fenced code blocks before link scanning
    code_block_pattern = re.compile(r"```.*?```", re.DOTALL)

    for md_path in scan_paths:
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Remove fenced code blocks so links inside examples are ignored
        text_no_code = code_block_pattern.sub("", text)

        for m in link_pattern.finditer(text_no_code):
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
        Matched integer or None if path does not exist or pattern
        is not found.

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
    """Run all 10 documentation audit checks in sequence.

    Checks cover test counts, workflow counts, version consistency,
    broken links, stale references, and other accuracy metrics.

    Args:
        project_root: Root directory of the project.

    Returns:
        List of 10 CheckResult objects, one per check function.

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
