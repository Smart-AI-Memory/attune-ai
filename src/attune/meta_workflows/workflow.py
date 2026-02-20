"""Meta-workflow orchestration engine.

Coordinates the complete meta-workflow execution:
1. Template selection
2. Form collection (Socratic questioning)
3. Agent team generation
4. Agent execution (with tier escalation)
5. Result aggregation and storage (files + optional memory)

Created: 2026-01-17
Updated: 2026-02-19 (refactored into focused modules)
Purpose: Core orchestration for meta-workflows
"""

# Load environment variables from .env file
# Try multiple locations: project root, home directory, empathy config
try:
    from pathlib import Path

    from dotenv import load_dotenv

    # Try common .env locations
    _env_paths = [
        Path.cwd() / ".env",  # Current working directory
        Path(__file__).parent.parent.parent.parent / ".env",  # Project root
        Path.home() / ".env",  # Home directory
        Path.home() / ".attune" / ".env",  # Attune config directory
    ]

    for _env_path in _env_paths:
        if _env_path.exists():
            load_dotenv(_env_path)
            break
except ImportError:
    pass  # dotenv not installed, use environment variables directly

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from attune.config import _validate_file_path
from attune.meta_workflows.agent_creator import DynamicAgentCreator
from attune.meta_workflows.form_engine import SocraticFormEngine
from attune.meta_workflows.llm_execution import evaluate_success_criteria, execute_agents_real
from attune.meta_workflows.models import (
    AgentExecutionResult,
    AgentSpec,
    FormResponse,
    MetaWorkflowResult,
    MetaWorkflowTemplate,
    TierStrategy,
)
from attune.meta_workflows.prompt_builder import build_agent_prompt, get_generic_instructions
from attune.meta_workflows.report_generator import generate_report
from attune.meta_workflows.template_registry import TemplateRegistry

if TYPE_CHECKING:
    from attune.meta_workflows.pattern_learner import PatternLearner

logger = logging.getLogger(__name__)


