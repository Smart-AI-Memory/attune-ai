"""Performance Audit Workflow

Identifies performance bottlenecks and optimization opportunities
through static analysis.

Stages:
1. profile (CHEAP) - Static analysis for common perf anti-patterns
2. analyze (CAPABLE) - Deep analysis of algorithmic complexity
3. hotspots (CAPABLE) - Identify performance hotspots
4. optimize (PREMIUM) - Generate optimization recommendations (conditional)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import heapq
import json
import re
from pathlib import Path
from typing import Any

from .base import BaseWorkflow, ModelTier
from .context import WorkflowContext
from .output import Finding, WorkflowReport, get_console
from .services import ParsingService, PromptService
from .step_config import WorkflowStepConfig

# Define step configurations for executor-based execution
PERF_AUDIT_STEPS = {
    "optimize": WorkflowStepConfig(
        name="optimize",
        task_type="final_review",  # Premium tier task
        tier_hint="premium",
        description="Generate performance optimization recommendations",
        max_tokens=3000,
    ),
}

# Performance anti-patterns to detect
PERF_PATTERNS = {
    "n_plus_one": {
        "patterns": [
            r"for\s+\w+\s+in\s+\w+:.*?\.get\(",
            r"for\s+\w+\s+in\s+\w+:.*?\.query\(",
            r"for\s+\w+\s+in\s+\w+:.*?\.fetch\(",
        ],
        "description": "Potential N+1 query pattern",
        "impact": "high",
    },
    "sync_in_async": {
        "patterns": [
            r"async\s+def.*?time\.sleep\(",
            r"async\s+def.*?requests\.get\(",
            r"async\s+def.*?open\([^)]+\)\.read\(",
        ],
        "description": "Synchronous operation in async context",
        "impact": "high",
    },
    "list_comprehension_in_loop": {
        "patterns": [
            r"for\s+\w+\s+in\s+\[.*for.*\]:",
        ],
        "description": "List comprehension recreated in loop",
        "impact": "medium",
    },
    "string_concat_loop": {
        "patterns": [
            # Match: for x in y: \n    str += "..." (actual loop, not generator expression)
            # Exclude: any(... for x in ...) by requiring standalone for statement
            r'^[ \t]*for\s+\w+\s+in\s+[^:]+:\s*\n[ \t]+\w+\s*\+=\s*["\']',
        ],
        "description": "String concatenation in loop (use join)",
        "impact": "medium",
    },
    "global_import": {
        "patterns": [
            r"^from\s+\w+\s+import\s+\*",
        ],
        "description": "Wildcard import may slow startup",
        "impact": "low",
    },
    # REMOVED: large_list_copy - too many false positives
    # - list(x) is often intentional defensive copying or type conversion
    # - dirs[:] is REQUIRED for os.walk directory filtering (see os-walk-dirs-pattern.md)
    # - Low impact even when not intentional
    # See: .claude/rules/attune/list-copy-guidelines.md
    "repeated_regex": {
        "patterns": [
            r're\.(search|match|findall)\s*\(["\'][^"\']+["\']',
        ],
        "description": "Regex pattern not pre-compiled",
        "impact": "medium",
    },
    "nested_loops": {
        "patterns": [
            r"for\s+\w+\s+in\s+\w+:\s*\n\s+for\s+\w+\s+in\s+\w+:\s*\n\s+for",
        ],
        "description": "Triple nested loop (O(n³) complexity)",
        "impact": "high",
    },
}

# Known false positives - patterns that match but aren't performance issues
# These are documented for transparency; the regex-based detection has limitations.
#
# IMPROVED: string_concat_loop
#   - Pattern now requires line to START with 'for' (excludes generator expressions)
#   - Previously matched: any(x for x in y) followed by += on next line
#   - Now correctly excludes: generator expressions inside any(), all(), etc.
#   - Sequential string building (code += "line1"; code += "line2") correctly ignored
#
# REMOVED: large_list_copy (v2.1.0)
#   - list(x) or x[:] used for defensive copying or type conversion
#   - dirs[:] is REQUIRED for os.walk directory filtering
#   - Often intentional to avoid mutating original data
#   - Verdict: REMOVED - too many false positives, low impact even when real
#   - See: .claude/rules/attune/list-copy-guidelines.md
#   - See: .claude/rules/attune/os-walk-dirs-pattern.md
#
# FALSE POSITIVE: repeated_regex (edge cases)
#   - Single-use regex in rarely-called functions
#   - Verdict: OK - pre-compilation only matters for hot paths


class PerformanceAuditWorkflow(BaseWorkflow):
    """Identify performance bottlenecks and optimization opportunities.

    Uses static analysis to find common performance anti-patterns
    and algorithmic complexity issues.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.
    """

    name = "perf-audit"
    description = "Identify performance bottlenecks and optimization opportunities"
    stages = ["profile", "analyze", "hotspots", "optimize"]
    tier_map = {
        "profile": ModelTier.CHEAP,
        "analyze": ModelTier.CAPABLE,
        "hotspots": ModelTier.CAPABLE,
        "optimize": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        min_hotspots_for_premium: int = 3,
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize performance audit workflow.

        Args:
            min_hotspots_for_premium: Minimum hotspots to trigger premium optimization
            enable_auth_strategy: Enable intelligent auth routing (default: True)
            **kwargs: Additional arguments passed to BaseWorkflow

        """
        super().__init__(**kwargs)
        self.min_hotspots_for_premium = min_hotspots_for_premium
        self.enable_auth_strategy = enable_auth_strategy
        self._hotspot_count: int = 0
        self._auth_mode_used: str | None = None

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for performance auditing.

        Args:
            xml_config: Optional XML prompt configuration dict.
                Defaults to XML disabled — benchmarks on Claude 4.x show
                +30% cost overhead with no quality improvement for perf audit.

        Returns:
            WorkflowContext with prompt and parsing services.
        """
        if xml_config is None:
            xml_config = {"enabled": False}
        return WorkflowContext(
            prompt=PromptService("perf-audit", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Downgrade optimize stage if few hotspots.

        Args:
            stage_name: Name of the stage to check
            input_data: Current workflow data

        Returns:
            Tuple of (should_skip, reason)

        """
        if stage_name == "optimize":
            if self._hotspot_count < self.min_hotspots_for_premium:
                self.tier_map["optimize"] = ModelTier.CAPABLE
                return False, None
        return False, None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to specific stage implementation."""
        if stage_name == "profile":
            return await self._profile(input_data, tier)
        if stage_name == "analyze":
            return await self._analyze(input_data, tier)
        if stage_name == "hotspots":
            return await self._hotspots(input_data, tier)
        if stage_name == "optimize":
            return await self._optimize(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _profile(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Static analysis for common performance anti-patterns.

        Scans code for known performance issues.
        """
        target_path = input_data.get("path", ".")
        file_types = input_data.get("file_types", [".py"])

        findings: list[dict] = []
        files_scanned = 0

        target = Path(target_path)

        # === AUTH STRATEGY INTEGRATION ===
        if self.enable_auth_strategy:
            try:
                import logging

                from attune.models import (
                    count_lines_of_code,
                    get_auth_strategy,
                    get_module_size_category,
                )

                logger = logging.getLogger(__name__)

                # Calculate total LOC for the project/path
                total_lines = 0
                if target.is_file():
                    total_lines = count_lines_of_code(target)
                elif target.is_dir():
                    # Estimate total lines for directory
                    for ext in file_types:
                        for file_path in target.rglob(f"*{ext}"):
                            if any(
                                skip in str(file_path)
                                for skip in [".git", "node_modules", "__pycache__", "venv", "test"]
                            ):
                                continue
                            try:
                                total_lines += count_lines_of_code(file_path)
                            except Exception:
                                pass

                if total_lines > 0:
                    strategy = get_auth_strategy()
                    recommended_mode = strategy.get_recommended_mode(total_lines)
                    self._auth_mode_used = recommended_mode.value

                    size_category = get_module_size_category(total_lines)
                    logger.info(
                        f"Performance audit target: {target_path} "
                        f"({total_lines:,} LOC, {size_category})"
                    )
                    logger.info(f"Recommended auth mode: {recommended_mode.value}")

                    cost_estimate = strategy.estimate_cost(total_lines, recommended_mode)
                    if recommended_mode.value == "subscription":
                        logger.info(
                            f"Cost estimate: ~${cost_estimate:.4f} "
                            "(significantly cheaper with subscription)"
                        )
                    else:
                        logger.info(f"Cost estimate: ~${cost_estimate:.4f} (API-based)")

            except ImportError as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Auth strategy not available: {e}")
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Auth strategy detection failed: {e}")
        # === END AUTH STRATEGY INTEGRATION ===
        if target.exists():
            for ext in file_types:
                for file_path in target.rglob(f"*{ext}"):
                    if any(
                        skip in str(file_path)
                        for skip in [".git", "node_modules", "__pycache__", "venv", "test"]
                    ):
                        continue

                    try:
                        content = file_path.read_text(errors="ignore")
                        files_scanned += 1

                        for pattern_name, pattern_info in PERF_PATTERNS.items():
                            for pattern in pattern_info["patterns"]:
                                matches = list(re.finditer(pattern, content, re.MULTILINE))
                                for match in matches:
                                    line_num = content[: match.start()].count("\n") + 1
                                    findings.append(
                                        {
                                            "type": pattern_name,
                                            "file": str(file_path),
                                            "line": line_num,
                                            "description": pattern_info["description"],
                                            "impact": pattern_info["impact"],
                                            "match": match.group()[:80],
                                        },
                                    )
                    except OSError:
                        continue

        # Group by impact
        by_impact: dict[str, list] = {"high": [], "medium": [], "low": []}
        for f in findings:
            impact = f.get("impact", "low")
            by_impact[impact].append(f)

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(findings)) // 4

        return (
            {
                "findings": findings,
                "finding_count": len(findings),
                "files_scanned": files_scanned,
                "by_impact": {k: len(v) for k, v in by_impact.items()},
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _analyze(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Deep analysis of algorithmic complexity.

        Examines code structure for complexity issues.
        """
        findings = input_data.get("findings", [])

        # Group findings by file
        by_file: dict[str, list] = {}
        for f in findings:
            file_path = f.get("file", "")
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(f)

        # Analyze each file
        analysis: list[dict] = []
        for file_path, file_findings in by_file.items():
            # Calculate file complexity score (generator expressions for memory efficiency)
            high_count = sum(1 for f in file_findings if f["impact"] == "high")
            medium_count = sum(1 for f in file_findings if f["impact"] == "medium")
            low_count = sum(1 for f in file_findings if f["impact"] == "low")

            complexity_score = high_count * 10 + medium_count * 5 + low_count * 1

            # Identify primary concerns
            concerns = list({f["type"] for f in file_findings})

            analysis.append(
                {
                    "file": file_path,
                    "complexity_score": complexity_score,
                    "finding_count": len(file_findings),
                    "high_impact": high_count,
                    "concerns": concerns[:5],
                },
            )

        # Sort by complexity score
        analysis.sort(key=lambda x: -x["complexity_score"])

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(analysis)) // 4

        return (
            {
                "analysis": analysis,
                "analyzed_files": len(analysis),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _hotspots(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Identify performance hotspots.

        Pinpoints files and areas requiring immediate attention.
        """
        analysis = input_data.get("analysis", [])

        # Top hotspots (highest complexity scores)
        hotspots = [a for a in analysis if a["complexity_score"] >= 10 or a["high_impact"] >= 2]

        self._hotspot_count = len(hotspots)

        # Categorize hotspots
        critical = [h for h in hotspots if h["complexity_score"] >= 20]
        moderate = [h for h in hotspots if 10 <= h["complexity_score"] < 20]

        # Calculate overall perf score (inverse of problems)
        total_score = sum(a["complexity_score"] for a in analysis)
        max_score = len(analysis) * 30  # Max possible score
        perf_score = max(0, 100 - int((total_score / max(max_score, 1)) * 100))

        hotspot_result = {
            "hotspots": hotspots[:15],  # Top 15
            "hotspot_count": self._hotspot_count,
            "critical_count": len(critical),
            "moderate_count": len(moderate),
            "perf_score": perf_score,
            "perf_level": (
                "critical" if perf_score < 50 else "warning" if perf_score < 75 else "good"
            ),
        }

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(hotspot_result)) // 4

        return (
            {
                "hotspot_result": hotspot_result,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _optimize(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate optimization recommendations using LLM.

        Creates actionable recommendations for performance improvements.

        Supports XML-enhanced prompts when enabled in workflow config.
        """
        hotspot_result = input_data.get("hotspot_result", {})
        hotspots = hotspot_result.get("hotspots", [])
        findings = input_data.get("findings", [])
        target = input_data.get("target", "")

        # Build hotspots summary for LLM
        hotspots_summary = []
        for h in hotspots[:10]:
            hotspots_summary.append(
                f"- {h.get('file')}: score={h.get('complexity_score', 0)}, "
                f"concerns={', '.join(h.get('concerns', []))}",
            )

        # Summary of most common issues
        issue_counts: dict[str, int] = {}
        for f in findings:
            t = f.get("type", "unknown")
            issue_counts[t] = issue_counts.get(t, 0) + 1
        top_issues = heapq.nlargest(5, issue_counts.items(), key=lambda x: x[1])

        # Build input payload for prompt
        input_payload = f"""Target: {target or "codebase"}

Performance Score: {hotspot_result.get("perf_score", 0)}/100
Performance Level: {hotspot_result.get("perf_level", "unknown")}

Hotspots:
{chr(10).join(hotspots_summary) if hotspots_summary else "No hotspots identified"}

Top Issues:
{json.dumps([{"type": t, "count": c} for t, c in top_issues], indent=2)}"""

        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            # Use XML-enhanced prompt
            from attune.prompts.examples import PERF_AUDIT_EXAMPLES

            user_message = self._render_xml_prompt(
                role="performance engineer specializing in optimization",
                goal="Generate comprehensive optimization recommendations for performance issues",
                instructions=[
                    "Analyze each performance hotspot and its concerns",
                    "Provide specific optimization strategies with code examples",
                    "Estimate the impact of each optimization (high/medium/low)",
                    "Prioritize recommendations by potential performance gain",
                    "Include before/after code patterns where helpful",
                ],
                constraints=[
                    "Be specific about which files and patterns to optimize",
                    "Include actionable code changes",
                    "Focus on high-impact optimizations first",
                ],
                input_type="performance_hotspots",
                input_payload=input_payload,
                examples=PERF_AUDIT_EXAMPLES,
                extra={
                    "perf_score": hotspot_result.get("perf_score", 0),
                    "hotspot_count": len(hotspots),
                },
            )
            system = None  # XML prompt includes all context
        else:
            # Use legacy plain text prompts
            system = """You are a performance engineer specializing in code optimization.
Analyze the identified performance hotspots and generate actionable recommendations.

For each hotspot:
1. Explain why the pattern causes performance issues
2. Provide specific optimization strategies with code examples
3. Estimate the impact of the optimization

Prioritize by potential performance gain."""

            user_message = f"""Generate optimization recommendations for these performance issues:

{input_payload}

Provide detailed optimization strategies."""

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = PERF_AUDIT_STEPS["optimize"]
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

        result = {
            "optimization_plan": response,
            "recommendation_count": len(hotspots),
            "top_issues": [{"type": t, "count": c} for t, c in top_issues],
            "perf_score": hotspot_result.get("perf_score", 0),
            "perf_level": hotspot_result.get("perf_level", "unknown"),
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
        result["formatted_report"] = format_perf_audit_report(result, input_data)

        # Add structured WorkflowReport for Rich rendering
        result["workflow_report"] = create_perf_audit_workflow_report(result, input_data)

        return (result, input_tokens, output_tokens)

    def _get_optimization_action(self, concern: str) -> dict | None:
        """Generate specific optimization action for a concern type."""
        actions = {
            "n_plus_one": {
                "action": "Batch database queries",
                "description": "Use prefetch_related/select_related or batch queries",
                "estimated_impact": "high",
            },
            "sync_in_async": {
                "action": "Use async alternatives",
                "description": "Replace sync operations with async versions",
                "estimated_impact": "high",
            },
            "string_concat_loop": {
                "action": "Use str.join()",
                "description": "Build list of strings and join at the end instead of concatenating",
                "estimated_impact": "medium",
            },
            "repeated_regex": {
                "action": "Pre-compile regex",
                "description": "Use re.compile() and reuse the compiled pattern",
                "estimated_impact": "medium",
            },
            "nested_loops": {
                "action": "Optimize algorithm",
                "description": "Consider using sets, dicts, or itertools to reduce complexity",
                "estimated_impact": "high",
            },
            "list_comprehension_in_loop": {
                "action": "Move comprehension outside loop",
                "description": "Create the list once before the loop",
                "estimated_impact": "medium",
            },
            # large_list_copy removed - too many false positives
            "global_import": {
                "action": "Use specific imports",
                "description": "Import only needed names to reduce memory and startup time",
                "estimated_impact": "low",
            },
        }
        return actions.get(concern)


def create_perf_audit_workflow_report(result: dict, input_data: dict) -> WorkflowReport:
    """Create a WorkflowReport from performance audit results.

    Args:
        result: The optimize stage result
        input_data: Input data from previous stages

    Returns:
        WorkflowReport instance for Rich or plain text rendering
    """
    perf_score = result.get("perf_score", 0)
    perf_level = result.get("perf_level", "unknown")

    # Determine report level
    if perf_score >= 85:
        level = "success"
    elif perf_score >= 50:
        level = "warning"
    else:
        level = "error"

    # Build summary
    files_scanned = input_data.get("files_scanned", 0)
    finding_count = input_data.get("finding_count", 0)
    by_impact = input_data.get("by_impact", {})

    summary = (
        f"Scanned {files_scanned} files, found {finding_count} issues. "
        f"High: {by_impact.get('high', 0)}, Medium: {by_impact.get('medium', 0)}, "
        f"Low: {by_impact.get('low', 0)}"
    )

    report = WorkflowReport(
        title="Performance Audit Report",
        summary=summary,
        score=perf_score,
        level=level,
        metadata={
            "perf_level": perf_level,
            "files_scanned": files_scanned,
            "finding_count": finding_count,
        },
    )

    # Add top issues section
    top_issues = result.get("top_issues", [])
    if top_issues:
        issues_content = {
            issue.get("type", "unknown")
            .replace("_", " ")
            .title(): f"{issue.get('count', 0)} occurrences"
            for issue in top_issues
        }
        report.add_section("Top Performance Issues", issues_content)

    # Add hotspots section
    hotspot_result = input_data.get("hotspot_result", {})
    hotspots = hotspot_result.get("hotspots", [])
    if hotspots:
        hotspot_content = {
            "Critical Hotspots": hotspot_result.get("critical_count", 0),
            "Moderate Hotspots": hotspot_result.get("moderate_count", 0),
        }
        report.add_section("Hotspot Summary", hotspot_content)

    # Add findings section
    findings = input_data.get("findings", [])
    high_impact = [f for f in findings if f.get("impact") == "high"]
    if high_impact:
        finding_objs = [
            Finding(
                severity="high",
                file=f.get("file", "unknown"),
                line=f.get("line"),
                message=f.get("description", ""),
            )
            for f in high_impact[:10]
        ]
        report.add_section("High Impact Findings", finding_objs, style="error")

    # Add recommendations section
    optimization_plan = result.get("optimization_plan", "")
    if optimization_plan:
        report.add_section("Optimization Recommendations", optimization_plan)

    return report


def format_perf_audit_report(result: dict, input_data: dict) -> str:
    """Format performance audit output as a human-readable report.

    Args:
        result: The optimize stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string

    """
    lines = []

    # Header with performance score
    perf_score = result.get("perf_score", 0)
    perf_level = result.get("perf_level", "unknown").upper()

    if perf_score >= 85:
        perf_icon = "🟢"
        perf_text = "EXCELLENT"
    elif perf_score >= 75:
        perf_icon = "🟡"
        perf_text = "GOOD"
    elif perf_score >= 50:
        perf_icon = "🟠"
        perf_text = "NEEDS OPTIMIZATION"
    else:
        perf_icon = "🔴"
        perf_text = "CRITICAL"

    lines.append("=" * 60)
    lines.append("PERFORMANCE AUDIT REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Performance Score: {perf_icon} {perf_score}/100 ({perf_text})")
    lines.append(f"Performance Level: {perf_level}")
    lines.append("")

    # Scan summary
    files_scanned = input_data.get("files_scanned", 0)
    finding_count = input_data.get("finding_count", 0)
    by_impact = input_data.get("by_impact", {})

    lines.append("-" * 60)
    lines.append("SCAN SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Files Scanned: {files_scanned}")
    lines.append(f"Issues Found: {finding_count}")
    lines.append("")
    lines.append("Issues by Impact:")
    lines.append(f"  🔴 High: {by_impact.get('high', 0)}")
    lines.append(f"  🟡 Medium: {by_impact.get('medium', 0)}")
    lines.append(f"  🟢 Low: {by_impact.get('low', 0)}")
    lines.append("")

    # Top issues
    top_issues = result.get("top_issues", [])
    if top_issues:
        lines.append("-" * 60)
        lines.append("TOP PERFORMANCE ISSUES")
        lines.append("-" * 60)
        for issue in top_issues:
            issue_type = issue.get("type", "unknown").replace("_", " ").title()
            count = issue.get("count", 0)
            lines.append(f"  • {issue_type}: {count} occurrences")
        lines.append("")

    # Hotspots
    hotspot_result = input_data.get("hotspot_result", {})
    hotspots = hotspot_result.get("hotspots", [])
    if hotspots:
        lines.append("-" * 60)
        lines.append("PERFORMANCE HOTSPOTS")
        lines.append("-" * 60)
        lines.append(f"Critical Hotspots: {hotspot_result.get('critical_count', 0)}")
        lines.append(f"Moderate Hotspots: {hotspot_result.get('moderate_count', 0)}")
        lines.append("")
        for h in hotspots[:8]:
            file_path = h.get("file", "unknown")
            score = h.get("complexity_score", 0)
            concerns = h.get("concerns", [])
            score_icon = "🔴" if score >= 20 else "🟠" if score >= 10 else "🟡"
            lines.append(f"  {score_icon} {file_path}")
            lines.append(f"      Score: {score} | Concerns: {', '.join(concerns[:3])}")
        lines.append("")

    # High impact findings
    findings = input_data.get("findings", [])
    high_impact = [f for f in findings if f.get("impact") == "high"]
    if high_impact:
        lines.append("-" * 60)
        lines.append("HIGH IMPACT FINDINGS")
        lines.append("-" * 60)
        for f in high_impact[:10]:
            file_path = f.get("file", "unknown")
            line = f.get("line", "?")
            desc = f.get("description", "Unknown issue")
            lines.append(f"  🔴 {file_path}:{line}")
            lines.append(f"      {desc}")
        lines.append("")

    # Optimization recommendations
    optimization_plan = result.get("optimization_plan", "")
    if optimization_plan:
        lines.append("-" * 60)
        lines.append("OPTIMIZATION RECOMMENDATIONS")
        lines.append("-" * 60)
        lines.append(optimization_plan)
        lines.append("")

    # Footer
    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    rec_count = result.get("recommendation_count", 0)
    lines.append(f"Analyzed {rec_count} hotspots using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    """CLI entry point for performance audit workflow."""
    import asyncio

    async def run():
        workflow = PerformanceAuditWorkflow()
        result = await workflow.execute(path=".", file_types=[".py"])

        output = result.final_output

        # Try Rich output first
        console = get_console()
        workflow_report = output.get("workflow_report")

        if console and workflow_report:
            # Render with Rich
            workflow_report.render(console, use_rich=True)
            console.print()
            console.print(f"[dim]Provider: {result.provider}[/dim]")
            console.print(f"[dim]Cost: ${result.cost_report.total_cost:.4f}[/dim]")
            savings = result.cost_report.savings
            pct = result.cost_report.savings_percent
            console.print(f"[dim]Savings: ${savings:.4f} ({pct:.1f}%)[/dim]")
        else:
            # Fallback to plain text
            print("\nPerformance Audit Results")
            print("=" * 50)
            print(f"Provider: {result.provider}")
            print(f"Success: {result.success}")

            print(f"Performance Level: {output.get('perf_level', 'N/A')}")
            print(f"Performance Score: {output.get('perf_score', 0)}/100")
            print(f"Recommendations: {output.get('recommendation_count', 0)}")

            if output.get("top_issues"):
                print("\nTop Issues:")
                for issue in output["top_issues"]:
                    print(f"  - {issue['type']}: {issue['count']} occurrences")

            print("\nCost Report:")
            print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
            savings = result.cost_report.savings
            pct = result.cost_report.savings_percent
            print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())


if __name__ == "__main__":
    main()
