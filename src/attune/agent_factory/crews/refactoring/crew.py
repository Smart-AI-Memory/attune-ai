"""Refactoring Crew

A 2-agent crew that performs interactive code refactoring analysis.
Designed for Level 4 Empathy with session memory, rollback capability,
and learning from user preferences over time.

Agents:
- RefactorAnalyzer: Identifies refactoring opportunities, prioritizes by impact
- RefactorWriter: Generates concrete code changes with before/after

Usage:
    from attune.agent_factory.crews import RefactoringCrew

    crew = RefactoringCrew(api_key="...")
    report = await crew.analyze(code="...", file_path="src/api.py")

    for finding in report.findings:
        print(f"  - {finding.title} ({finding.category.value})")

        # Generate the refactored code
        finding = await crew.generate_refactor(finding, code)
        print(f"    Before: {finding.before_code[:50]}...")
        print(f"    After: {finding.after_code[:50]}...")

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import uuid
from typing import Any

from .checkpoints import create_checkpoint, rollback
from .config import XML_PROMPT_TEMPLATES
from .types import (
    CodeCheckpoint,
    Impact,
    RefactoringCategory,
    RefactoringConfig,
    RefactoringFinding,
    RefactoringReport,
    Severity,
    UserProfile,
)
from .user_profiles import (
    apply_user_preferences,
    load_user_profile,
    record_decision,
    save_user_profile,
)

logger = logging.getLogger(__name__)


# =============================================================================
# RefactoringCrew Class
# =============================================================================


class RefactoringCrew:
    """2-agent crew for interactive code refactoring.

    The crew consists of:

    1. **RefactorAnalyzer** (Analysis Agent)
       - Analyzes code for refactoring opportunities
       - Identifies code smells and improvement areas
       - Prioritizes by impact and confidence
       - Model: Capable tier (cost-effective)

    2. **RefactorWriter** (Generation Agent)
       - Generates concrete refactored code
       - Produces before/after diffs
       - Ensures syntactic correctness
       - Model: Capable tier

    Features:
    - Checkpoint/rollback for safe refactoring
    - User profile learning for personalized recommendations
    - Memory Graph integration for cross-session learning

    Example:
        crew = RefactoringCrew(api_key="...")
        report = await crew.analyze(code="...", file_path="api.py")

        for finding in report.findings:
            # Generate refactored code on demand
            finding = await crew.generate_refactor(finding, full_code)
            print(f"After: {finding.after_code}")

    """

    def __init__(self, config: RefactoringConfig | None = None, **kwargs: Any):
        """Initialize the Refactoring Crew.

        Args:
            config: RefactoringConfig or pass individual params as kwargs
            **kwargs: Individual config parameters (api_key, provider, etc.)

        """
        if config:
            self.config = config
        else:
            self.config = RefactoringConfig(**kwargs)

        self._factory: Any = None
        self._agents: dict[str, Any] = {}
        self._workflow: Any = None
        self._graph: Any = None
        self._user_profile: UserProfile | None = None
        self._initialized = False

    def _render_xml_prompt(self, template_key: str) -> str:
        """Render XML prompt template with config values."""
        template = XML_PROMPT_TEMPLATES.get(template_key, "")
        return template.format(schema_version=self.config.xml_schema_version)

    def _get_system_prompt(self, agent_key: str, fallback: str) -> str:
        """Get system prompt - XML if enabled, fallback otherwise."""
        if self.config.xml_prompts_enabled:
            return self._render_xml_prompt(agent_key)
        return fallback

    async def _initialize(self) -> None:
        """Lazy initialization of agents and workflow."""
        if self._initialized:
            return

        from attune.agent_factory import AgentFactory, Framework

        # Check if CrewAI is available
        try:
            from attune.agent_factory.adapters.crewai_adapter import _check_crewai

            use_crewai = _check_crewai()
        except ImportError:
            use_crewai = False

        # Use CrewAI if available, otherwise fall back to Native
        framework = Framework.CREWAI if use_crewai else Framework.NATIVE

        self._factory = AgentFactory(
            framework=framework,
            provider=self.config.provider,
            api_key=self.config.api_key,
        )

        # Initialize Memory Graph if enabled
        if self.config.memory_graph_enabled:
            try:
                from attune.memory import MemoryGraph

                self._graph = MemoryGraph(path=self.config.memory_graph_path)
            except ImportError:
                logger.warning("Memory Graph not available, continuing without it")

        # Load user profile if enabled
        if self.config.user_profile_enabled:
            self._user_profile = load_user_profile(self.config.user_profile_path)

        # Create the 2 specialized agents
        await self._create_agents()

        self._initialized = True

    async def _create_agents(self) -> None:
        """Create the 2 specialized refactoring agents."""
        # Fallback prompts
        analyzer_fallback = """You are a Refactoring Analyst.

