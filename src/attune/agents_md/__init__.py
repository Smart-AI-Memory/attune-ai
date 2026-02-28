"""Markdown Agent System

Define agents in Markdown files with YAML frontmatter for portability.
Integrates with Attune AI's UnifiedAgentConfig and model tier system.

Markdown agent format inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.agents_md.loader import AgentLoader
from attune.agents_md.parser import MarkdownAgentParser
from attune.agents_md.registry import AgentRegistry

__all__ = [
    "AgentLoader",
    "AgentRegistry",
    "MarkdownAgentParser",
]