class MetaWorkflow:
    """Orchestrates complete meta-workflow execution.

    Coordinates form collection, agent generation, and execution
    to implement dynamic, template-based workflows.

    Hybrid Storage:
    - Files: Persistent, human-readable execution results
    - Memory: Rich semantic queries (optional via pattern_learner)

    Attributes:
        template: Meta-workflow template to execute
        storage_dir: Directory for storing execution results
        form_engine: Engine for collecting form responses
        agent_creator: Creator for generating agent teams
        pattern_learner: Optional pattern learner for memory integration
    """

    def __init__(
        self,
        template: MetaWorkflowTemplate | None = None,
        template_id: str | None = None,
        storage_dir: str | None = None,
        pattern_learner: "PatternLearner | None" = None,
    ):
        """Initialize meta-workflow with optional memory integration.

        Args:
            template: Template to execute (optional if template_id provided)
            template_id: ID of template to load (optional if template provided)
            storage_dir: Directory for execution results
                        (default: .attune/meta_workflows/executions/)
            pattern_learner: Optional pattern learner with memory integration
                            If provided, execution results will be stored in
                            both files and memory for rich semantic querying

        Raises:
            ValueError: If neither template nor template_id provided
        """
        if template is None and template_id is None:
            raise ValueError("Must provide either template or template_id")

        # Load template if needed
        if template is None:
            registry = TemplateRegistry()
            template = registry.load_template(template_id)
            if template is None:
                raise ValueError(f"Template not found: {template_id}")

        self.template = template
        self.form_engine = SocraticFormEngine()
        self.agent_creator = DynamicAgentCreator()
        self.pattern_learner = pattern_learner

        # Set up storage
        if storage_dir is None:
            storage_dir = str(Path.home() / ".attune" / "meta_workflows" / "executions")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Initialized MetaWorkflow for template: {self.template.template_id}",
            extra={"memory_enabled": pattern_learner is not None},
        )

    def execute(
        self,
        form_response: FormResponse | None = None,
        mock_execution: bool = True,
        use_defaults: bool = False,
    ) -> MetaWorkflowResult:
        """Execute complete meta-workflow.

        Args:
            form_response: Pre-collected form responses (optional)
                          If None, will collect via form_engine
            mock_execution: Use mock agent execution (default: True for MVP)
                           Set to False for real LLM execution
            use_defaults: Use default values instead of asking questions
                         (non-interactive mode)

        Returns:
            MetaWorkflowResult with complete execution details

        Raises:
            ValueError: If execution fails
        """
        run_id = f"{self.template.template_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        start_time = time.time()

        logger.info(f"Starting meta-workflow execution: {run_id}")

        try:
            # Stage 1: Form collection (if not provided)
            if form_response is None:
                if use_defaults:
                    logger.info("Stage 1: Using default form values (non-interactive)")
                else:
                    logger.info("Stage 1: Collecting form responses")
                form_response = self.form_engine.ask_questions(
                    self.template.form_schema, self.template.template_id
                )
            else:
                logger.info("Stage 1: Using provided form responses")

            # Stage 2: Agent generation
            logger.info("Stage 2: Generating agent team")
            agents = self.agent_creator.create_agents(self.template, form_response)

            logger.info(f"Created {len(agents)} agents")

            # Stage 3: Agent execution
            logger.info("Stage 3: Executing agents")

            if mock_execution:
                agent_results = self._execute_agents_mock(agents)
            else:
                agent_results = execute_agents_real(agents)

            # Stage 4: Aggregate results
            logger.info("Stage 4: Aggregating results")

            total_cost = sum(result.cost for result in agent_results)
            total_duration = time.time() - start_time
            success = all(result.success for result in agent_results)

            result = MetaWorkflowResult(
                run_id=run_id,
                template_id=self.template.template_id,
                timestamp=datetime.now().isoformat(),
                form_responses=form_response,
                agents_created=agents,
                agent_results=agent_results,
                total_cost=total_cost,
                total_duration=total_duration,
                success=success,
            )

            # Stage 5: Save results (files + optional memory)
            logger.info("Stage 5: Saving results")
            self._save_execution(result)

            # Store in memory if pattern learner available
            if self.pattern_learner:
                logger.info("Stage 5b: Storing in memory")
                pattern_id = self.pattern_learner.store_execution_in_memory(result)
                if pattern_id:
                    logger.info(f"Execution stored in memory: {pattern_id}")

            logger.info(
                f"Meta-workflow execution complete: {run_id} "
                f"(cost: ${total_cost:.2f}, duration: {total_duration:.1f}s)"
            )

            return result

        except Exception as e:
            logger.error(f"Meta-workflow execution failed: {e}")

            # Create error result
            error_result = MetaWorkflowResult(
                run_id=run_id,
                template_id=self.template.template_id,
                timestamp=datetime.now().isoformat(),
                form_responses=form_response or FormResponse(template_id=self.template.template_id),
                total_cost=0.0,
                total_duration=time.time() - start_time,
                success=False,
                error=str(e),
            )

            # Try to save error result
            try:
                self._save_execution(error_result)
            except Exception as save_error:
                logger.error(f"Failed to save error result: {save_error}")

            raise ValueError(f"Meta-workflow execution failed: {e}") from e

    def _execute_agents_mock(self, agents: list[AgentSpec]) -> list[AgentExecutionResult]:
        """Execute agents with mock execution (for MVP).

        Args:
            agents: List of agent specs to execute

        Returns:
            List of agent execution results
        """
        results = []

        for agent in agents:
            logger.debug(f"Mock executing agent: {agent.role}")

            # Simulate execution time based on tier
            if agent.tier_strategy == TierStrategy.CHEAP_ONLY:
                duration = 1.5
                cost = 0.05
                tier_used = "cheap"
            elif agent.tier_strategy == TierStrategy.PROGRESSIVE:
                duration = 3.0
                cost = 0.15  # Average (may escalate)
                tier_used = "capable"
            elif agent.tier_strategy == TierStrategy.CAPABLE_FIRST:
                duration = 4.0
                cost = 0.25
                tier_used = "capable"
            else:  # PREMIUM_ONLY
                duration = 6.0
                cost = 0.40
                tier_used = "premium"

            # Mock result
            result = AgentExecutionResult(
                agent_id=agent.agent_id,
                role=agent.role,
                success=True,
                cost=cost,
                duration=duration,
                tier_used=tier_used,
                output={
                    "message": f"Mock execution of {agent.role}",
                    "tier_strategy": agent.tier_strategy.value,
                    "tools_used": agent.tools,
                    "config": agent.config,
                    "success_criteria": agent.success_criteria,
                },
            )

            results.append(result)

            # Simulate some execution time
            time.sleep(0.1)

        return results

    def _save_execution(self, result: MetaWorkflowResult) -> Path:
        """Save execution results to disk.

        Args:
            result: Execution result to save

        Returns:
            Path to saved results directory

        Raises:
            OSError: If save operation fails
        """
        # Create run directory
        run_dir = self.storage_dir / result.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save config (template info + form responses)
        config_file = run_dir / "config.json"
        config_data = {
            "template_id": result.template_id,
            "template_name": self.template.name,
            "template_version": self.template.version,
            "run_id": result.run_id,
            "timestamp": result.timestamp,
        }
        validated_config = _validate_file_path(str(config_file))
        validated_config.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

        # Save form responses
        responses_file = run_dir / "form_responses.json"
        validated_responses = _validate_file_path(str(responses_file))
        validated_responses.write_text(
            json.dumps(
                {
                    "template_id": result.form_responses.template_id,
                    "responses": result.form_responses.responses,
                    "timestamp": result.form_responses.timestamp,
                    "response_id": result.form_responses.response_id,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # Save agents created
        agents_file = run_dir / "agents.json"
        agents_data = [
            {
                "agent_id": agent.agent_id,
                "role": agent.role,
                "base_template": agent.base_template,
                "tier_strategy": agent.tier_strategy.value,
                "tools": agent.tools,
                "config": agent.config,
                "success_criteria": agent.success_criteria,
            }
            for agent in result.agents_created
        ]
        validated_agents = _validate_file_path(str(agents_file))
        validated_agents.write_text(json.dumps(agents_data, indent=2), encoding="utf-8")

        # Save complete result
        result_file = run_dir / "result.json"
        validated_result = _validate_file_path(str(result_file))
        validated_result.write_text(result.to_json(), encoding="utf-8")

        # Create human-readable report
        report_file = run_dir / "report.txt"
        report = self._generate_report(result)
        validated_report = _validate_file_path(str(report_file))
        validated_report.write_text(report, encoding="utf-8")

        logger.info(f"Saved execution results to: {run_dir}")
        return run_dir

    def _generate_report(self, result: MetaWorkflowResult) -> str:
        """Generate human-readable report.

        Delegates to report_generator module.

        Args:
            result: Execution result

        Returns:
            Markdown-formatted report
        """
        return generate_report(result, self.template)

    def _get_generic_instructions(self, role: str) -> str:
        """Generate generic instructions based on agent role.

        Delegates to prompt_builder.get_generic_instructions().

        Args:
            role: Agent role name

        Returns:
            Generic instructions appropriate for the role
        """
        return get_generic_instructions(role)

    def _build_agent_prompt(self, agent: AgentSpec) -> str:
        """Build prompt for agent from specification.

        Delegates to prompt_builder.build_agent_prompt().

        Args:
            agent: Agent specification

        Returns:
            Formatted prompt string
        """
        return build_agent_prompt(agent)

    def _evaluate_success_criteria(self, result: AgentExecutionResult, agent: AgentSpec) -> bool:
        """Evaluate if agent result meets success criteria.

        Delegates to llm_execution.evaluate_success_criteria().

        Args:
            result: Agent execution result
            agent: Agent specification with success criteria

        Returns:
            True if success criteria met, False otherwise
        """
        return evaluate_success_criteria(result, agent)


# =============================================================================
# Helper functions
# =============================================================================


def load_execution_result(run_id: str, storage_dir: str | None = None) -> MetaWorkflowResult:
    """Load a saved execution result.

    Args:
        run_id: ID of execution to load
        storage_dir: Directory where executions are stored

    Returns:
        Loaded MetaWorkflowResult

    Raises:
        FileNotFoundError: If result not found
        ValueError: If result file is invalid
    """
    if storage_dir is None:
        storage_dir = str(Path.home() / ".attune" / "meta_workflows" / "executions")

    result_file = Path(storage_dir) / run_id / "result.json"

    if not result_file.exists():
        raise FileNotFoundError(f"Result not found: {run_id}")

    try:
        json_str = result_file.read_text(encoding="utf-8")
        data = json.loads(json_str)
        return MetaWorkflowResult.from_dict(data)

    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid result file: {e}") from e


def list_execution_results(storage_dir: str | None = None) -> list[str]:
    """List all saved execution results.

    Args:
        storage_dir: Directory where executions are stored

    Returns:
        List of run IDs (sorted by timestamp, newest first)
    """
    if storage_dir is None:
        storage_dir = str(Path.home() / ".attune" / "meta_workflows" / "executions")

    storage_path = Path(storage_dir)

    if not storage_path.exists():
        return []

    # Find all directories with result.json
    run_ids = []
    for dir_path in storage_path.iterdir():
        if dir_path.is_dir() and (dir_path / "result.json").exists():
            run_ids.append(dir_path.name)

    # Sort by timestamp (newest first)
    run_ids.sort(reverse=True)

    return run_ids