Your job is to analyze code and identify refactoring opportunities:

1. Look for code smells:
   - Long methods (>20 lines)
   - Duplicate code blocks
   - Poor naming
   - Dead code (unused variables/functions)
   - Complex conditionals

2. For each finding, provide:
   - Title and description
   - Category (extract_method, rename, simplify, etc.)
   - Severity (critical/high/medium/low)
   - Line numbers (start_line, end_line)
   - The before_code snippet
   - Confidence score (0-1)
   - Estimated impact (high/medium/low)
   - Rationale for the recommendation

Focus on actionable, safe refactorings. Prioritize by impact."""

        writer_fallback = """You are a Refactoring Engineer.

Your job is to generate the refactored code for a specific finding.

Requirements:
1. The code MUST be syntactically valid
2. Preserve all functionality - no behavior changes
3. Match the project's coding style
4. Keep changes minimal - only change what's needed

Return the refactored code as after_code."""

        # 1. RefactorAnalyzer
        self._agents["analyzer"] = self._factory.create_agent(
            name="refactor_analyzer",
            role="analyst",
            description="Analyzes code for refactoring opportunities",
            system_prompt=self._get_system_prompt("refactor_analyzer", analyzer_fallback),
            model_tier=self.config.analyzer_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
            resilience_enabled=self.config.resilience_enabled,
        )

        # 2. RefactorWriter
        self._agents["writer"] = self._factory.create_agent(
            name="refactor_writer",
            role="engineer",
            description="Generates refactored code for specific findings",
            system_prompt=self._get_system_prompt("refactor_writer", writer_fallback),
            model_tier=self.config.writer_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
            resilience_enabled=self.config.resilience_enabled,
        )

    # =========================================================================
    # Public Methods
    # =========================================================================

    async def analyze(
        self,
        code: str,
        file_path: str,
        context: dict | None = None,
    ) -> RefactoringReport:
        """Analyze code for refactoring opportunities.

        Args:
            code: The source code to analyze
            file_path: Path to the file being analyzed
            context: Optional context (language, project conventions, etc.)

        Returns:
            RefactoringReport with prioritized findings

        """
        import time

        start_time = time.time()

        # Initialize if needed
        await self._initialize()

        context = context or {}
        findings: list[RefactoringFinding] = []
        memory_hits = 0

        # Query Memory Graph for similar past refactorings
        if self._graph and self.config.memory_graph_enabled:
            try:
                similar = self._graph.find_similar(
                    {"name": f"refactor:{file_path}", "description": file_path},
                    threshold=0.4,
                    limit=10,
                )
                if similar:
                    memory_hits = len(similar)
                    context["similar_refactorings"] = [
                        {
                            "name": node.name,
                            "category": node.metadata.get("category", "unknown"),
                        }
                        for node, score in similar
                    ]
                    logger.info(f"Found {memory_hits} similar past refactorings")
            except (AttributeError, KeyError, ValueError) as e:
                # Memory Graph data structure errors
                logger.warning(f"Memory Graph query error (data issue): {e}")
            except OSError as e:
                # File system errors accessing memory graph
                logger.warning(f"Memory Graph query error (file system): {e}")
            except Exception:
                # INTENTIONAL: Memory Graph is optional - continue without it
                logger.exception("Unexpected error querying Memory Graph")

        # Build analysis task
        task = self._build_analysis_task(code, file_path, context)

        # Execute analysis
        try:
            result = await self._agents["analyzer"].invoke(task, context)
            findings = self._parse_findings(result)

            # Apply user preferences for prioritization
            if self._user_profile:
                findings = apply_user_preferences(findings, self._user_profile)

        except KeyError as e:
            # Agent not initialized or missing in agents dict
            logger.error(f"Analysis failed (agent not found): {e}")
            return RefactoringReport(
                target=file_path,
                findings=[],
                summary=f"Analysis failed - agent not initialized: {e}",
                duration_seconds=time.time() - start_time,
                agents_used=["analyzer"],
                memory_graph_hits=memory_hits,
                metadata={"error": str(e)},
            )
        except (ValueError, TypeError, RuntimeError) as e:
            # Agent invocation errors (invalid input, API errors, etc.)
            logger.error(f"Analysis failed (invocation error): {e}")
            return RefactoringReport(
                target=file_path,
                findings=[],
                summary=f"Analysis failed - agent error: {e}",
                duration_seconds=time.time() - start_time,
                agents_used=["analyzer"],
                memory_graph_hits=memory_hits,
                metadata={"error": str(e)},
            )
        except Exception:
            # INTENTIONAL: Graceful degradation - return empty report rather than crashing
            logger.exception("Unexpected error in refactoring analysis")
            return RefactoringReport(
                target=file_path,
                findings=[],
                summary="Analysis failed due to unexpected error",
                duration_seconds=time.time() - start_time,
                agents_used=["analyzer"],
                memory_graph_hits=memory_hits,
                metadata={"error": "unexpected_error"},
            )

        # Build report
        duration = time.time() - start_time
        report = RefactoringReport(
            target=file_path,
            findings=findings,
            summary=self._generate_summary(findings),
            duration_seconds=duration,
            agents_used=list(self._agents.keys()),
            memory_graph_hits=memory_hits,
            metadata={
                "depth": self.config.depth,
                "framework": str(self._factory.framework.value) if self._factory else "unknown",
            },
        )

        # Store in Memory Graph
        if self._graph and self.config.memory_graph_enabled:
            try:
                self._graph.add_finding(
                    "refactoring_crew",
                    {
                        "type": "refactoring_analysis",
                        "name": f"refactor:{file_path}",
                        "description": report.summary,
                        "findings_count": len(findings),
                    },
                )
                self._graph._save()
            except (AttributeError, KeyError, ValueError) as e:
                # Memory Graph data structure errors
                logger.warning(f"Error storing in Memory Graph (data issue): {e}")
            except (OSError, PermissionError) as e:
                # File system errors saving memory graph
                logger.warning(f"Error storing in Memory Graph (file system): {e}")
            except Exception:
                # INTENTIONAL: Memory Graph storage is optional - continue without it
                logger.exception("Unexpected error storing in Memory Graph")

        return report

    async def generate_refactor(
        self,
        finding: RefactoringFinding,
        full_code: str,
    ) -> RefactoringFinding:
        """Generate refactored code for a specific finding.

        Args:
            finding: The finding to generate refactored code for
            full_code: The complete source file content

        Returns:
            Updated finding with after_code populated

        """
        await self._initialize()

        task = self._build_refactor_task(finding, full_code)

        try:
            result = await self._agents["writer"].invoke(task)
            after_code = self._parse_refactor_result(result)
            finding.after_code = after_code
        except KeyError as e:
            # Agent not initialized or missing in agents dict
            logger.error(f"Refactor generation failed (agent not found): {e}")
            finding.metadata["generation_error"] = f"Agent not initialized: {e}"
        except (ValueError, TypeError, RuntimeError) as e:
            # Agent invocation errors (invalid input, API errors, etc.)
            logger.error(f"Refactor generation failed (invocation error): {e}")
            finding.metadata["generation_error"] = f"Agent error: {e}"
        except Exception:
            # INTENTIONAL: Graceful degradation - finding without after_code is still useful
            logger.exception("Unexpected error in refactor generation")
            finding.metadata["generation_error"] = "Unexpected error"

        return finding

    # =========================================================================
    # Checkpoint & Rollback
    # =========================================================================

    def create_checkpoint(
        self,
        file_path: str,
        content: str,
        finding_id: str,
    ) -> CodeCheckpoint:
        """Create a checkpoint before applying a change.

        Args:
            file_path: Path to the file
            content: Current content of the file
            finding_id: ID of the finding being applied

        Returns:
            CodeCheckpoint that can be used for rollback

        """
        return create_checkpoint(file_path, content, finding_id)

    def rollback(self, checkpoint: CodeCheckpoint) -> str:
        """Get the original content from a checkpoint.

        Args:
            checkpoint: The checkpoint to rollback to

        Returns:
            The original file content

        """
        return rollback(checkpoint)

    # =========================================================================
    # User Profile Management
    # =========================================================================

    def _load_user_profile(self) -> UserProfile:
        """Load user profile from disk."""
        return load_user_profile(self.config.user_profile_path)

    def save_user_profile(self) -> None:
        """Save user profile to disk."""
        if not self._user_profile:
            return
        save_user_profile(self._user_profile, self.config.user_profile_path)

    def record_decision(self, finding: RefactoringFinding, accepted: bool) -> None:
        """Record user decision for learning.

        Args:
            finding: The finding that was accepted or rejected
            accepted: True if user accepted, False if rejected

        """
        if not self._user_profile:
            return
        record_decision(self._user_profile, finding, accepted, self.config.user_profile_path)

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _build_analysis_task(self, code: str, file_path: str, context: dict) -> str:
        """Build the analysis task for the analyzer agent."""
        depth_instructions = {
            "quick": "Focus on obvious issues only. Skip minor improvements.",
            "standard": "Balance thoroughness with practicality. Cover major patterns.",
            "thorough": "Deep analysis including subtle improvements and edge cases.",
        }

        focus_list = ", ".join(self.config.focus_areas)

        task = f"""Analyze the following code for refactoring opportunities.

