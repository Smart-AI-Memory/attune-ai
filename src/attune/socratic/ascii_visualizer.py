"""ASCII Workflow Visualizer

Creates ASCII art visualization of workflows for terminal display.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .blueprint import WorkflowBlueprint

# Box-drawing characters
_HORIZONTAL = "\u2500"  # ─
_VERTICAL = "\u2502"  # │
_DOUBLE_VERTICAL = "\u2551"  # ║
_TOP_LEFT = "\u250c"  # ┌
_TOP_RIGHT = "\u2510"  # ┐
_BOTTOM_LEFT = "\u2514"  # └
_BOTTOM_RIGHT = "\u2518"  # ┘
_ARROW = "\u2192"  # →
_PARALLEL = "\u2225"  # ∥


class ASCIIVisualizer:
    """Creates ASCII art visualization of workflows for terminal display."""

    def __init__(self, width: int = 80):
        """Initialize ASCII visualizer.

        Args:
            width: Maximum width in characters

        """
        self.width = width

    def render(self, blueprint: WorkflowBlueprint) -> str:
        """Render workflow as ASCII art.

        Args:
            blueprint: The workflow blueprint

        Returns:
            ASCII art string

        """
        lines: list[str] = []

        # Header
        lines.append("=" * self.width)
        lines.append(self._center(f"Workflow: {blueprint.name}"))
        lines.append("=" * self.width)
        lines.append("")

        # Agents summary
        lines.append(self._box("Agents"))
        for agent in blueprint.agents:
            # Access tools via spec since AgentBlueprint wraps AgentSpec
            agent_tools = agent.spec.tools if hasattr(agent, "spec") else []
            tools = ", ".join(t.id for t in agent_tools[:3])
            if len(agent_tools) > 3:
                tools += f" (+{len(agent_tools) - 3} more)"
            agent_role = agent.spec.role if hasattr(agent, "spec") else agent.role
            agent_name = agent.spec.name if hasattr(agent, "spec") else agent.name
            lines.append(f"  [{agent_role.value[:3].upper()}] {agent_name}")
            lines.append(f"       Tools: {tools}")
        lines.append("")

        # Flow diagram
        lines.append(self._box("Workflow Flow"))
        lines.append("")
        lines.append(self._center("[ START ]"))
        lines.append(self._center(_VERTICAL))

        for i, stage in enumerate(blueprint.stages):
            is_last = i == len(blueprint.stages) - 1

            # Stage box
            bar = _HORIZONTAL * (len(stage.name) + 2)
            lines.append(self._center(f"{_TOP_LEFT}{bar}{_TOP_RIGHT}"))
            lines.append(self._center(f"{_VERTICAL} {stage.name} {_VERTICAL}"))
            lines.append(self._center(f"{_BOTTOM_LEFT}{bar}{_BOTTOM_RIGHT}"))

            # Agents in stage
            if stage.agent_ids:
                agent_str = f" {_ARROW} ".join(stage.agent_ids)
                if len(agent_str) > self.width - 10:
                    agent_str = agent_str[: self.width - 13] + "..."
                lines.append(self._center(f"({agent_str})"))

            # Connector
            if not is_last:
                lines.append(self._center(_VERTICAL))
                if blueprint.stages[i + 1].parallel:
                    lines.append(self._center(f"{_DOUBLE_VERTICAL} (parallel)"))
                else:
                    lines.append(self._center(_VERTICAL))

        lines.append(self._center(_VERTICAL))
        lines.append(self._center("[ END ]"))
        lines.append("")

        # Footer
        lines.append("=" * self.width)

        return "\n".join(lines)

    def render_compact(self, blueprint: WorkflowBlueprint) -> str:
        """Render a compact single-line representation.

        Args:
            blueprint: The workflow blueprint

        Returns:
            Compact string representation

        """
        stages = []
        for stage in blueprint.stages:
            agents = ",".join(a[:8] for a in stage.agent_ids)
            marker = _PARALLEL if stage.parallel else _ARROW
            stages.append(f"[{stage.name}{marker}:{agents}]")

        joiner = f" {_ARROW} "
        return f" {joiner.join(stages)} "

    def _center(self, text: str) -> str:
        """Center text within width.

        Args:
            text: Text to center

        Returns:
            Centered text string

        """
        if len(text) >= self.width:
            return text
        padding = (self.width - len(text)) // 2
        return " " * padding + text

    def _box(self, title: str) -> str:
        """Create a section header box.

        Args:
            title: Box title

        Returns:
            Section header string

        """
        fill = _HORIZONTAL * (self.width - len(title) - 5)
        return f"{_TOP_LEFT}{_HORIZONTAL} {title} {fill}{_TOP_RIGHT}"
