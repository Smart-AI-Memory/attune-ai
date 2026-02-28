"""Generated workflow from blueprint execution.

Contains the GeneratedWorkflow dataclass that represents a
runnable workflow with agents and stages.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .blueprint import WorkflowBlueprint


@dataclass
class GeneratedWorkflow:
    """A generated, runnable workflow.

    Contains all the components needed to execute the workflow.
    """

    # Source blueprint
    blueprint: WorkflowBlueprint

    # Generated XMLAgent instances
    agents: list[Any]  # XMLAgent

    # Stage configuration
    stages: list[dict[str, Any]]

    # Generation timestamp
    generated_at: str = ""

    # Whether workflow has been validated
    validated: bool = False

    async def execute(
        self,
        input_data: dict[str, Any],
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """Execute the workflow.

        Args:
            input_data: Input data for the workflow
            progress_callback: Optional progress callback

        Returns:
            Workflow results

        """
        # This is a simplified execution - real implementation would
        # integrate with BaseWorkflow
        results: dict[str, Any] = {
            "stages": {},
            "agents": {},
            "final_output": None,
            "success": False,
        }

        for stage_config in self.stages:
            stage_id = stage_config["id"]
            agent_ids = stage_config["agents"]

            stage_results = []
            for agent_id in agent_ids:
                # Find agent
                agent = next(
                    (
                        a
                        for a in self.agents
                        if hasattr(a, "role") and self._match_agent(a, agent_id)
                    ),
                    None,
                )
                if agent:
                    # Execute agent (simplified)
                    result = {
                        "agent_id": agent_id,
                        "status": "completed",
                        "output": f"Agent {agent_id} completed",
                    }
                    stage_results.append(result)

            results["stages"][stage_id] = stage_results

        results["success"] = True
        results["final_output"] = results["stages"]

        return results

    def _match_agent(self, agent: Any, agent_id: str) -> bool:
        """Check if an agent matches an ID."""
        # Match by role name (simplified)
        if hasattr(agent, "role"):
            return agent_id.replace("_", " ").lower() in agent.role.lower()
        return False

    def describe(self) -> str:
        """Get human-readable description of the workflow."""
        lines = [
            f"Workflow: {self.blueprint.name}",
            f"Description: {self.blueprint.description}",
            "",
            f"Agents ({len(self.agents)}):",
        ]

        for agent in self.agents:
            if hasattr(agent, "role"):
                lines.append(f"  - {agent.role}: {getattr(agent, 'goal', 'N/A')}")

        lines.append("")
        lines.append(f"Stages ({len(self.stages)}):")

        for stage in self.stages:
            parallel = "parallel" if stage.get("parallel") else "sequential"
            lines.append(f"  - {stage['name']} ({parallel}): {', '.join(stage['agents'])}")

        return "\n".join(lines)