File: {file_path}
Analysis Depth: {self.config.depth}
Instructions: {depth_instructions.get(self.config.depth, "standard")}
Focus Areas: {focus_list}

```
{code[:20000]}
```

Return a JSON array of findings. Each finding should have:
- id: unique identifier (use UUID format)
- title: brief description
- description: detailed explanation
- category: {focus_list}, or "other"
- severity: critical, high, medium, low, or info
- file_path: "{file_path}"
- start_line: starting line number
- end_line: ending line number
- before_code: the current code snippet
- confidence: 0.0 to 1.0
- estimated_impact: high, medium, or low
- rationale: why this refactoring is recommended

Prioritize by impact and confidence. Return at most 10 findings.
"""

        if context.get("similar_refactorings"):
            task += f"\n\nSimilar past refactorings found: {len(context['similar_refactorings'])}"

        return task

    def _build_refactor_task(self, finding: RefactoringFinding, full_code: str) -> str:
        """Build the refactoring task for the writer agent."""
        return f"""Generate refactored code for the following finding.

Finding: {finding.title}
Category: {finding.category.value}
Description: {finding.description}
Lines: {finding.start_line} to {finding.end_line}
Rationale: {finding.rationale}

Current code (before):
```
{finding.before_code}
```

Full file context:
```
{full_code[:15000]}
```

