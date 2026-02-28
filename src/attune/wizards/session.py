"""Wizard session state management.

Tracks state across wizard steps including collected user data,
step results, decomposed tasks, and cost accumulation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WizardSession:
    """Tracks mutable state across wizard steps.

    Each step reads from and writes to the session. The session provides
    a layered lookup: ``get()`` checks ``collected_data`` first, then
    falls back to ``initial_context``.

    Args:
        wizard_id: Identifier of the wizard that owns this session.
        initial_context: Read-only context provided at wizard start.

    Example:
        >>> session = WizardSession(wizard_id="debug")
        >>> session.set("target_file", "src/main.py")
        >>> session.get("target_file")
        'src/main.py'

    """

    wizard_id: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    initial_context: dict[str, Any] = field(default_factory=dict)
    collected_data: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, Any] = field(default_factory=dict)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    steps_completed: list[str] = field(default_factory=list)
    steps_skipped: list[str] = field(default_factory=list)
    generated_output: str | dict[str, Any] = ""
    total_cost: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # -----------------------------------------------------------------
    # Data access
    # -----------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Set a value in collected data.

        Args:
            key: Data key.
            value: Data value.

        """
        self.collected_data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value, checking collected data then initial context.

        Args:
            key: Data key.
            default: Fallback if key not found in either dict.

        Returns:
            The value or *default*.

        """
        if key in self.collected_data:
            return self.collected_data[key]
        return self.initial_context.get(key, default)

    # -----------------------------------------------------------------
    # Step lifecycle
    # -----------------------------------------------------------------

    def complete_step(
        self,
        step_id: str,
        result: Any = None,
        cost: float = 0.0,
    ) -> None:
        """Mark a step as completed.

        Args:
            step_id: Identifier of the completed step.
            result: Optional result data to store.
            cost: LLM cost incurred during this step.

        """
        self.steps_completed.append(step_id)
        if result is not None:
            self.step_results[step_id] = result
        self.total_cost += cost

    def skip_step(self, step_id: str) -> None:
        """Mark a step as skipped.

        Args:
            step_id: Identifier of the skipped step.

        """
        self.steps_skipped.append(step_id)

    # -----------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to a JSON-safe dict.

        Returns:
            Dict representation of this session.

        """
        return {
            "wizard_id": self.wizard_id,
            "run_id": self.run_id,
            "collected_data": self.collected_data,
            "step_results": self.step_results,
            "tasks": self.tasks,
            "steps_completed": self.steps_completed,
            "steps_skipped": self.steps_skipped,
            "generated_output": self.generated_output,
            "total_cost": self.total_cost,
            "started_at": self.started_at,
        }
