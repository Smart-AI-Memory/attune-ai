"""Bug Prediction Workflow

Analyzes code against learned bug patterns to predict likely issues
before they manifest in production.

Stages:
1. scan (CHEAP) - Scan codebase for code patterns and structures
2. correlate (CAPABLE) - Match against historical bug patterns
3. predict (CAPABLE) - Identify high-risk areas based on correlation
4. recommend (PREMIUM) - Generate actionable fix recommendations

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
from pathlib import Path
from typing import Any

from .base import BaseWorkflow, ModelTier, estimate_tokens

# Re-export extracted modules for backward compatibility
from .bug_predict_patterns import (  # noqa: F401
    _has_problematic_exception_handlers,
    _is_acceptable_broad_exception,
    _is_dangerous_eval_usage,
    _is_security_policy_line,
    _load_bug_predict_config,
    _remove_docstrings,
    _should_exclude_file,
)
from .bug_predict_report import (
    format_bug_predict_report,
    main,
)
from .context import WorkflowContext
from .services import ParsingService, PromptService
from .step_config import WorkflowStepConfig

logger = logging.getLogger(__name__)


# Define step configurations for executor-based execution
BUG_PREDICT_STEPS = {
    "recommend": WorkflowStepConfig(
        name="recommend",
        task_type="final_review",  # Premium tier task
        tier_hint="premium",
        description="Generate bug prevention recommendations",
        max_tokens=2000,
    ),
}


class BugPredictionWorkflow(BaseWorkflow):
    """Predict bugs by correlating current code with learned patterns.

    Uses pattern library integration to identify code that matches
    historical bug patterns and generates preventive recommendations.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.
    """

    name = "bug-predict"
    description = "Predict bugs by analyzing code against learned patterns"
    stages = ["scan", "correlate", "predict", "recommend"]
    tier_map = {
        "scan": ModelTier.CHEAP,
        "correlate": ModelTier.CAPABLE,
        "predict": ModelTier.CAPABLE,
        "recommend": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        risk_threshold: float | None = None,
        patterns_dir: str = "./patterns",
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize bug prediction workflow.

        Args:
            risk_threshold: Minimum risk score to trigger premium recommendations
                           (defaults to config value or 0.7)
            patterns_dir: Directory containing learned patterns
            enable_auth_strategy: If True, use intelligent subscription vs API routing
                based on codebase size (default True)
            **kwargs: Additional arguments passed to BaseWorkflow

        """
        super().__init__(**kwargs)

        # Create instance-level tier_map to prevent class-level mutation
        self.tier_map = {
            "scan": ModelTier.CHEAP,
            "correlate": ModelTier.CAPABLE,
            "predict": ModelTier.CAPABLE,
            "recommend": ModelTier.PREMIUM,
        }

        # Load bug_predict config from attune.config.yml
        self._bug_predict_config = _load_bug_predict_config()

        # Use provided risk_threshold or fall back to config
        self.risk_threshold = (
            risk_threshold
            if risk_threshold is not None
            else self._bug_predict_config["risk_threshold"]
        )
        self.patterns_dir = patterns_dir
        self.enable_auth_strategy = enable_auth_strategy
        self._risk_score: float = 0.0
        self._bug_patterns: list[dict] = []
        self._auth_mode_used: str | None = None  # Track which auth was recommended
        self._load_patterns()

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for bug prediction.

        Args:
            xml_config: Optional XML prompt configuration dict.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        return WorkflowContext(
            prompt=PromptService("bug-predict", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def _load_patterns(self) -> None:
        """Load bug patterns from the pattern library."""
        debugging_file = Path(self.patterns_dir) / "debugging.json"
        if debugging_file.exists():
            try:
                with open(debugging_file) as f:
                    data = json.load(f)
                    self._bug_patterns = data.get("patterns", [])
            except (json.JSONDecodeError, OSError):
                self._bug_patterns = []

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Conditionally downgrade recommend stage based on risk score.

        Args:
            stage_name: Name of the stage to check
            input_data: Current workflow data

        Returns:
            Tuple of (should_skip, reason)

        """
        if stage_name == "recommend":
            if self._risk_score < self.risk_threshold:
                # Downgrade to CAPABLE instead of skipping
                self.tier_map["recommend"] = ModelTier.CAPABLE
                return False, None
        return False, None

    async def _scan(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Scan codebase for code patterns and structures.

        In production, this would analyze source files for patterns
        that historically correlate with bugs.
        """
        target_path = input_data.get("path", ".")
        file_types = input_data.get("file_types", [".py", ".ts", ".tsx", ".js"])

        # Simulate scanning for code patterns
        scanned_files: list[dict] = []
        patterns_found: list[dict] = []

        # Directories to exclude from scanning (dependencies, build artifacts, etc.)
        exclude_dirs = [
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "env",
            "__pycache__",
            "site-packages",
            "dist",
            "build",
            ".tox",
            ".nox",
            ".eggs",
            "*.egg-info",
        ]

        # Get config options
        config_exclude_patterns = self._bug_predict_config.get("exclude_files", [])
        acceptable_contexts = self._bug_predict_config.get("acceptable_exception_contexts", None)

        # === AUTH STRATEGY INTEGRATION ===
        # Detect codebase size and recommend auth mode (first stage only)
        if self.enable_auth_strategy:
            try:
                from attune.models import (
                    count_lines_of_code,
                    get_auth_strategy,
                    get_module_size_category,
                )

                # Calculate codebase size
                codebase_lines = 0
                target = Path(target_path)
                if target.exists():
                    codebase_lines = count_lines_of_code(str(target))

                # Get auth strategy and recommendation
                strategy = get_auth_strategy()
                if strategy:
                    # Get recommended auth mode
                    recommended_mode = strategy.get_recommended_mode(codebase_lines)
                    self._auth_mode_used = recommended_mode.value

                    # Get size category
                    size_category = get_module_size_category(codebase_lines)

                    # Log recommendation
                    logger.info(
                        "Auth Strategy: %s codebase (%s lines) -> %s",
                        size_category.value,
                        codebase_lines,
                        recommended_mode.value,
                    )
            except ImportError:
                # Auth strategy module not available - continue without it
                logger.debug("Auth strategy module not available")
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Auth strategy is optional; don't fail the workflow
                logger.warning("Auth strategy detection failed: %s", e)
        # === END AUTH STRATEGY ===/

        # Walk directory and collect file info
        target = Path(target_path)
        if target.exists():
            for ext in file_types:
                for file_path in target.rglob(f"*{ext}"):
                    # Skip excluded directories
                    path_str = str(file_path)
                    if any(excl in path_str for excl in exclude_dirs):
                        continue

                    # Skip files matching config exclude patterns
                    if _should_exclude_file(path_str, config_exclude_patterns):
                        continue

                    try:
                        content = file_path.read_text(errors="ignore")
                        scanned_files.append(
                            {
                                "path": str(file_path),
                                "lines": len(content.splitlines()),
                                "size": len(content),
                            },
                        )

                        # Look for common bug-prone patterns
                        # Use smart detection with configurable acceptable contexts
                        if _has_problematic_exception_handlers(
                            content,
                            str(file_path),
                            acceptable_contexts,
                        ):
                            patterns_found.append(
                                {
                                    "file": str(file_path),
                                    "pattern": "broad_exception",
                                    "severity": "medium",
                                },
                            )
                        if "# TODO" in content or "# FIXME" in content:
                            patterns_found.append(
                                {
                                    "file": str(file_path),
                                    "pattern": "incomplete_code",
                                    "severity": "low",
                                },
                            )
                        # Use smart detection to filter false positives
                        if _is_dangerous_eval_usage(content, str(file_path)):
                            patterns_found.append(
                                {
                                    "file": str(file_path),
                                    "pattern": "dangerous_eval",
                                    "severity": "high",
                                },
                            )
                    except OSError:
                        continue

        input_tokens = estimate_tokens(input_data)
        output_tokens = estimate_tokens(scanned_files) + estimate_tokens(patterns_found)

        return (
            {
                "scanned_files": scanned_files[:100],  # Limit for efficiency
                "patterns_found": patterns_found,
                "file_count": len(scanned_files),
                "pattern_count": len(patterns_found),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _correlate(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Match current code patterns against historical bug patterns.

        Correlates findings from scan stage with patterns stored in
        the debugging.json pattern library.
        """
        patterns_found = input_data.get("patterns_found", [])
        correlations: list[dict] = []

        # Match against known bug patterns
        for pattern in patterns_found:
            pattern_type = pattern.get("pattern", "")

            # Check against historical patterns
            for bug_pattern in self._bug_patterns:
                bug_type = bug_pattern.get("bug_type", "")
                if self._patterns_correlate(pattern_type, bug_type):
                    correlations.append(
                        {
                            "current_pattern": pattern,
                            "historical_bug": {
                                "type": bug_type,
                                "root_cause": bug_pattern.get("root_cause", ""),
                                "fix": bug_pattern.get("fix", ""),
                            },
                            "confidence": 0.75,
                        },
                    )

        # Add correlations for patterns without direct matches
        for pattern in patterns_found:
            if not any(c["current_pattern"] == pattern for c in correlations):
                correlations.append(
                    {
                        "current_pattern": pattern,
                        "historical_bug": None,
                        "confidence": 0.3,
                    },
                )

        input_tokens = estimate_tokens(input_data)
        output_tokens = estimate_tokens(correlations)

        return (
            {
                "correlations": correlations,
                "correlation_count": len(correlations),
                "high_confidence_count": sum(1 for c in correlations if c["confidence"] > 0.6),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    def _patterns_correlate(self, current: str, historical: str) -> bool:
        """Check if current pattern correlates with historical bug type."""
        correlation_map = {
            "broad_exception": ["null_reference", "type_mismatch", "unknown"],
            "incomplete_code": ["async_timing", "null_reference"],
            "dangerous_eval": ["import_error", "type_mismatch"],
        }
        return historical in correlation_map.get(current, [])

    async def _predict(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Identify high-risk areas based on correlation scores.

        Calculates risk scores for each file and identifies
        the most likely locations for bugs to occur.
        """
        correlations = input_data.get("correlations", [])
        patterns_found = input_data.get("patterns_found", [])

        # Calculate file risk scores
        file_risks: dict[str, float] = {}
        for corr in correlations:
            file_path = corr["current_pattern"].get("file", "")
            confidence = corr.get("confidence", 0.3)
            severity_weight = {
                "high": 1.0,
                "medium": 0.6,
                "low": 0.3,
            }.get(corr["current_pattern"].get("severity", "low"), 0.3)

            risk = confidence * severity_weight
            file_risks[file_path] = file_risks.get(file_path, 0) + risk

        # Normalize and sort
        max_risk = max(file_risks.values()) if file_risks else 1.0
        predictions: list[dict] = [
            {
                "file": f,
                "risk_score": round(r / max_risk, 2),
                "patterns": [p for p in patterns_found if p.get("file") == f],
            }
            for f, r in sorted(file_risks.items(), key=lambda x: -x[1])
        ]

        # Calculate overall risk score
        self._risk_score = (
            sum(float(p["risk_score"]) for p in predictions[:5]) / 5
            if len(predictions) >= 5
            else sum(float(p["risk_score"]) for p in predictions) / max(len(predictions), 1)
        )

        input_tokens = estimate_tokens(input_data)
        output_tokens = estimate_tokens(predictions)

        return (
            {
                "predictions": predictions[:20],  # Top 20 risky files
                "overall_risk_score": round(self._risk_score, 2),
                "high_risk_files": sum(1 for p in predictions if float(p["risk_score"]) > 0.7),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _recommend(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate actionable fix recommendations using LLM.

        Uses premium tier (or capable if downgraded) to generate
        specific recommendations for addressing predicted bugs.

        Supports XML-enhanced prompts when enabled in workflow config.
        """
        predictions = input_data.get("predictions", [])
        target = input_data.get("target", "")

        # Build context for LLM
        top_risks = predictions[:10]
        issues_summary = []
        for pred in top_risks:
            file_path = pred.get("file", "")
            patterns = pred.get("patterns", [])
            for p in patterns:
                issues_summary.append(
                    f"- {file_path}: {p.get('pattern')} (severity: {p.get('severity')})",
                )

        # Build input payload
        input_payload = f"""Target: {target or "codebase"}

Issues Found:
{chr(10).join(issues_summary) if issues_summary else "No specific issues identified"}

Historical Bug Patterns:
{json.dumps(self._bug_patterns[:5], indent=2) if self._bug_patterns else "None"}

Risk Score: {input_data.get("overall_risk_score", 0):.2f}"""

        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            # Use XML-enhanced prompt
            from attune.prompts.examples import BUG_PREDICT_EXAMPLES

            user_message = self._render_xml_prompt(
                role="senior software engineer specializing in bug prevention",
                goal="Analyze bug-prone patterns and generate actionable recommendations",
                instructions=[
                    "Explain why each pattern is risky",
                    "Provide specific fixes with code examples",
                    "Suggest preventive measures",
                    "Reference historical patterns when relevant",
                    "Prioritize by severity and risk score",
                ],
                constraints=[
                    "Be specific and actionable",
                    "Include code examples where helpful",
                    "Group recommendations by priority",
                ],
                input_type="bug_patterns",
                input_payload=input_payload,
                examples=BUG_PREDICT_EXAMPLES,
                extra={
                    "risk_score": input_data.get("overall_risk_score", 0),
                    "pattern_count": len(issues_summary),
                },
            )
            system = None  # XML prompt includes all context
        else:
            # Use legacy plain text prompts
            system = """You are a senior software engineer specializing in bug prevention.
Analyze the identified code patterns and generate actionable recommendations.

For each issue:
1. Explain why this pattern is risky
2. Provide a specific fix with code example if applicable
3. Suggest preventive measures

Be specific and actionable. Prioritize by severity."""

            user_message = f"""Analyze these bug-prone patterns and provide recommendations:

{input_payload}

Provide detailed recommendations for preventing bugs."""

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = BUG_PREDICT_STEPS["recommend"]
                response, input_tokens, output_tokens, cost = await self.run_step_with_executor(
                    step=step,
                    prompt=user_message,
                    system=system,
                )
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback to legacy _call_llm if executor fails
                logger.warning("Executor failed, falling back to legacy LLM call: %s", e)
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system or "",
                    user_message,
                    max_tokens=2000,
                )
        else:
            # Legacy path for backward compatibility
            response, input_tokens, output_tokens = await self._call_llm(
                tier,
                system or "",
                user_message,
                max_tokens=2000,
            )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        result = {
            "recommendations": response,
            "recommendation_count": len(top_risks),
            "model_tier_used": tier.value,
            "overall_risk_score": input_data.get("overall_risk_score", 0),
            "auth_mode_used": self._auth_mode_used,  # Track recommended auth mode
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
        result["formatted_report"] = format_bug_predict_report(result, input_data)

        return (result, input_tokens, output_tokens)


if __name__ == "__main__":
    main()