Return a JSON object with:
- after_code: the complete refactored code snippet (to replace before_code)
- explanation: brief explanation of changes made

The refactored code MUST be syntactically valid and preserve all functionality.
"""

    def _parse_findings(self, result: dict) -> list[RefactoringFinding]:
        """Parse findings from analyzer result."""
        findings = []

        output = result.get("output", "")
        metadata = result.get("metadata", {})

        # Try structured findings first
        if "findings" in metadata:
            for f in metadata["findings"]:
                findings.append(RefactoringFinding.from_dict(f))
            return findings

        # Try to parse JSON from output
        try:
            # Look for JSON array in output
            import re

            json_match = re.search(r"\[[\s\S]*\]", output)
            if json_match:
                data = json.loads(json_match.group())
                for f in data:
                    findings.append(RefactoringFinding.from_dict(f))
                return findings
        except json.JSONDecodeError:
            pass

        # Fallback: create a single finding from text
        if output.strip():
            findings.append(
                RefactoringFinding(
                    id=str(uuid.uuid4()),
                    title="Analysis Result",
                    description=output[:500],
                    category=RefactoringCategory.OTHER,
                    severity=Severity.INFO,
                    file_path="",
                    start_line=0,
                    end_line=0,
                    confidence=0.5,
                ),
            )

        return findings

    def _parse_refactor_result(self, result: dict) -> str:
        """Parse refactored code from writer result."""
        output = result.get("output", "")
        metadata = result.get("metadata", {})

        # Check metadata first
        if "after_code" in metadata:
            return str(metadata["after_code"])

        # Try to parse JSON from output
        try:
            import re

            json_match = re.search(r"\{[\s\S]*\}", output)
            if json_match:
                data = json.loads(json_match.group())
                if "after_code" in data:
                    return str(data["after_code"])
        except json.JSONDecodeError:
            pass

        # Look for code blocks
        import re

        code_match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", output)
        if code_match:
            return code_match.group(1).strip()

        # Return raw output as fallback
        return str(output).strip()

    def _apply_user_preferences(
        self,
        findings: list[RefactoringFinding],
    ) -> list[RefactoringFinding]:
        """Apply user preferences to prioritize findings."""
        if not self._user_profile:
            return findings
        return apply_user_preferences(findings, self._user_profile)

    def _generate_summary(self, findings: list[RefactoringFinding]) -> str:
        """Generate summary of analysis."""
        if not findings:
            return "No refactoring opportunities identified."

        by_impact = {
            Impact.HIGH: sum(1 for f in findings if f.estimated_impact == Impact.HIGH),
            Impact.MEDIUM: sum(1 for f in findings if f.estimated_impact == Impact.MEDIUM),
            Impact.LOW: sum(1 for f in findings if f.estimated_impact == Impact.LOW),
        }

        parts = [f"Found {len(findings)} refactoring opportunities:"]

        if by_impact[Impact.HIGH] > 0:
            parts.append(f"  - {by_impact[Impact.HIGH]} high impact")
        if by_impact[Impact.MEDIUM] > 0:
            parts.append(f"  - {by_impact[Impact.MEDIUM]} medium impact")
        if by_impact[Impact.LOW] > 0:
            parts.append(f"  - {by_impact[Impact.LOW]} low impact")

        # Top categories
        by_cat: dict[str, int] = {}
        for f in findings:
            cat = f.category.value
            by_cat[cat] = by_cat.get(cat, 0) + 1

        if by_cat:
            top = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:3]
            parts.append("\nTop categories:")
            for cat, count in top:
                parts.append(f"  - {cat}: {count}")

        return "\n".join(parts)

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def agents(self) -> dict[str, Any]:
        """Get the crew's agents."""
        return self._agents

    @property
    def is_initialized(self) -> bool:
        """Check if crew is initialized."""
        return self._initialized

    @property
    def user_profile(self) -> UserProfile | None:
        """Get the current user profile."""
        return self._user_profile
