"""Code Review Workflow

A tiered code analysis pipeline:
1. Haiku: Classify change type (cheap, fast)
2. Sonnet: Security scan + bug pattern matching
3. Opus: Architectural review (conditional on complexity)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import re
from pathlib import Path
from typing import Any

from .base import BaseWorkflow, ModelTier
from .code_review_report import format_code_review_report  # noqa: F401
from .context import WorkflowContext
from .perf_audit import PERF_PATTERNS
from .services import ParsingService, PromptService
from .step_config import WorkflowStepConfig

logger = logging.getLogger(__name__)

# Quality check thresholds
MAX_FILE_LINES = 500
CHARS_PER_TOKEN_ESTIMATE = 4

# Define step configurations for executor-based execution
CODE_REVIEW_STEPS = {
    "architect_review": WorkflowStepConfig(
        name="architect_review",
        task_type="architectural_decision",  # Premium tier task
        tier_hint="premium",
        description="Comprehensive architectural code review",
        max_tokens=3000,
    ),
}


def _has_return_type_hint(content: str, func_start: int) -> bool:
    """Check if a function definition has a return type hint.

    Uses parenthesis depth tracking to find the closing paren,
    then checks for ``->`` between ``)`` and the body colon.

    Args:
        content: Full file content string.
        func_start: Character offset of the ``def`` keyword.

    Returns:
        True if the function has a ``-> ...`` return type annotation.
    """
    open_paren = content.find("(", func_start)
    if open_paren == -1:
        return True  # Can't determine, assume OK
    depth = 1
    pos = open_paren + 1
    while pos < len(content) and depth > 0:
        if content[pos] == "(":
            depth += 1
        elif content[pos] == ")":
            depth -= 1
        pos += 1
    if depth != 0:
        return True  # Malformed, assume OK
    colon_pos = content.find(":", pos)
    if colon_pos == -1:
        return True
    return "->" in content[pos:colon_pos]


def _gather_file_snippets(
    findings: list[dict],
    context_lines: int = 3,
) -> dict[str, dict[int, str]]:
    """Read source files and extract snippet context around each finding.

    Args:
        findings: List of finding dicts with ``file`` and ``line`` keys.
        context_lines: Number of lines to include above/below the finding.

    Returns:
        Dict mapping file path to {line_num: snippet_text}.
    """
    snippets: dict[str, dict[int, str]] = {}
    file_cache: dict[str, list[str]] = {}
    for finding in findings:
        fpath = finding.get("file", "")
        line_num = finding.get("line")
        if not fpath or not line_num:
            continue
        if fpath not in file_cache:
            try:
                file_cache[fpath] = Path(fpath).read_text(errors="ignore").splitlines()
                snippets[fpath] = {}
            except OSError:
                continue
        file_lines = file_cache[fpath]
        start = max(0, line_num - 1 - context_lines)
        end = min(len(file_lines), line_num + context_lines)
        snippet = "\n".join(f"  {i + 1}: {file_lines[i]}" for i in range(start, end))
        snippets[fpath][line_num] = snippet
    return snippets


def _format_findings_for_prompt(
    findings: list[dict],
    snippets: dict[str, dict[int, str]],
) -> str:
    """Format findings and their code snippets into a prompt string.

    Args:
        findings: List of finding dicts.
        snippets: Output from ``_gather_file_snippets()``.

    Returns:
        Formatted string for inclusion in an LLM prompt.
    """
    parts: list[str] = []
    for i, finding in enumerate(findings):
        fpath = finding.get("file", "?")
        line_num = finding.get("line", "?")
        desc = finding.get("description", "")
        ftype = finding.get("type", "unknown")
        severity = finding.get("severity", finding.get("impact", "unknown"))
        parts.append(f"[{i}] {ftype} ({severity}) at {fpath}:{line_num}\n" f"    {desc}")
        snippet = snippets.get(fpath, {}).get(line_num)
        if snippet:
            parts.append(f"    Code context:\n{snippet}")
        parts.append("")
    return "\n".join(parts)


def _parse_deep_enrichment(
    response: str,
    original_findings: list[dict],
) -> list[dict]:
    """Parse LLM JSON response and merge enrichment into findings.

    Gracefully handles malformed responses by keeping original findings
    unchanged when parsing fails.

    Args:
        response: Raw LLM response (expected JSON with ``findings`` key).
        original_findings: Original finding dicts from CHEAP stage.

    Returns:
        List of enriched finding dicts with added keys:
        ``validated``, ``false_positive``, ``suggestion``.
    """
    import json as _json

    enriched = [dict(f) for f in original_findings]  # shallow copy each

    try:
        # Try to extract JSON from response
        text = response.strip()
        # Handle markdown code blocks
        if "```" in text:
            start = text.find("```")
            end = text.rfind("```")
            if start != end:
                inner = text[start:end]
                # Remove opening fence line
                inner = inner.split("\n", 1)[1] if "\n" in inner else inner
                text = inner.strip()

        data = _json.loads(text)
        llm_findings = data.get("findings", [])

        for item in llm_findings:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(enriched):
                enriched[idx]["validated"] = item.get("validated", True)
                enriched[idx]["false_positive"] = item.get("false_positive", False)
                if "suggestion" in item:
                    enriched[idx]["suggestion"] = item["suggestion"]
                if "severity" in item:
                    # Allow severity adjustment but preserve original key name
                    sev_key = "severity" if "severity" in enriched[idx] else "impact"
                    enriched[idx][sev_key] = item["severity"]
    except (ValueError, KeyError, TypeError) as e:
        logger.warning(f"Could not parse deep enrichment response: {e}")
        # Return originals with validated=True (assume valid if can't parse)
        for f in enriched:
            f["validated"] = True
            f["false_positive"] = False

    return enriched


def _recount_by_key(findings: list[dict], key: str) -> dict[str, int]:
    """Recount findings by a grouping key, excluding false positives.

    Args:
        findings: List of finding dicts (may include ``false_positive`` flag).
        key: Key to group by (``"severity"`` or ``"impact"``).

    Returns:
        Dict mapping key values to counts, e.g. ``{"high": 2, "medium": 1, "low": 0}``.
    """
    counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        if f.get("false_positive", False):
            continue
        val = f.get(key, "low")
        counts[val] = counts.get(val, 0) + 1
    return counts


class CodeReviewWorkflow(BaseWorkflow):
    """Multi-tier code review workflow.

    Uses cheap models for classification, capable models for security
    and bug scanning, and premium models only for complex architectural
    reviews (10+ files or core module changes).

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.

    Usage:
        workflow = CodeReviewWorkflow()
        result = await workflow.execute(
            diff="...",
            files_changed=["src/main.py", "tests/test_main.py"],
            is_core_module=False
        )
    """

    name = "code-review"
    description = "Tiered code analysis with conditional premium review"
    stages = [
        "classify",
        "scan",
        "perf_check",
        "perf_check_deep",
        "health_monitor",
        "quality_check",
        "quality_check_deep",
        "architect_review",
    ]
    tier_map = {
        "classify": ModelTier.CHEAP,
        "scan": ModelTier.CAPABLE,
        "perf_check": ModelTier.CHEAP,
        "perf_check_deep": ModelTier.CAPABLE,
        "health_monitor": ModelTier.CHEAP,
        "quality_check": ModelTier.CHEAP,
        "quality_check_deep": ModelTier.CAPABLE,
        "architect_review": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        file_threshold: int = 10,
        core_modules: list[str] | None = None,
        use_crew: bool = True,
        crew_config: dict | None = None,
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize workflow.

        Args:
            file_threshold: Number of files above which premium review is used.
            core_modules: List of module paths considered "core" (trigger premium).
            use_crew: Enable CodeReviewCrew for comprehensive 5-agent analysis (default: True).
            crew_config: Configuration dict for CodeReviewCrew.
            enable_auth_strategy: If True, use intelligent subscription vs API routing
                based on module size (default True).

        """
        super().__init__(**kwargs)
        self.file_threshold = file_threshold
        self.core_modules = core_modules or [
            "src/core/",
            "src/security/",
            "src/auth/",
            "empathy_os/core.py",
            "empathy_os/security/",
        ]
        self.use_crew = use_crew
        self.crew_config = crew_config or {}
        self.enable_auth_strategy = enable_auth_strategy
        self._needs_architect_review: bool = False
        self._change_type: str = "unknown"
        self._crew: Any = None
        self._crew_available = False
        self._auth_mode_used: str | None = None

        # Dynamically configure stages based on crew setting
        if use_crew:
            self.stages = [
                "classify",
                "crew_review",
                "scan",
                "perf_check",
                "perf_check_deep",
                "health_monitor",
                "quality_check",
                "quality_check_deep",
                "architect_review",
            ]
            self.tier_map = {
                "classify": ModelTier.CHEAP,
                "crew_review": ModelTier.CAPABLE,
                "scan": ModelTier.CAPABLE,
                "perf_check": ModelTier.CHEAP,
                "perf_check_deep": ModelTier.CAPABLE,
                "health_monitor": ModelTier.CHEAP,
                "quality_check": ModelTier.CHEAP,
                "quality_check_deep": ModelTier.CAPABLE,
                "architect_review": ModelTier.PREMIUM,
            }

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for code review.

        Args:
            xml_config: Optional XML prompt configuration dict.
                Defaults to XML disabled — benchmarks on Claude 4.x show
                +56% cost overhead with no quality improvement for code review.

        Returns:
            WorkflowContext with prompt and parsing services.
        """
        if xml_config is None:
            xml_config = {"enabled": False}
        return WorkflowContext(
            prompt=PromptService("code-review", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    async def _initialize_crew(self) -> None:
        """Initialize the CodeReviewCrew."""
        if self._crew is not None:
            return

        try:
            import logging

            from attune.agent_factory.crews.code_review import CodeReviewCrew

            self._crew = CodeReviewCrew()
            self._crew_available = True
            logging.getLogger(__name__).info("CodeReviewCrew initialized successfully")
        except ImportError as e:
            import logging

            logging.getLogger(__name__).warning(f"CodeReviewCrew not available: {e}")
            self._crew_available = False

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Skip stages when appropriate."""
        # Skip all stages after classify if there was an input error
        if isinstance(input_data, dict) and input_data.get("error"):
            if stage_name != "classify":
                return True, "Skipped due to input validation error"

        # Skip crew review if crew is not available
        if stage_name == "crew_review" and not self._crew_available:
            return True, "CodeReviewCrew not available"

        # Skip perf_check and quality_check if no files to analyze
        if stage_name in ("perf_check", "quality_check"):
            files = input_data.get("files_changed", []) if isinstance(input_data, dict) else []
            if not files:
                return True, f"No files_changed provided for {stage_name}"

        # Skip deep stages if their CHEAP counterpart found nothing
        if stage_name == "perf_check_deep":
            count = input_data.get("perf_finding_count", 0) if isinstance(input_data, dict) else 0
            if count == 0:
                return True, "No perf findings to enrich"

        if stage_name == "quality_check_deep":
            count = (
                input_data.get("quality_finding_count", 0) if isinstance(input_data, dict) else 0
            )
            if count == 0:
                return True, "No quality findings to enrich"

        # Skip architectural review if change is simple
        if stage_name == "architect_review" and not self._needs_architect_review:
            return True, "Simple change - architectural review not needed"
        return False, None

    def _gather_project_context(self) -> str:
        """Gather project context for project-level reviews.

        Reads project metadata and key files to provide context to the LLM.
        Returns formatted project context string, or empty string if no context found.
        """
        import os
        from pathlib import Path

        context_parts = []
        cwd = Path.cwd()

        # Get project name from directory or config files
        project_name = cwd.name
        context_parts.append(f"# Project: {project_name}")
        context_parts.append(f"# Path: {cwd}")
        context_parts.append("")

        # Check for pyproject.toml
        pyproject = cwd / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()[:2000]
                context_parts.append("## pyproject.toml")
                context_parts.append("```toml")
                context_parts.append(content)
                context_parts.append("```")
                context_parts.append("")
            except OSError:
                pass

        # Check for package.json
        package_json = cwd / "package.json"
        if package_json.exists():
            try:
                content = package_json.read_text()[:2000]
                context_parts.append("## package.json")
                context_parts.append("```json")
                context_parts.append(content)
                context_parts.append("```")
                context_parts.append("")
            except OSError:
                pass

        # Check for README
        for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
            readme = cwd / readme_name
            if readme.exists():
                try:
                    content = readme.read_text()[:3000]
                    context_parts.append(f"## {readme_name}")
                    context_parts.append(content)
                    context_parts.append("")
                    break
                except OSError:
                    pass

        # Get directory structure (top 2 levels)
        context_parts.append("## Project Structure")
        context_parts.append("```")
        try:
            for root, dirs, files in os.walk(cwd):
                # Skip hidden and common ignored directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d
                    not in (
                        "node_modules",
                        "__pycache__",
                        "venv",
                        ".venv",
                        "dist",
                        "build",
                        ".git",
                        ".tox",
                        ".pytest_cache",
                        ".mypy_cache",
                        "htmlcov",
                    )
                ]
                level = root.replace(str(cwd), "").count(os.sep)
                if level < 2:
                    indent = "  " * level
                    folder_name = os.path.basename(root) or project_name
                    context_parts.append(f"{indent}{folder_name}/")
                    # Show key files at this level
                    key_files = [
                        f
                        for f in files
                        if f.endswith(
                            (".py", ".ts", ".js", ".json", ".yaml", ".yml", ".toml", ".md"),
                        )
                        and not f.startswith(".")
                    ][:10]
                    for f in key_files:
                        context_parts.append(f"{indent}  {f}")
                if level >= 2:
                    break
        except OSError:
            context_parts.append("(Unable to read directory structure)")
        context_parts.append("```")

        # Return empty if we only have the header
        if len(context_parts) <= 3:
            return ""

        return "\n".join(context_parts)

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Execute a code review stage."""
        if stage_name == "classify":
            return await self._classify(input_data, tier)
        if stage_name == "crew_review":
            return await self._crew_review(input_data, tier)
        if stage_name == "scan":
            return await self._scan(input_data, tier)
        if stage_name == "perf_check":
            return await self._perf_check(input_data, tier)
        if stage_name == "perf_check_deep":
            return await self._perf_check_deep(input_data, tier)
        if stage_name == "health_monitor":
            return await self._health_monitor(input_data, tier)
        if stage_name == "quality_check":
            return await self._quality_check(input_data, tier)
        if stage_name == "quality_check_deep":
            return await self._quality_check_deep(input_data, tier)
        if stage_name == "architect_review":
            return await self._architect_review(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _classify(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Classify the type of change."""
        diff = input_data.get("diff", "")
        target = input_data.get("target", "")
        files_changed = input_data.get("files_changed", [])

        # If target provided instead of diff, use it as the code to review
        code_to_review = diff or target

        # Handle project-level review when target is "." or empty
        if not code_to_review or code_to_review.strip() in (".", "", "./"):
            # Gather project context for project-level review
            project_context = self._gather_project_context()
            if not project_context:
                # Return early with helpful error message if no context found
                return (
                    {
                        "classification": "ERROR: No code provided for review",
                        "error": True,
                        "error_message": (
                            "No code was provided for review. Please ensure you:\n"
                            "1. Have a file open in the editor, OR\n"
                            "2. Select a specific file to review, OR\n"
                            '3. Provide code content directly via --input \'{"diff": "..."}\'\n\n'
                            "Tip: Use 'Select File...' option in the workflow picker."
                        ),
                        "change_type": "none",
                        "files_changed": [],
                        "file_count": 0,
                        "needs_architect_review": False,
                        "is_core_module": False,
                        "code_to_review": "",
                    },
                    0,
                    0,
                )
            code_to_review = project_context
            # Mark as project-level review
            input_data["is_project_review"] = True

        # === AUTH STRATEGY INTEGRATION ===
        if self.enable_auth_strategy:
            try:
                import logging
                from pathlib import Path

                from attune.models import (
                    count_lines_of_code,
                    get_auth_strategy,
                    get_module_size_category,
                )

                logger = logging.getLogger(__name__)

                # Calculate module size (for file) or total LOC (for directory)
                target_path = target or diff
                total_lines = 0
                if target_path:
                    target_obj = Path(target_path)
                    if target_obj.exists():
                        if target_obj.is_file():
                            total_lines = count_lines_of_code(target_obj)
                        elif target_obj.is_dir():
                            for py_file in target_obj.rglob("*.py"):
                                try:
                                    total_lines += count_lines_of_code(py_file)
                                except Exception:
                                    pass

                if total_lines > 0:
                    strategy = get_auth_strategy()
                    recommended_mode = strategy.get_recommended_mode(total_lines)
                    self._auth_mode_used = recommended_mode.value

                    size_category = get_module_size_category(total_lines)
                    logger.info(
                        f"Code review target: {target_path} ({total_lines:,} LOC, {size_category})"
                    )
                    logger.info(f"Recommended auth mode: {recommended_mode.value}")

                    cost_estimate = strategy.estimate_cost(total_lines, recommended_mode)
                    if recommended_mode.value == "subscription":
                        logger.info(f"Cost: {cost_estimate['quota_cost']}")
                    else:
                        logger.info(f"Cost: ~${cost_estimate['monetary_cost']:.4f}")

            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Auth strategy detection failed: {e}")

        system = """You are a code review classifier. Analyze the code and classify:
1. Change type: bug_fix, feature, refactor, docs, test, config, or security
2. Complexity: low, medium, high
3. Risk level: low, medium, high

Respond with a brief classification summary."""

        user_message = f"""Classify this code change:

Files: {", ".join(files_changed) if files_changed else "Not specified"}

Code:
{code_to_review[:4000]}"""

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=500,
        )

        # Parse response to determine if architect review needed
        is_high_complexity = "high" in response.lower() and (
            "complexity" in response.lower() or "risk" in response.lower()
        )
        is_core = (
            any(any(core in f for core in self.core_modules) for f in files_changed)
            if files_changed
            else False
        )

        self._needs_architect_review = (
            len(files_changed) >= self.file_threshold
            or is_core
            or is_high_complexity
            or input_data.get("is_core_module", False)
        )

        return (
            {
                "classification": response,
                "change_type": "feature",  # Will be refined by LLM
                "files_changed": files_changed,
                "file_count": len(files_changed),
                "needs_architect_review": self._needs_architect_review,
                "is_core_module": is_core,
                "code_to_review": code_to_review,
            },
            input_tokens,
            output_tokens,
        )

    async def _crew_review(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Run CodeReviewCrew for comprehensive 5-agent analysis.

        This stage uses the CodeReviewCrew (Review Lead, Security Analyst,
        Architecture Reviewer, Quality Analyst, Performance Reviewer) for
        deep code analysis with memory graph integration.

        Falls back gracefully if CodeReviewCrew is not available.
        """
        await self._initialize_crew()

        try:
            from .code_review_adapters import (
                _check_crew_available,
                _get_crew_review,
                crew_report_to_workflow_format,
            )
        except ImportError:
            # Crew adapters removed - return fallback
            return (
                {
                    "crew_review": {
                        "available": False,
                        "fallback": True,
                        "reason": "Crew adapters not installed",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Get code to review
        diff = input_data.get("diff", "") or input_data.get("code_to_review", "")
        files_changed = input_data.get("files_changed", [])

        # Check if crew is available
        if not self._crew_available or not _check_crew_available():
            return (
                {
                    "crew_review": {
                        "available": False,
                        "fallback": True,
                        "reason": "CodeReviewCrew not installed or failed to initialize",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Run CodeReviewCrew
        report = await _get_crew_review(
            diff=diff,
            files_changed=files_changed,
            config=self.crew_config,
        )

        if report is None:
            return (
                {
                    "crew_review": {
                        "available": True,
                        "fallback": True,
                        "reason": "CodeReviewCrew review failed or timed out",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Convert crew report to workflow format
        crew_results = crew_report_to_workflow_format(report)

        # Update needs_architect_review based on crew findings
        has_blocking = crew_results.get("has_blocking_issues", False)
        critical_count = len(crew_results.get("assessment", {}).get("critical_findings", []))
        high_count = len(crew_results.get("assessment", {}).get("high_findings", []))

        if has_blocking or critical_count > 0 or high_count > 2:
            self._needs_architect_review = True

        crew_review_result = {
            "available": True,
            "fallback": False,
            "findings": crew_results.get("findings", []),
            "finding_count": crew_results.get("finding_count", 0),
            "verdict": crew_results.get("verdict", "approve"),
            "quality_score": crew_results.get("quality_score", 100),
            "has_blocking_issues": has_blocking,
            "critical_count": critical_count,
            "high_count": high_count,
            "summary": crew_results.get("summary", ""),
            "agents_used": crew_results.get("agents_used", []),
            "memory_graph_hits": crew_results.get("memory_graph_hits", 0),
            "review_duration_seconds": crew_results.get("review_duration_seconds", 0),
        }

        # Estimate tokens (crew uses internal LLM calls)
        input_tokens = len(diff) // 4
        output_tokens = len(str(crew_review_result)) // 4

        return (
            {
                "crew_review": crew_review_result,
                "needs_architect_review": self._needs_architect_review,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _scan(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Security scan and bug pattern matching.

        When external_audit_results is provided in input_data (e.g., from
        SecurityAuditCrew), these findings are merged with the LLM analysis
        and can trigger architect_review if critical issues are found.
        """
        code_to_review = input_data.get("code_to_review", input_data.get("diff", ""))
        classification = input_data.get("classification", "")
        files_changed = input_data.get("files_changed", input_data.get("files", []))

        # Check for external audit results (e.g., from SecurityAuditCrew)
        external_audit = input_data.get("external_audit_results")

        system = """You are a security and code quality expert. Analyze the code for:

1. SECURITY ISSUES (OWASP Top 10):
   - SQL Injection, XSS, Command Injection
   - Hardcoded secrets, API keys, passwords
   - Insecure deserialization
   - Authentication/authorization flaws

2. BUG PATTERNS:
   - Null/undefined references
   - Resource leaks
   - Race conditions
   - Error handling issues

3. CODE QUALITY:
   - Code smells
   - Maintainability issues
   - Performance concerns

For each issue found, provide:
- Severity (critical/high/medium/low)
- Location (if identifiable)
- Description
- Recommendation

Be thorough but focused on actionable findings."""

        # If external audit provided, include it in the prompt for context
        external_context = ""
        if external_audit:
            external_summary = external_audit.get("summary", "")
            external_findings = external_audit.get("findings", [])
            if external_summary or external_findings:
                # Build findings list efficiently (avoid O(n²) string concat)
                finding_lines = []
                for finding in external_findings[:10]:  # Top 10
                    sev = finding.get("severity", "unknown").upper()
                    title = finding.get("title", "N/A")
                    desc = finding.get("description", "")[:100]
                    finding_lines.append(f"- [{sev}] {title}: {desc}")

                external_context = f"""

## External Security Audit Results
Summary: {external_summary}

Findings ({len(external_findings)} total):
{chr(10).join(finding_lines)}

Verify these findings and identify additional issues."""

        user_message = f"""Review this code for security and quality issues:

Previous classification: {classification}
{external_context}
Code to review:
{code_to_review[:6000]}"""

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=2048,
        )

        # Extract structured findings from LLM response
        llm_findings = self._extract_findings_from_response(
            response=response,
            files_changed=files_changed or [],
            code_context=code_to_review[:1000],  # First 1000 chars for context
        )

        # Check if critical issues found in LLM response
        has_critical = "critical" in response.lower() or "high" in response.lower()

        # Merge external audit findings if provided
        security_findings: list[dict] = []
        external_has_critical = False

        if external_audit:
            merged_response, security_findings, external_has_critical = self._merge_external_audit(
                response,
                external_audit,
            )
            response = merged_response
            has_critical = has_critical or external_has_critical

        # Combine LLM findings with security findings
        all_findings = llm_findings + security_findings

        # Calculate summary statistics
        summary: dict[str, Any] = {
            "total_findings": len(all_findings),
            "by_severity": {},
            "by_category": {},
            "files_affected": list({f.get("file", "") for f in all_findings if f.get("file")}),
        }

        # Count by severity
        for finding in all_findings:
            sev = finding.get("severity", "info")
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1

        # Count by category
        for finding in all_findings:
            cat = finding.get("category", "other")
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

        # Add helpful message if no findings
        if len(all_findings) == 0:
            summary["message"] = (
                "No security or quality issues found in scan. "
                "Code will proceed to architectural review."
            )

        # Calculate security score
        security_score = 70 if has_critical else 90

        # Determine preliminary verdict based on scan
        if has_critical:
            preliminary_verdict = "request_changes"
        elif security_score >= 90:
            preliminary_verdict = "approve"
        else:
            preliminary_verdict = "approve_with_suggestions"

        result = {
            "scan_results": response,
            "findings": all_findings,  # NEW: structured findings for UI
            "summary": summary,  # NEW: summary statistics
            "security_findings": security_findings,  # Keep for backward compat
            "bug_patterns": [],
            "quality_issues": [],
            "has_critical_issues": has_critical,
            "security_score": security_score,
            "verdict": preliminary_verdict,  # Add verdict for when architect_review is skipped
            "needs_architect_review": input_data.get("needs_architect_review", False)
            or has_critical,
            "code_to_review": code_to_review,
            "classification": classification,
            "external_audit_included": external_audit is not None,
            "external_audit_risk_score": (
                external_audit.get("risk_score", 0) if external_audit else 0
            ),
            "auth_mode_used": self._auth_mode_used,  # Track auth mode
            "model_tier_used": tier.value,  # Track model tier
        }

        # Generate formatted report (for when architect_review is skipped)
        formatted_report = format_code_review_report(result, input_data)
        result["formatted_report"] = formatted_report
        result["display_output"] = formatted_report

        return (result, input_tokens, output_tokens)

    def _merge_external_audit(
        self,
        llm_response: str,
        external_audit: dict,
    ) -> tuple[str, list, bool]:
        """Merge external SecurityAuditCrew results into scan output.

        Args:
            llm_response: Response from LLM security scan
            external_audit: External audit dict (from SecurityAuditCrew.to_dict())

        Returns:
            Tuple of (merged_response, security_findings, has_critical)

        """
        findings = external_audit.get("findings", [])
        summary = external_audit.get("summary", "")
        risk_score = external_audit.get("risk_score", 0)

        # Check for critical/high findings
        has_critical = any(f.get("severity") in ("critical", "high") for f in findings)

        # Build merged response
        merged_sections = [llm_response]

        if summary or findings:
            # Build crew section efficiently (avoid O(n²) string concat)
            parts = ["\n\n## SecurityAuditCrew Analysis\n"]
            if summary:
                parts.append(f"\n{summary}\n")

            parts.append(f"\n**Risk Score**: {risk_score}/100\n")

            if findings:
                critical = [f for f in findings if f.get("severity") == "critical"]
                high = [f for f in findings if f.get("severity") == "high"]

                if critical:
                    parts.append("\n### Critical Findings\n")
                    for f in critical:
                        title = f"- **{f.get('title', 'N/A')}**"
                        if f.get("file"):
                            title += f" ({f.get('file')}:{f.get('line', '?')})"
                        parts.append(title)
                        parts.append(f"\n  {f.get('description', '')[:200]}\n")
                        if f.get("remediation"):
                            parts.append(f"  *Fix*: {f.get('remediation')[:150]}\n")

                if high:
                    parts.append("\n### High Severity Findings\n")
                    for f in high[:5]:  # Top 5
                        title = f"- **{f.get('title', 'N/A')}**"
                        if f.get("file"):
                            title += f" ({f.get('file')}:{f.get('line', '?')})"
                        parts.append(title)
                        parts.append(f"\n  {f.get('description', '')[:150]}\n")

            merged_sections.append("".join(parts))

        return "\n".join(merged_sections), findings, has_critical

    async def _perf_check(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Scan reviewed files for performance anti-patterns.

        Reuses PERF_PATTERNS from the perf-audit workflow to provide
        performance baselines alongside every code review.

        Args:
            input_data: Must contain ``files_changed`` list of file paths.
            tier: Model tier (unused — pure static analysis).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        files_changed: list[str] = input_data.get("files_changed", [])
        findings: list[dict] = []

        for file_str in files_changed:
            file_path = Path(file_str)
            if not file_path.exists() or not file_path.is_file():
                continue
            if file_path.suffix != ".py":
                continue

            try:
                content = file_path.read_text(errors="ignore")
            except OSError as e:
                logger.debug(f"Cannot read {file_path} for perf check: {e}")
                continue

            for pattern_name, pattern_info in PERF_PATTERNS.items():
                for pattern in pattern_info["patterns"]:
                    for match in re.finditer(pattern, content, re.MULTILINE):
                        line_num = content[: match.start()].count("\n") + 1
                        findings.append(
                            {
                                "type": pattern_name,
                                "file": str(file_path),
                                "line": line_num,
                                "description": pattern_info["description"],
                                "impact": pattern_info["impact"],
                                "match": match.group()[:80],
                            }
                        )

        by_impact: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            by_impact[f.get("impact", "low")] = by_impact.get(f.get("impact", "low"), 0) + 1

        input_tokens = len(str(files_changed)) // CHARS_PER_TOKEN_ESTIMATE
        output_tokens = len(str(findings)) // CHARS_PER_TOKEN_ESTIMATE

        return (
            {
                "perf_findings": findings,
                "perf_finding_count": len(findings),
                "perf_by_impact": by_impact,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _perf_check_deep(
        self,
        input_data: dict,
        tier: ModelTier,
    ) -> tuple[dict, int, int]:
        """LLM-enriched validation of performance findings.

        Sends static perf_check findings to a CAPABLE-tier model to:
        - Filter false positives (e.g., test fixtures, intentional patterns)
        - Adjust severity based on context
        - Add actionable fix suggestions

        Only runs when perf_finding_count > 0 (gated by should_skip_stage).

        Args:
            input_data: Must contain ``perf_findings`` from _perf_check.
            tier: Model tier (CAPABLE).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        findings = input_data.get("perf_findings", [])
        if not findings:
            return ({**input_data}, 0, 0)

        # Gather code snippets for context
        snippets = _gather_file_snippets(findings)

        # Format findings for the prompt
        findings_text = _format_findings_for_prompt(findings, snippets)

        system = (
            "You are a performance analysis expert. You will receive a list of "
            "performance anti-pattern findings from static analysis, along with "
            "code snippets for context.\n\n"
            "For each finding, determine:\n"
            "1. Is it a TRUE positive or FALSE positive? (e.g., test fixtures, "
            "intentional patterns, or patterns that don't apply in context)\n"
            "2. What is the correct severity? (high/medium/low)\n"
            "3. What is a specific, actionable fix suggestion?\n\n"
            "Respond in JSON format:\n"
            '{"findings": [\n'
            '  {"index": 0, "validated": true, "false_positive": false, '
            '"severity": "medium", "suggestion": "Use generator expression instead"},\n'
            '  {"index": 1, "validated": true, "false_positive": true, '
            '"severity": "low", "suggestion": "Test fixture, safe to ignore"}\n'
            "]}\n\n"
            "IMPORTANT: Only mark as false_positive if you are highly confident. "
            "When uncertain, keep validated=true and false_positive=false."
        )

        user_message = f"Analyze these {len(findings)} performance findings:\n\n" f"{findings_text}"

        response, in_tokens, out_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=2048,
            stage_name="perf_check_deep",
        )

        # Parse and merge enrichment back into findings
        enriched = _parse_deep_enrichment(response, findings)
        by_impact = _recount_by_key(enriched, "impact")
        validated_count = sum(1 for f in enriched if not f.get("false_positive", False))

        return (
            {
                "perf_findings": enriched,
                "perf_finding_count": validated_count,
                "perf_by_impact": by_impact,
                "perf_deep_ran": True,
                **{
                    k: v
                    for k, v in input_data.items()
                    if k not in ("perf_findings", "perf_finding_count", "perf_by_impact")
                },
            },
            in_tokens,
            out_tokens,
        )

    async def _health_monitor(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Collect framework health metrics snapshot.

        Pulls data from existing singletons (CacheMonitor, CostTracker,
        UsageTracker) to provide proactive monitoring alongside every review.
        Each source is independently wrapped so a missing dependency never
        blocks the stage.

        Args:
            input_data: Current workflow data (passed through).
            tier: Model tier (unused — no LLM calls).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        health_snapshot: dict[str, Any] = {}

        # Cache metrics
        try:
            from attune.cache_monitor import CacheMonitor

            monitor = CacheMonitor.get_instance()
            all_stats = monitor.get_all_stats()
            health_snapshot["cache_stats"] = (
                {
                    name: stats.to_dict() if hasattr(stats, "to_dict") else str(stats)
                    for name, stats in all_stats.items()
                }
                if all_stats
                else {}
            )
        except ImportError:
            logger.debug("CacheMonitor not available for health snapshot")
            health_snapshot["cache_stats"] = {}

        # Cost metrics (today)
        try:
            from attune.cost_tracker import get_tracker

            tracker = get_tracker()
            health_snapshot["cost_today"] = tracker.get_today()
        except ImportError:
            logger.debug("CostTracker not available for health snapshot")
            health_snapshot["cost_today"] = {}

        # Usage telemetry (last 7 days)
        try:
            from attune.telemetry import UsageTracker

            usage = UsageTracker.get_instance()
            health_snapshot["usage_stats_7d"] = usage.get_stats(days=7)
        except ImportError:
            logger.debug("UsageTracker not available for health snapshot")
            health_snapshot["usage_stats_7d"] = {}

        input_tokens = 0
        output_tokens = len(str(health_snapshot)) // CHARS_PER_TOKEN_ESTIMATE

        return (
            {
                "health_snapshot": health_snapshot,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _quality_check(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Static code quality checks on reviewed files.

        Lightweight regex/line-based checks (no AST parsing):
        - Bare ``except:`` or ``except Exception:`` without ``# noqa``
        - TODO/FIXME comment counts
        - Files exceeding 500 lines (complexity warning)
        - Public functions missing return type hints

        Args:
            input_data: Must contain ``files_changed`` list of file paths.
            tier: Model tier (unused — pure static analysis).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        files_changed: list[str] = input_data.get("files_changed", [])
        findings: list[dict] = []

        bare_except_re = re.compile(r"^\s*except\s*(?:Exception)?\s*:", re.MULTILINE)
        noqa_re = re.compile(r"#\s*noqa")
        todo_re = re.compile(r"#\s*(TODO|FIXME)\b", re.IGNORECASE)
        public_func_re = re.compile(r"^def\s+([a-zA-Z][a-zA-Z0-9_]*)\s*\(", re.MULTILINE)

        for file_str in files_changed:
            file_path = Path(file_str)
            if not file_path.exists() or not file_path.is_file():
                continue
            if file_path.suffix != ".py":
                continue

            try:
                content = file_path.read_text(errors="ignore")
            except OSError as e:
                logger.debug(f"Cannot read {file_path} for quality check: {e}")
                continue

            lines = content.splitlines()

            # Check file length
            if len(lines) > MAX_FILE_LINES:
                findings.append(
                    {
                        "type": "long_file",
                        "file": str(file_path),
                        "line": None,
                        "description": f"File has {len(lines)} lines (>{MAX_FILE_LINES}), consider splitting",
                        "severity": "medium",
                    }
                )

            # Check for bare except
            for match in bare_except_re.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                line_text = lines[line_num - 1] if line_num <= len(lines) else ""
                if not noqa_re.search(line_text):
                    findings.append(
                        {
                            "type": "bare_except",
                            "file": str(file_path),
                            "line": line_num,
                            "description": "Bare except or broad except Exception without # noqa",
                            "severity": "high",
                        }
                    )

            # Count TODOs/FIXMEs
            todo_count = len(todo_re.findall(content))
            if todo_count > 0:
                findings.append(
                    {
                        "type": "todo_fixme",
                        "file": str(file_path),
                        "line": None,
                        "description": f"{todo_count} TODO/FIXME comment(s) found",
                        "severity": "low",
                    }
                )

            # Check public functions for return type hints
            for match in public_func_re.finditer(content):
                func_name = match.group(1)
                if func_name.startswith("_"):
                    continue  # Skip private functions
                if not _has_return_type_hint(content, match.start()):
                    line_num = content[: match.start()].count("\n") + 1
                    findings.append(
                        {
                            "type": "missing_type_hint",
                            "file": str(file_path),
                            "line": line_num,
                            "description": f"Public function '{func_name}' missing return type hint",
                            "severity": "medium",
                        }
                    )

        by_severity: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.get("severity", "low")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        input_tokens = len(str(files_changed)) // CHARS_PER_TOKEN_ESTIMATE
        output_tokens = len(str(findings)) // CHARS_PER_TOKEN_ESTIMATE

        return (
            {
                "quality_findings": findings,
                "quality_finding_count": len(findings),
                "quality_by_severity": by_severity,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _quality_check_deep(
        self,
        input_data: dict,
        tier: ModelTier,
    ) -> tuple[dict, int, int]:
        """LLM-enriched validation of quality findings.

        Sends static quality_check findings to a CAPABLE-tier model to:
        - Filter false positives (e.g., intentional broad catches with # INTENTIONAL:)
        - Distinguish informational TODOs from blocking issues
        - Add specific fix suggestions with code examples

        Only runs when quality_finding_count > 0 (gated by should_skip_stage).

        Args:
            input_data: Must contain ``quality_findings`` from _quality_check.
            tier: Model tier (CAPABLE).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        findings = input_data.get("quality_findings", [])
        if not findings:
            return ({**input_data}, 0, 0)

        # Gather code snippets for context
        snippets = _gather_file_snippets(findings)

        # Format findings for the prompt
        findings_text = _format_findings_for_prompt(findings, snippets)

        system = (
            "You are a code quality expert. You will receive a list of "
            "quality findings from static analysis, along with code snippets.\n\n"
            "For each finding, determine:\n"
            "1. Is it a TRUE positive or FALSE positive? Consider:\n"
            "   - `except Exception` with `# noqa: BLE001` or `# INTENTIONAL:` "
            "is acceptable\n"
            "   - TODO/FIXME in test files may be lower priority\n"
            "   - Long files may be justified (e.g., test files)\n"
            "2. What is the correct severity? (high/medium/low)\n"
            "3. What is a specific, actionable fix suggestion?\n\n"
            "Respond in JSON format:\n"
            '{"findings": [\n'
            '  {"index": 0, "validated": true, "false_positive": false, '
            '"severity": "high", "suggestion": "Add specific exception types"},\n'
            '  {"index": 1, "validated": true, "false_positive": true, '
            '"severity": "low", "suggestion": "Intentional broad catch with '
            '# INTENTIONAL: comment"}\n'
            "]}\n\n"
            "IMPORTANT: Only mark as false_positive if you are highly confident. "
            "When uncertain, keep validated=true and false_positive=false."
        )

        user_message = f"Analyze these {len(findings)} quality findings:\n\n" f"{findings_text}"

        response, in_tokens, out_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=2048,
            stage_name="quality_check_deep",
        )

        # Parse and merge enrichment back into findings
        enriched = _parse_deep_enrichment(response, findings)
        by_severity = _recount_by_key(enriched, "severity")
        validated_count = sum(1 for f in enriched if not f.get("false_positive", False))

        return (
            {
                "quality_findings": enriched,
                "quality_finding_count": validated_count,
                "quality_by_severity": by_severity,
                "quality_deep_ran": True,
                **{
                    k: v
                    for k, v in input_data.items()
                    if k
                    not in (
                        "quality_findings",
                        "quality_finding_count",
                        "quality_by_severity",
                    )
                },
            },
            in_tokens,
            out_tokens,
        )

    async def _architect_review(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Deep architectural review.

        Supports XML-enhanced prompts when enabled in workflow config.
        """
        code_to_review = input_data.get("code_to_review", "")
        scan_results = input_data.get("scan_results", "")
        classification = input_data.get("classification", "")

        # Build input payload
        input_payload = f"""Classification: {classification}

Security Scan Results:
{scan_results[:2000]}

Code:
{code_to_review[:4000]}"""

        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            from attune.prompts.examples import CODE_REVIEW_EXAMPLES

            user_message = self._render_xml_prompt(
                role="senior software architect",
                goal="Perform comprehensive code review with architectural assessment",
                instructions=[
                    "Assess design patterns used (or missing)",
                    "Evaluate SOLID principles compliance",
                    "Check separation of concerns",
                    "Analyze coupling and cohesion",
                    "Provide specific improvement recommendations with examples",
                    "Suggest refactoring and testing improvements",
                    "Provide verdict: approve, approve_with_suggestions, or reject",
                ],
                constraints=[
                    "Be specific and actionable",
                    "Reference file locations where possible",
                    "Prioritize issues by impact",
                ],
                input_type="code",
                input_payload=input_payload,
                examples=CODE_REVIEW_EXAMPLES,
            )
            system = None
        else:
            system = """You are a senior software architect. Provide a comprehensive review:

1. ARCHITECTURAL ASSESSMENT:
   - Design patterns used (or missing)
   - SOLID principles compliance
   - Separation of concerns
   - Coupling and cohesion

2. RECOMMENDATIONS:
   - Specific improvements with examples
   - Refactoring suggestions
   - Testing recommendations

3. VERDICT:
   - APPROVE: Code is production-ready
   - APPROVE_WITH_SUGGESTIONS: Minor improvements recommended
   - REQUEST_CHANGES: Issues must be addressed
   - REJECT: Fundamental problems

Provide actionable, specific feedback."""

            user_message = f"""Perform an architectural review:

{input_payload}"""

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = CODE_REVIEW_STEPS["architect_review"]
                response, input_tokens, output_tokens, cost = await self.run_step_with_executor(
                    step=step,
                    prompt=user_message,
                    system=system,
                )
            except Exception:
                # Fall back to legacy _call_llm if executor fails
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system or "",
                    user_message,
                    max_tokens=3000,
                )
        else:
            # Legacy path for backward compatibility
            response, input_tokens, output_tokens = await self._call_llm(
                tier,
                system or "",
                user_message,
                max_tokens=3000,
            )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        # Determine verdict from response or parsed data
        verdict = "approve_with_suggestions"
        if parsed_data.get("xml_parsed"):
            extra = parsed_data.get("_parsed_response")
            if extra and hasattr(extra, "extra"):
                parsed_verdict = extra.extra.get("verdict", "").lower()
                if parsed_verdict in [
                    "approve",
                    "approve_with_suggestions",
                    "request_changes",
                    "reject",
                ]:
                    verdict = parsed_verdict

        if verdict == "approve_with_suggestions":
            # Fall back to text parsing
            if "REQUEST_CHANGES" in response.upper() or "REJECT" in response.upper():
                verdict = "request_changes"
            elif "APPROVE" in response.upper() and "SUGGESTIONS" not in response.upper():
                verdict = "approve"

        result: dict = {
            "architectural_review": response,
            "verdict": verdict,
            "recommendations": [],
            "model_tier_used": tier.value,
            "auth_mode_used": self._auth_mode_used,
        }

        # Merge parsed XML data if available
        if parsed_data.get("xml_parsed"):
            result.update(
                {
                    "xml_parsed": True,
                    "summary": parsed_data.get("summary"),
                    "findings": parsed_data.get("findings", []),
                    "checklist": parsed_data.get("checklist", []),
                },
            )

        # Add formatted report for human readability
        formatted_report = format_code_review_report(result, input_data)
        result["formatted_report"] = formatted_report

        # Also add as top-level display_output for better UX
        result["display_output"] = formatted_report

        return (result, input_tokens, output_tokens)
